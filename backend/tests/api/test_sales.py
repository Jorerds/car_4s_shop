"""销售端确认/拒绝/试驾记录与站内通知的接口测试"""

import pytest
from sqlalchemy import select

from app.api.deps import get_sms_code_service
from app.core.security import create_access_token, hash_password
from app.models.testdrive import Appointment, TestDriveRecord, TestDriveVehicle
from app.models.user import User
from app.services.sms_code import DictCodeStore, SmsCodeService
from tests.api.test_appointment import _appt_payload, _login_headers, _slot
from tests.api.test_car_model import _create_model


@pytest.fixture(autouse=True)
def sms_override(client):
    """本模块统一用内存验证码存储（预置两个已知手机号验证码）"""
    service = SmsCodeService(DictCodeStore())
    service.store.set("sms:code:13800001111", "888888", 300)
    service.store.set("sms:code:13800002222", "666666", 300)
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_sms_code_service] = lambda: service
    yield
    fastapi_app.dependency_overrides.pop(get_sms_code_service, None)


def _sales_headers(db_session, username="sales01"):
    """创建销售账号并返回请求头"""
    user = User(role="sales", username=username, password_hash=hash_password("pass1234"),
                name="张销售", status="active")
    db_session.add(user)
    db_session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id, 'sales')}"}, user


def _pending_appointment(client, db_session, model, slot, phone="13800001111", code="888888"):
    """走 API 创建待确认预约，返回预约 ID"""
    resp = client.post("/api/v1/appointments",
                       json=_appt_payload(model, slot, phone=phone, code=code))
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _vehicle(db_session, model, plate="沪A·T0001", status="available"):
    """造一台试驾车"""
    v = TestDriveVehicle(plate_no=plate, model_id=model.id, status=status)
    db_session.add(v)
    db_session.flush()
    return v


def _confirm(client, headers, appt_id, vehicle_id):
    """确认预约（测试辅助）"""
    resp = client.post(f"/api/v1/sales/appointments/{appt_id}/confirm",
                       headers=headers, json={"vehicle_id": vehicle_id})
    assert resp.status_code == 200


class TestConfirmAppointment_可用车辆_确认并通知:
    def test_状态已确认车辆归属销售且通知入库(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        appt_id = _pending_appointment(client, db_session, model, slot)
        headers, sales = _sales_headers(db_session)
        vehicle = _vehicle(db_session, model)

        _confirm(client, headers, appt_id, vehicle.id)

        db_session.expire_all()
        appt = db_session.get(Appointment, appt_id)
        assert appt.status == "confirmed"
        assert appt.sales_id == sales.id
        assert appt.vehicle_id == vehicle.id
        # 站内通知已生成
        from sqlalchemy import text
        row = db_session.execute(
            text("select content from notification where phone='13800001111'")
        ).first()
        assert "已确认" in row[0]

    def test_重复确认返回400(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        appt_id = _pending_appointment(client, db_session, model, slot)
        headers, _ = _sales_headers(db_session)
        vehicle = _vehicle(db_session, model)

        _confirm(client, headers, appt_id, vehicle.id)
        resp = client.post(f"/api/v1/sales/appointments/{appt_id}/confirm",
                           headers=headers, json={"vehicle_id": vehicle.id})

        assert resp.status_code == 400


class TestConfirmAppointment_车辆不合规_返回400:
    def test_其他车型车辆不可分配(self, client, db_session):
        model = _create_model(db_session, name="车A")
        other = _create_model(db_session, name="车B")
        slot = _slot(db_session, model)
        appt_id = _pending_appointment(client, db_session, model, slot)
        headers, _ = _sales_headers(db_session)

        resp = client.post(f"/api/v1/sales/appointments/{appt_id}/confirm",
                           headers=headers, json={"vehicle_id": _vehicle(db_session, other).id})

        assert resp.status_code == 400

    def test_停用车辆不可分配(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        appt_id = _pending_appointment(client, db_session, model, slot)
        headers, _ = _sales_headers(db_session)
        disabled = _vehicle(db_session, model, plate="沪A·T0002", status="disabled")

        resp = client.post(f"/api/v1/sales/appointments/{appt_id}/confirm",
                           headers=headers, json={"vehicle_id": disabled.id})

        assert resp.status_code == 400

    def test_同时段车辆只能分配一个预约(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model, capacity=2)
        appt1 = _pending_appointment(client, db_session, model, slot, phone="13800001111", code="888888")
        appt2 = _pending_appointment(client, db_session, model, slot, phone="13800002222", code="666666")
        headers, _ = _sales_headers(db_session)
        vehicle = _vehicle(db_session, model)

        _confirm(client, headers, appt1, vehicle.id)
        resp = client.post(f"/api/v1/sales/appointments/{appt2}/confirm",
                           headers=headers, json={"vehicle_id": vehicle.id})

        assert resp.status_code == 400


class TestRejectAppointment_拒绝_释放名额并通知:
    def test_名额释放状态为已拒绝(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        appt_id = _pending_appointment(client, db_session, model, slot)
        headers, _ = _sales_headers(db_session)

        resp = client.post(f"/api/v1/sales/appointments/{appt_id}/reject",
                           headers=headers, json={"reason": "该时段车辆保养"})

        assert resp.status_code == 200
        db_session.expire_all()
        appt = db_session.get(Appointment, appt_id)
        assert appt.status == "rejected"
        assert "保养" in appt.reject_reason
        assert db_session.get(TestDriveSlot := type(slot), slot.id).booked_count == 0


class TestRecordTestDrive_已确认预约_登记结果:
    def _confirmed_setup(self, client, db_session):
        """创建并确认一个预约，返回 (headers, appt_id)"""
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        appt_id = _pending_appointment(client, db_session, model, slot)
        headers, _ = _sales_headers(db_session)
        _confirm(client, headers, appt_id, _vehicle(db_session, model).id)
        return headers, appt_id

    def test_完成并保存评分反馈(self, client, db_session):
        headers, appt_id = self._confirmed_setup(client, db_session)

        resp = client.post(f"/api/v1/sales/appointments/{appt_id}/record",
                           headers=headers,
                           json={"result": "completed", "feedback_score": 5, "feedback_text": "动力响应快"})

        assert resp.status_code == 200
        db_session.expire_all()
        assert db_session.get(Appointment, appt_id).status == "completed"
        record = db_session.scalar(select(TestDriveRecord).where(TestDriveRecord.appointment_id == appt_id))
        assert record.feedback_score == 5
        assert record.feedback_text == "动力响应快"

    def test_爽约不计评分(self, client, db_session):
        headers, appt_id = self._confirmed_setup(client, db_session)

        resp = client.post(f"/api/v1/sales/appointments/{appt_id}/record",
                           headers=headers, json={"result": "no_show"})

        assert resp.status_code == 200
        db_session.expire_all()
        assert db_session.get(Appointment, appt_id).status == "no_show"
        record = db_session.scalar(select(TestDriveRecord).where(TestDriveRecord.appointment_id == appt_id))
        assert record.feedback_score is None

    def test_重复登记返回400(self, client, db_session):
        headers, appt_id = self._confirmed_setup(client, db_session)
        client.post(f"/api/v1/sales/appointments/{appt_id}/record",
                    headers=headers, json={"result": "completed"})

        resp = client.post(f"/api/v1/sales/appointments/{appt_id}/record",
                           headers=headers, json={"result": "no_show"})

        assert resp.status_code == 400

    def test_未确认预约不可登记(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        appt_id = _pending_appointment(client, db_session, model, slot)
        headers, _ = _sales_headers(db_session)

        resp = client.post(f"/api/v1/sales/appointments/{appt_id}/record",
                           headers=headers, json={"result": "completed"})

        # 待确认预约不属于该销售，按数据范围返回 404（与列表口径一致）
        assert resp.status_code == 404


class TestSalesPermissions_顾客角色_返回403:
    def test_顾客不可访问销售接口(self, client, db_session):
        customer = User(role="customer", phone="13900000001", name="顾客", status="active")
        db_session.add(customer)
        db_session.flush()
        headers = {"Authorization": f"Bearer {create_access_token(customer.id, 'customer')}"}

        resp = client.get("/api/v1/sales/appointments", headers=headers)

        assert resp.status_code == 403


class TestSalesListFinished_已结束状态_合并已完成与爽约:
    def test_finished包含completed与no_show(self, client, db_session):
        model = _create_model(db_session)
        headers, _ = _sales_headers(db_session)
        # 一单完成、一单爽约（车牌唯一、手机号唯一避免去重与验证码复用）
        for idx, (result, phone, code) in enumerate(
            [("completed", "13800001111", "888888"), ("no_show", "13800002222", "666666")]
        ):
            slot = _slot(db_session, model, time_slot=f"{10 + idx}:00")
            appt_id = _pending_appointment(client, db_session, model, slot, phone=phone, code=code)
            vehicle = _vehicle(db_session, model, plate=f"沪A·F{idx:04d}")
            _confirm(client, headers, appt_id, vehicle.id)
            client.post(f"/api/v1/sales/appointments/{appt_id}/record",
                        headers=headers, json={"result": result})

        resp = client.get("/api/v1/sales/appointments", params={"status": "finished"}, headers=headers)

        assert resp.status_code == 200
        statuses = [i["status"] for i in resp.json()["data"]["items"]]
        assert sorted(statuses) == ["completed", "no_show"]


class TestNotifications_顾客_拉取并标记已读:
    def test_确认后顾客可见通知并标记已读(self, client, db_session):
        model = _create_model(db_session)
        slot = _slot(db_session, model)
        appt_id = _pending_appointment(client, db_session, model, slot)
        headers, _ = _sales_headers(db_session)
        _confirm(client, headers, appt_id, _vehicle(db_session, model).id)

        # 顾客登录后拉取通知
        cust_headers = _login_headers(client, "13800001111")
        resp = client.get("/api/v1/notifications/mine", headers=cust_headers)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["unread"] == 1
        assert "已确认" in data["items"][0]["content"]

        # 标记已读
        nid = data["items"][0]["id"]
        client.post(f"/api/v1/notifications/{nid}/read", headers=cust_headers)
        resp = client.get("/api/v1/notifications/mine", headers=cust_headers)
        assert resp.json()["data"]["unread"] == 0
