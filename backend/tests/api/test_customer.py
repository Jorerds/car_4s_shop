"""客户跟进（列表/认领/分配/详情/跟进登记）与账号管理的接口测试"""

import pytest
from sqlalchemy import select

from app.api.deps import get_sms_code_service
from app.core.security import create_access_token, hash_password
from app.models.customer import Customer
from app.models.user import User
from app.services.sms_code import DictCodeStore, SmsCodeService
from tests.api.test_appointment import _appt_payload, _slot
from tests.api.test_car_model import _admin_headers, _create_model


@pytest.fixture(autouse=True)
def sms_override(client):
    """内存验证码存储，预置已知手机号"""
    service = SmsCodeService(DictCodeStore())
    service.store.set("sms:code:13800001111", "888888", 300)
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_sms_code_service] = lambda: service
    yield
    fastapi_app.dependency_overrides.pop(get_sms_code_service, None)


def _sales(db_session, username="sales01"):
    """创建销售账号，返回 (headers, user)"""
    user = User(role="sales", username=username, password_hash=hash_password("pass1234"),
                name="张销售", status="active")
    db_session.add(user)
    db_session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id, 'sales')}"}, user


def _customer_headers(db_session, phone="13900000001"):
    """创建顾客账号，返回请求头"""
    user = User(role="customer", phone=phone, name="顾客", status="active")
    db_session.add(user)
    db_session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id, 'customer')}"}


def _make_customer_via_appointment(client, db_session, model, phone="13800001111"):
    """通过预约接口自动建档，返回客户 ID"""
    slot = _slot(db_session, model)
    resp = client.post("/api/v1/appointments", json=_appt_payload(
        model, slot, phone=phone, code="888888"))
    assert resp.status_code == 200
    db_session.expire_all()
    return db_session.scalar(select(Customer).where(Customer.phone == phone)).id


class TestCustomerList_默认公共池_预约即建档:
    def test_新客户进入公共池(self, client, db_session):
        model = _create_model(db_session)
        headers, _ = _sales(db_session)
        customer_id = _make_customer_via_appointment(client, db_session, model)

        resp = client.get("/api/v1/sales/customers?scope=pool", headers=headers)

        items = resp.json()["data"]["items"]
        assert [i["id"] for i in items] == [customer_id]
        assert items[0]["status_text"] == "新线索"


class TestClaimCustomer_公共池认领_先到先得:
    def test_认领后进入我的客户(self, client, db_session):
        model = _create_model(db_session)
        headers, user = _sales(db_session)
        customer_id = _make_customer_via_appointment(client, db_session, model)

        resp = client.post(f"/api/v1/sales/customers/{customer_id}/claim", headers=headers)

        assert resp.status_code == 200
        mine = client.get("/api/v1/sales/customers?scope=mine", headers=headers).json()["data"]
        assert [i["id"] for i in mine["items"]] == [customer_id]

    def test_已分配线索不可重复认领(self, client, db_session):
        model = _create_model(db_session)
        headers1, _ = _sales(db_session, "sales01")
        headers2, _ = _sales(db_session, "sales02")
        customer_id = _make_customer_via_appointment(client, db_session, model)
        client.post(f"/api/v1/sales/customers/{customer_id}/claim", headers=headers1)

        resp = client.post(f"/api/v1/sales/customers/{customer_id}/claim", headers=headers2)

        assert resp.status_code == 400


class TestAssignCustomer_管理员分配:
    def test_分配后销售可见且他人不可见(self, client, db_session):
        model = _create_model(db_session)
        admin_headers = _admin_headers(db_session)
        headers1, _ = _sales(db_session, "sales01")
        headers2, _ = _sales(db_session, "sales02")
        sales2_user = db_session.scalar(select(User).where(User.username == "sales02"))
        customer_id = _make_customer_via_appointment(client, db_session, model)

        resp = client.put(f"/api/v1/admin/customers/{customer_id}/assign",
                          params={"sales_id": sales2_user.id}, headers=admin_headers)

        assert resp.status_code == 200
        assert client.get("/api/v1/sales/customers?scope=mine", headers=headers2).json()["data"]["items"]
        assert not client.get("/api/v1/sales/customers?scope=mine", headers=headers1).json()["data"]["items"]


class TestCustomerDetail_归属校验与聚合:
    def test_详情含预约与跟进时间线(self, client, db_session):
        model = _create_model(db_session)
        headers, _ = _sales(db_session)
        customer_id = _make_customer_via_appointment(client, db_session, model)
        client.post(f"/api/v1/sales/customers/{customer_id}/claim", headers=headers)
        client.post(f"/api/v1/sales/customers/{customer_id}/follow-ups", headers=headers,
                    json={"type": "phone", "content": "电话沟通了预算"})

        resp = client.get(f"/api/v1/sales/customers/{customer_id}", headers=headers)

        data = resp.json()["data"]
        assert len(data["appointments"]) == 1
        assert data["appointments"][0]["model_name"] == model.name
        assert data["follow_ups"][0]["type_text"] == "电话"
        assert data["status"] == "following"  # 电话跟进后自动流转

    def test_非归属销售不可见详情(self, client, db_session):
        model = _create_model(db_session)
        headers1, _ = _sales(db_session, "sales01")
        headers2, _ = _sales(db_session, "sales02")
        customer_id = _make_customer_via_appointment(client, db_session, model)
        client.post(f"/api/v1/sales/customers/{customer_id}/claim", headers=headers1)

        resp = client.get(f"/api/v1/sales/customers/{customer_id}", headers=headers2)

        assert resp.status_code == 404


class TestFollowUp_类型驱动状态流转:
    def test_成交跟进置为已成交(self, client, db_session):
        model = _create_model(db_session)
        headers, _ = _sales(db_session)
        customer_id = _make_customer_via_appointment(client, db_session, model)
        client.post(f"/api/v1/sales/customers/{customer_id}/claim", headers=headers)

        client.post(f"/api/v1/sales/customers/{customer_id}/follow-ups", headers=headers,
                    json={"type": "deal", "content": "已签单"})
        db_session.expire_all()
        assert db_session.get(Customer, customer_id).status == "deal"

    def test_跟进内容为空被拒绝(self, client, db_session):
        model = _create_model(db_session)
        headers, _ = _sales(db_session)
        customer_id = _make_customer_via_appointment(client, db_session, model)
        client.post(f"/api/v1/sales/customers/{customer_id}/claim", headers=headers)

        resp = client.post(f"/api/v1/sales/customers/{customer_id}/follow-ups", headers=headers,
                           json={"type": "phone", "content": ""})

        assert resp.status_code == 422


class TestUserAdmin_创建与停用账号:
    def test_创建销售账号并可登录(self, client, db_session):
        admin_headers = _admin_headers(db_session)
        resp = client.post("/api/v1/admin/users", headers=admin_headers, json={
            "username": "sales_new", "password": "pass1234", "name": "新销售", "role": "sales",
        })
        assert resp.status_code == 200

        login = client.post("/api/v1/auth/login-by-account",
                            json={"username": "sales_new", "password": "pass1234"})
        assert login.status_code == 200

    def test_重复账号被拒绝(self, client, db_session):
        admin_headers = _admin_headers(db_session)
        client.post("/api/v1/admin/users", headers=admin_headers, json={
            "username": "dup01", "password": "pass1234", "name": "A", "role": "sales",
        })

        resp = client.post("/api/v1/admin/users", headers=admin_headers, json={
            "username": "dup01", "password": "pass1234", "name": "B", "role": "sales",
        })

        assert resp.status_code == 400

    def test_停用后登录被拒(self, client, db_session):
        admin_headers = _admin_headers(db_session)
        created = client.post("/api/v1/admin/users", headers=admin_headers, json={
            "username": "sales_off", "password": "pass1234", "name": "停用销售", "role": "sales",
        }).json()["data"]

        client.put(f"/api/v1/admin/users/{created['id']}/status",
                   params={"status": "disabled"}, headers=admin_headers)
        login = client.post("/api/v1/auth/login-by-account",
                            json={"username": "sales_off", "password": "pass1234"})

        # 停用账号登录返回 403（账号或密码错误统一 401，已停用单独提示）
        assert login.status_code == 403

    def test_内置管理员不可停用(self, client, db_session):
        admin_headers = _admin_headers(db_session, username="admin_x")
        # 创建一个 username=admin 的账号，验证内置保护规则
        created = client.post("/api/v1/admin/users", headers=admin_headers, json={
            "username": "admin", "password": "pass1234", "name": "管理员", "role": "admin",
        }).json()["data"]

        resp = client.put(f"/api/v1/admin/users/{created['id']}/status",
                          params={"status": "disabled"}, headers=admin_headers)

        assert resp.status_code == 400


class TestCustomerPermissions_顾客角色_返回403:
    def test_顾客不可访问客户接口(self, client, db_session):
        headers = _customer_headers(db_session)
        resp = client.get("/api/v1/sales/customers", headers=headers)
        assert resp.status_code == 403
