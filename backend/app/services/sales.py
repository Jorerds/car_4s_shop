"""销售端业务：预约确认/拒绝、试驾记录登记、双通道通知

短信发送为同步直发（单店量级低、开发期无 Celery Worker 常驻）；
站内通知落库，顾客登录后按手机号拉取
"""

from app.core.exceptions import BizException
from app.integrations.sms import get_sms_sender
from app.models.notification import Notification
from app.models.testdrive import TestDriveRecord, TestDriveVehicle
from app.repositories.sales import SalesRepository
from app.repositories.testdrive import TestDriveRepository
from app.schemas.sales import RecordRequest, SalesAppointmentItem


class SalesService:
    """销售业务用例"""

    def __init__(self, repo: SalesRepository, testdrive_repo: TestDriveRepository):
        self.repo = repo
        self.testdrive_repo = testdrive_repo

    # ---- 列表 ----

    def list_appointments(self, status: str, sales_id: int) -> dict:
        """预约列表（待确认公共池；其余仅看自己处理的）"""
        appointments = self.repo.list_appointments(status=status, sales_id=sales_id)
        model_names = self._model_names([a.model_id for a in appointments])
        plates = self._vehicle_plates([a.vehicle_id for a in appointments])
        slots = {s.id: s for s in (self.repo.get_slot(a.slot_id) for a in appointments) if s}
        return {
            "items": [
                SalesAppointmentItem(
                    id=a.id, model_id=a.model_id, model_name=model_names.get(a.model_id, ""),
                    customer_name=a.customer_name, customer_phone=a.customer_phone,
                    slot_date=str(slots[a.slot_id].slot_date) if a.slot_id in slots else "",
                    time_slot=slots[a.slot_id].time_slot if a.slot_id in slots else "",
                    status=a.status, remark=a.remark,
                    vehicle_plate=plates.get(a.vehicle_id),
                    reject_reason=a.reject_reason,
                    created_at=a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
                ).model_dump()
                for a in appointments
            ]
        }

    def list_assignable_vehicles(self, model_id: int) -> dict:
        """可分配试驾车（该车型且可用）"""
        vehicles = self.repo.list_vehicles_by_model(model_id, available_only=True)
        return {"items": [{"id": v.id, "plate_no": v.plate_no} for v in vehicles]}

    # ---- 确认 / 拒绝 ----

    def confirm(self, appointment_id: int, vehicle_id: int, sales_id: int) -> None:
        """确认预约：校验状态与车辆，占用车辆（同时段唯一），双通道通知顾客"""
        appointment = self._get_pending(appointment_id)
        vehicle = self.repo.db.get(TestDriveVehicle, vehicle_id)
        if vehicle is None or vehicle.model_id != appointment.model_id:
            raise BizException(code=400, message="试驾车不存在或不属于该车型")
        if vehicle.status != "available":
            raise BizException(code=400, message="该试驾车已停用，不可分配")
        # 同一时段一辆车只能服务一个预约
        if self.repo.find_vehicle_conflict(vehicle_id, appointment.slot_id):
            raise BizException(code=400, message="该车辆在此时段已被分配")

        appointment.status = "confirmed"
        appointment.sales_id = sales_id
        appointment.vehicle_id = vehicle_id
        self.repo.db.flush()

        slot = self.repo.get_slot(appointment.slot_id)
        self._notify(
            appointment.customer_phone,
            f"您的试驾预约已确认：{self._model_name(appointment.model_id)} "
            f"{slot.slot_date} {slot.time_slot}，试驾车 {vehicle.plate_no}，请携带驾驶证准时到店。",
        )

    def reject(self, appointment_id: int, reason: str, sales_id: int) -> None:
        """拒绝预约：释放时段名额，通知顾客（附原因）"""
        appointment = self._get_pending(appointment_id)
        appointment.status = "rejected"
        appointment.sales_id = sales_id
        appointment.reject_reason = reason
        self.testdrive_repo.release_slot(appointment.slot_id)
        self.repo.db.flush()

        slot = self.repo.get_slot(appointment.slot_id)
        self._notify(
            appointment.customer_phone,
            f"很抱歉，您 {slot.slot_date} {slot.time_slot} 的"
            f"{self._model_name(appointment.model_id)}试驾预约未能确认。原因：{reason}。欢迎改约其他时段。",
        )

    # ---- 试驾记录 ----

    def record(self, appointment_id: int, body: RecordRequest, sales_id: int) -> None:
        """登记试驾结果：仅已确认可登记，每单仅一次"""
        appointment = self.repo.get_appointment(appointment_id)
        if appointment is None or appointment.sales_id != sales_id:
            raise BizException(code=404, message="预约不存在", http_status=404)
        if appointment.status != "confirmed":
            raise BizException(code=400, message="仅已确认的预约可登记试驾记录")
        if self.repo.get_record_by_appointment(appointment_id):
            raise BizException(code=400, message="该预约已登记过试驾记录")

        appointment.status = body.result
        self.repo.add_record(TestDriveRecord(
            appointment_id=appointment_id, vehicle_id=appointment.vehicle_id,
            feedback_score=body.feedback_score if body.result == "completed" else None,
            feedback_text=body.feedback_text,
        ))
        self.repo.db.flush()

    # ---- 通知 ----

    def list_notifications(self, phone: str) -> dict:
        """站内通知列表 + 未读数"""
        items = self.repo.list_notifications(phone)
        return {
            "items": [
                {
                    "id": n.id, "content": n.content, "is_read": n.is_read,
                    "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "",
                }
                for n in items
            ],
            "unread": self.repo.count_unread(phone),
        }

    def mark_read(self, notification_id: int, phone: str) -> None:
        """标记已读：校验归属，防止越权修改他人通知"""
        notification = self.repo.get_notification(notification_id)
        if notification is None or notification.phone != phone:
            raise BizException(code=404, message="通知不存在", http_status=404)
        notification.is_read = True
        self.repo.db.flush()

    # ---- 内部工具 ----

    def _get_pending(self, appointment_id: int):
        appointment = self.repo.get_appointment(appointment_id)
        if appointment is None:
            raise BizException(code=404, message="预约不存在", http_status=404)
        if appointment.status != "pending":
            raise BizException(code=400, message="该预约已处理，请勿重复操作")
        return appointment

    def _notify(self, phone: str, content: str) -> None:
        """双通道通知：站内落库 + 短信直发（mock 模式打日志）"""
        self.repo.add_notification(Notification(phone=phone, content=content))
        get_sms_sender().send_notify(phone, "appointment", {"content": content})

    def _model_name(self, model_id: int) -> str:
        from sqlalchemy import select
        from app.models.car_model import CarModel
        row = self.repo.db.execute(select(CarModel.name).where(CarModel.id == model_id)).first()
        return row[0] if row else ""

    def _model_names(self, model_ids: list[int]) -> dict[int, str]:
        from sqlalchemy import select
        from app.models.car_model import CarModel
        ids = set(model_ids)
        if not ids:
            return {}
        rows = self.repo.db.execute(select(CarModel.id, CarModel.name).where(CarModel.id.in_(ids)))
        return {row[0]: row[1] for row in rows.all()}

    def _vehicle_plates(self, vehicle_ids: list[int | None]) -> dict[int, str]:
        from sqlalchemy import select
        from app.models.testdrive import TestDriveVehicle
        ids = {vid for vid in vehicle_ids if vid}
        if not ids:
            return {}
        rows = self.repo.db.execute(select(TestDriveVehicle.id, TestDriveVehicle.plate_no).where(TestDriveVehicle.id.in_(ids)))
        return {row[0]: row[1] for row in rows.all()}
