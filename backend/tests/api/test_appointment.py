"""试驾时段、预约提交（防超约/去重/验证码）、我的预约与取消的接口测试"""

from datetime import date, timedelta

import pytest

from app.api.deps import get_sms_code_service
from app.models.testdrive import Appointment, TestDriveSlot, TestDriveVehicle
from app.services.sms_code import DictCodeStore, SmsCodeService
from tests.api.test_car_model import _admin_headers, _create_model


@pytest.fixture()
def sms_override():
    """用内存验证码存储替换依赖（测试不依赖外部 Redis），并预置已知验证码"""
    service = SmsCodeService(DictCodeStore())
    service.store.set("sms:code:13800001111", "888888", 300)
    service.store.set("sms:code:13800002222", "666666", 300)
    return service


@pytest.fixture(autouse=True)
def _override_sms(client, sms_override):
    """将验证码服务依赖替换为内存实现"""
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_sms_code_service] = lambda: sms_override
    yield
    fastapi_app.dependency_overrides.pop(get_sms_code_service, None)


def _slot(db_session, model, days=1, time_slot="10:00", capacity=1, booked=0):
    """造一个时段（默认明天，避免过期）"""
    s = TestDriveSlot(
        model_id=model.id, slot_date=date.today() + timedelta(days=days),
        time_slot=time_slot, capacity=capacity, booked_count=booked,
    )
    db_session.add(s)
    db_session.flush()
    return s


def _appt_payload(model, slot, phone="13800001111", **kw):
    """预约请求体（含游客验证码默认值）"""
    return {
        "model_id": model.id, "slot_id": slot.id,
        "customer_name": "张顾客", "phone": phone, "code": "888888", **kw
    }


def _login_headers(client, phone):
    """手机号登录并返回请求头：预约已消耗预置验证码，需重新获取（mock 模式响应带 dev_code）"""
    send = client.post("/api/v1/auth/sms-code", json={"phone": phone})
    code = send.json()["data"]["dev_code"]
    login = client.post("/api/v1/auth/login-by-phone", json={"phone": phone, "code": code})
    return {"Authorization": f"Bearer {login.json()['data']['token']}"}


class TestSlotBatchGenerate_合法参数_生成时段:
    def test_生成并可查询余量(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)
        d = date.today() + timedelta(days=2)

        resp = client.post("/api/v1/admin/slots/batch", headers=headers, json={
            "model_id": model.id, "dates": [str(d)], "time_slots": ["10:00", "11:00"], "capacity": 2,
        })

        assert resp.status_code == 200
        assert resp.json()["data"]["created"] == 2
        day = client.get("/api/v1/admin/slots", params={"model_id": model.id, "date": str(d)},
                         headers=headers).json()["data"]
        assert [s["time_slot"] for s in day["items"]] == ["10:00", "11:00"]
        assert day["items"][0]["remaining"] == 2

    def test_重复生成跳过已存在(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)
        d = date.today() + timedelta(days=2)
        client.post("/api/v1/admin/slots/batch", headers=headers, json={
            "model_id": model.id, "dates": [str(d)], "time_slots": ["10:00"], "capacity": 2,
        })

        resp = client.post("/api/v1/admin/slots/batch", headers=headers, json={
            "model_id": model.id, "dates": [str(d)], "time_slots": ["10:00"], "capacity": 5,
        })

        assert resp.json()["data"]["created"] == 0
        # 原容量与已约数不被重置
        day = client.get("/api/v1/admin/slots", params={"model_id": model.id, "date": str(d)},
                         headers=headers).json()["data"]
        assert day["items"][0]["capacity"] == 2

    def test_非整点时段被拒绝(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)

        resp = client.post("/api/v1/admin/slots/batch", headers=headers, json={
            "model_id": model.id, "dates": [str(date.today() + timedelta(days=2))],
            "time_slots": ["10:30"], "capacity": 1,
        })

        assert resp.status_code == 400


class TestAvailableSlots_仅返回有余量时段:
    def test_约满时段不出现在可约列表(self, client, db_session):
        model = _create_model(db_session)
        d = date.today() + timedelta(days=2)
        full = _slot(db_session, model, days=2, time_slot="10:00", capacity=1, booked=1)
        free = _slot(db_session, model, days=2, time_slot="11:00", capacity=2, booked=1)

        resp = client.get("/api/v1/slots", params={"model_id": model.id, "date": str(d)})

        ids = [s["id"] for s in resp.json()["data"]["items"]]
        assert full.id not in ids
        assert free.id in ids
        assert resp.json()["data"]["items"][0]["remaining"] == 1


class TestCreateAppointment_游客带正确验证码_预约成功:
    def test_占用名额并生成线索(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model, capacity=2)

        resp = client.post("/api/v1/appointments", json=_appt_payload(model, slot))

        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "pending"
        # 名额占用
        day = client.get("/api/v1/admin/slots", params={"model_id": model.id, "date": str(slot.slot_date)},
                         headers=_admin_headers(db_session, username="admin02")).json()["data"]
        assert day["items"][0]["booked_count"] == 1
        # 客户线索建档
        from sqlalchemy import text
        row = db_session.execute(text("select name from customer where phone='13800001111'")).first()
        assert row[0] == "张顾客"

    def test_验证码错误被拒绝(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)

        resp = client.post("/api/v1/appointments",
                           json=_appt_payload(model, slot, code="000000"))

        assert resp.status_code == 400
        assert "验证码" in resp.json()["message"]

    def test_未提供验证码被拒绝(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)

        resp = client.post("/api/v1/appointments", json=_appt_payload(model, slot, code=None))

        assert resp.status_code == 400


class TestCreateAppointment_重复提交_被拒绝:
    def test_同时段重复预约返回400(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model, capacity=2)
        client.post("/api/v1/appointments", json=_appt_payload(model, slot))
        # 首次预约已消耗验证码，重新获取后再提交（验证码一次性）
        fresh = client.post("/api/v1/auth/sms-code", json={"phone": "13800001111"}).json()["data"]["dev_code"]

        resp = client.post("/api/v1/appointments",
                           json=_appt_payload(model, slot, code=fresh))

        assert resp.status_code == 400
        assert "重复" in resp.json()["message"]


class TestCreateAppointment_并发抢约_不超卖:
    def test_容量1并发2单仅1单成功(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model, capacity=1)
        results = []
        for phone, code in [("13800001111", "888888"), ("13800002222", "666666")]:
            results.append(client.post("/api/v1/appointments",
                                       json=_appt_payload(model, slot, phone=phone, code=code)))
        statuses = sorted(r.status_code for r in results)
        assert statuses == [200, 400]
        assert "约满" in [r.json()["message"] for r in results if r.status_code == 400][0]
        # 名额只被占用一次
        db_session.expire_all()
        assert db_session.get(TestDriveSlot, slot.id).booked_count == 1


class TestCreateAppointment_时段过期或不存在_返回400:
    def test_过期时段(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model, days=0, time_slot="09:00")  # 今天 9 点，若已过则过期

        resp = client.post("/api/v1/appointments", json=_appt_payload(model, slot))

        assert resp.status_code == 400


class TestMyAppointments_登录顾客_返回本人预约:
    def test_按手机号返回且含车型与时段(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        client.post("/api/v1/appointments", json=_appt_payload(model, slot))
        headers = _login_headers(client, "13800001111")

        resp = client.get("/api/v1/appointments/mine", headers=headers)

        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["model_name"] == model.name
        assert items[0]["status"] == "pending"
        assert items[0]["slot_date"] == str(slot.slot_date)

    def test_未登录返回401(self, client):
        resp = client.get("/api/v1/appointments/mine")
        assert resp.status_code == 401


class TestCancelAppointment_开始前2小时外_取消并释放名额:
    def test_取消后名额释放状态更新(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model, days=2, capacity=2)
        created = client.post("/api/v1/appointments", json=_appt_payload(model, slot)).json()["data"]
        headers = _login_headers(client, "13800001111")

        resp = client.post(f"/api/v1/appointments/{created['id']}/cancel", headers=headers)

        assert resp.status_code == 200
        db_session.expire_all()
        assert db_session.get(Appointment, created["id"]).status == "cancelled"
        assert db_session.get(TestDriveSlot, slot.id).booked_count == 0

    def test_他人预约不可取消(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        created = client.post("/api/v1/appointments", json=_appt_payload(model, slot)).json()["data"]
        # 另一手机号登录（验证码已预置，且尚未被消耗）
        headers = _login_headers(client, "13800002222")

        resp = client.post(f"/api/v1/appointments/{created['id']}/cancel", headers=headers)

        assert resp.status_code == 404

    def test_已取消不可重复取消(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model, days=2)
        created = client.post("/api/v1/appointments", json=_appt_payload(model, slot)).json()["data"]
        headers = _login_headers(client, "13800001111")
        client.post(f"/api/v1/appointments/{created['id']}/cancel", headers=headers)

        resp = client.post(f"/api/v1/appointments/{created['id']}/cancel", headers=headers)

        assert resp.status_code == 400


class TestVehicleManage_车牌重复_返回400:
    def test_重复车牌拒绝创建(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)
        client.post("/api/v1/admin/vehicles", headers=headers,
                    json={"plate_no": "沪A00001", "model_id": model.id})

        resp = client.post("/api/v1/admin/vehicles", headers=headers,
                           json={"plate_no": "沪A00001", "model_id": model.id})

        assert resp.status_code == 400
        assert "已存在" in resp.json()["message"]
