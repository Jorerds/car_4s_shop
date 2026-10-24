"""统计报表与导出测试"""

import pytest
from sqlalchemy import text

from app.api.deps import get_sms_code_service
from app.core.security import create_access_token, hash_password
from app.models.customer import Customer, FollowUpRecord
from app.models.stat import ModelStatDaily
from app.models.testdrive import Appointment, TestDriveSlot
from app.models.user import User
from app.services.sms_code import DictCodeStore, SmsCodeService
from tests.api.test_car_model import _admin_headers, _create_model


@pytest.fixture(autouse=True)
def _sms_override(client):
    """内存验证码存储"""
    service = SmsCodeService(DictCodeStore())
    service.store.set("sms:code:13800001111", "888888", 300)
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_sms_code_service] = lambda: service
    yield
    fastapi_app.dependency_overrides.pop(get_sms_code_service, None)


def _sales(db_session, username="sales01"):
    user = User(role="sales", username=username, password_hash=hash_password("pass1234"),
                name="张销售", status="active")
    db_session.add(user)
    db_session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id, 'sales')}"}, user


def _appointment(db_session, model, status="pending", sales_id=None, name="张顾客",
                 phone="13800001111", time_slot="10:00"):
    """直接造一条预约（指定状态；时段默认 10:00，同车型多次调用需传不同时段）"""
    slot = TestDriveSlot(
        model_id=model.id, slot_date=__import__("datetime").date.today(),
        time_slot=time_slot, capacity=2, booked_count=0,
    )
    db_session.add(slot)
    db_session.flush()
    appt = Appointment(
        customer_name=name, customer_phone=phone, model_id=model.id, slot_id=slot.id,
        status=status, sales_id=sales_id,
    )
    db_session.add(appt)
    db_session.flush()
    return appt


class TestBookingReport_有预约数据_返回趋势与漏斗:
    def test_状态计数与爽约率正确(self, client, db_session):
        model = _create_model(db_session)
        _appointment(db_session, model, status="completed", time_slot="10:00")
        _appointment(db_session, model, status="completed", time_slot="11:00")
        _appointment(db_session, model, status="no_show", time_slot="13:00")
        headers = _admin_headers(db_session)

        resp = client.get("/api/v1/reports/booking", headers=headers)

        data = resp.json()["data"]
        assert data["total"] == 3
        counts = {c["status"]: c["count"] for c in data["status_counts"]}
        assert counts["completed"] == 2 and counts["no_show"] == 1
        # 漏斗末级 = 到店试驾完成数
        assert data["funnel"][-1]["value"] == 2
        # 爽约率 = 爽约 / 已处理（完成+爽约） = 1/3
        assert data["no_show_rate"] == round(1 / 3 * 100, 1)
        # 趋势含今天
        assert any(row["count"] == 3 for row in data["trend"])


class TestSalesReport_按销售聚合:
    def test_跟进与成交计入对应销售(self, client, db_session):
        model = _create_model(db_session)
        _, sales_user = _sales(db_session)
        _appointment(db_session, model, status="completed", sales_id=sales_user.id)
        db_session.add(Customer(phone="13800001111", name="张顾客", sales_id=sales_user.id))
        db_session.add(FollowUpRecord(customer_id=1, sales_id=sales_user.id,
                                      type="deal", content="已签单"))
        db_session.flush()
        headers = _admin_headers(db_session)

        resp = client.get("/api/v1/reports/sales", headers=headers)

        items = resp.json()["data"]["items"]
        assert len(items) == 1
        row = items[0]
        assert row["sales_name"] == "张销售"
        assert row["completed"] == 1
        assert row["deals"] == 1
        assert row["follow_ups"] == 1


class TestCustomerReport_新增与状态分布:
    def test_返回趋势与四状态(self, client, db_session):
        db_session.add_all([
            Customer(phone="13800000001", name="A", status="new"),
            Customer(phone="13800000002", name="B", status="deal"),
            Customer(phone="13800000003", name="C", status="following"),
        ])
        db_session.flush()
        headers = _admin_headers(db_session)

        resp = client.get("/api/v1/reports/customer", headers=headers)

        data = resp.json()["data"]
        assert sum(row["count"] for row in data["trend"]) == 3
        dist = {d["status"]: d["count"] for d in data["status_dist"]}
        assert dist == {"new": 1, "deal": 1, "following": 1}


class TestModelHeatReport_聚合热度与预约:
    def test_浏览对比预约按车型归并(self, client, db_session):
        import datetime
        model = _create_model(db_session)
        _appointment(db_session, model, status="pending")
        db_session.add(ModelStatDaily(
            model_id=model.id, stat_date=datetime.date.today(), view_count=5, compare_count=2))
        db_session.flush()
        headers = _admin_headers(db_session)

        resp = client.get("/api/v1/reports/model", headers=headers)

        items = resp.json()["data"]["items"]
        assert items[0]["model_name"] == model.name
        assert items[0]["views"] == 5
        assert items[0]["compares"] == 2
        assert items[0]["appointments"] == 1


class TestExportReport_导出Excel与CSV:
    @pytest.mark.parametrize("fmt,ext", [("excel", "xlsx"), ("csv", "csv")])
    def test_生成文件并写审计日志(self, client, db_session, tmp_path, monkeypatch, fmt, ext):
        from app.core.config import settings
        monkeypatch.setattr(settings, "EXPORT_DIR", str(tmp_path))
        model = _create_model(db_session)
        _appointment(db_session, model, status="completed")
        headers = _admin_headers(db_session)

        resp = client.post(f"/api/v1/reports/booking/export",
                           params={"format": fmt}, headers=headers)

        assert resp.status_code == 200
        url = resp.json()["data"]["url"]
        assert url.endswith(f".{ext}")
        filename = url.rsplit("/", 1)[1]
        assert (tmp_path / filename).exists()
        # 审计留痕
        row = db_session.execute(
            text("select action, detail from audit_log order by id desc limit 1")).first()
        assert row[0] == "export"
        assert f"booking/{fmt}" in row[1]

    def test_导出CSV内容正确(self, client, db_session, tmp_path, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "EXPORT_DIR", str(tmp_path))
        model = _create_model(db_session)
        _appointment(db_session, model)
        headers = _admin_headers(db_session)
        url = client.post("/api/v1/reports/model/export",
                          params={"format": "csv"}, headers=headers).json()["data"]["url"]

        # StaticFiles 挂载目录在应用创建时固定，测试直接校验落盘文件内容
        filename = url.rsplit("/", 1)[1]
        content = (tmp_path / filename).read_text(encoding="utf-8-sig")
        assert "车型" in content
        assert model.name in content


class TestReportPermissions_销售角色_返回403:
    def test_销售不可访问报表(self, client, db_session):
        headers, _ = _sales(db_session)
        resp = client.get("/api/v1/reports/booking", headers=headers)
        assert resp.status_code == 403
