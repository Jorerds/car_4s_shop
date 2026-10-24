"""销售端数据访问：预约查询、试驾记录与通知"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.testdrive import Appointment, TestDriveRecord, TestDriveSlot, TestDriveVehicle


class SalesRepository:
    """销售端查询封装"""

    def __init__(self, db: Session):
        self.db = db

    def get_appointment(self, appointment_id: int) -> Appointment | None:
        return self.db.get(Appointment, appointment_id)

    def list_appointments(self, *, status: str, sales_id: int | None) -> list[Appointment]:
        """预约列表：待确认为公共池（全量）；其余状态仅看自己处理的（finished = 已完成 + 爽约）"""
        statuses = ["completed", "no_show"] if status == "finished" else [status]
        stmt = select(Appointment).where(Appointment.status.in_(statuses))
        if status != "pending":
            stmt = stmt.where(Appointment.sales_id == sales_id)
        return list(self.db.scalars(stmt.order_by(Appointment.id.asc())).all())

    def find_vehicle_conflict(self, vehicle_id: int, slot_id: int) -> Appointment | None:
        """同车辆同时段是否已被其他已确认预约占用"""
        return self.db.scalar(
            select(Appointment).where(
                Appointment.vehicle_id == vehicle_id,
                Appointment.slot_id == slot_id,
                Appointment.status == "confirmed",
            )
        )

    def list_vehicles_by_model(self, model_id: int, available_only: bool) -> list[TestDriveVehicle]:
        stmt = select(TestDriveVehicle).where(TestDriveVehicle.model_id == model_id)
        if available_only:
            stmt = stmt.where(TestDriveVehicle.status == "available")
        return list(self.db.scalars(stmt.order_by(TestDriveVehicle.plate_no)).all())

    def get_slot(self, slot_id: int) -> TestDriveSlot | None:
        return self.db.get(TestDriveSlot, slot_id)

    def add_record(self, record: TestDriveRecord) -> TestDriveRecord:
        self.db.add(record)
        self.db.flush()
        return record

    def get_record_by_appointment(self, appointment_id: int) -> TestDriveRecord | None:
        return self.db.scalar(select(TestDriveRecord).where(TestDriveRecord.appointment_id == appointment_id))

    def add_notification(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def list_notifications(self, phone: str) -> list[Notification]:
        return list(self.db.scalars(
            select(Notification).where(Notification.phone == phone)
            .order_by(Notification.id.desc()).limit(50)
        ).all())

    def count_unread(self, phone: str) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Notification)
            .where(Notification.phone == phone, Notification.is_read.is_(False))
        ) or 0

    def get_notification(self, notification_id: int) -> Notification | None:
        return self.db.get(Notification, notification_id)
