"""预约与客户数据访问：预约单、客户线索、跟进记录"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer, FollowUpRecord
from app.models.testdrive import Appointment


class AppointmentRepository:
    """预约单查询封装"""

    def __init__(self, db: Session):
        self.db = db

    def add(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.flush()
        return appointment

    def get(self, appointment_id: int) -> Appointment | None:
        return self.db.get(Appointment, appointment_id)

    def find_active_same_day(self, phone: str, model_id: int, slot_id: int) -> Appointment | None:
        """同手机号同车型同时段的有效预约（去重用）"""
        return self.db.scalar(
            select(Appointment).where(
                Appointment.customer_phone == phone,
                Appointment.model_id == model_id,
                Appointment.slot_id == slot_id,
                Appointment.status.in_(["pending", "confirmed"]),
            )
        )

    def list_by_phone(self, phone: str) -> list[Appointment]:
        """按手机号查预约（含客户详情聚合用）"""
        return list(self.db.scalars(
            select(Appointment).where(Appointment.customer_phone == phone)
            .order_by(Appointment.id.desc())
        ).all())


class CustomerRepository:
    """客户线索：以手机号为唯一标识合并建档"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_phone(self, phone: str) -> Customer | None:
        return self.db.scalar(select(Customer).where(Customer.phone == phone))

    def get(self, customer_id: int) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def upsert_by_phone(self, phone: str, name: str) -> Customer:
        """预约即建档：已存在则更新姓名（顾客可能换称呼），否则新建"""
        customer = self.get_by_phone(phone)
        if customer is None:
            customer = Customer(phone=phone, name=name)
            self.db.add(customer)
            self.db.flush()
        elif customer.name != name:
            customer.name = name
            self.db.flush()
        return customer

    def list_by_scope(self, scope: str, sales_id: int) -> list[Customer]:
        """客户列表：mine 仅自己；pool 公共池（未分配）"""
        stmt = select(Customer)
        if scope == "mine":
            stmt = stmt.where(Customer.sales_id == sales_id)
        else:
            stmt = stmt.where(Customer.sales_id.is_(None))
        return list(self.db.scalars(stmt.order_by(Customer.id.desc())).all())

    def list_follow_ups(self, customer_id: int) -> list[FollowUpRecord]:
        """客户跟进时间线（新在前）"""
        return list(self.db.scalars(
            select(FollowUpRecord).where(FollowUpRecord.customer_id == customer_id)
            .order_by(FollowUpRecord.id.desc())
        ).all())

    def add_follow_up(self, record: FollowUpRecord) -> FollowUpRecord:
        self.db.add(record)
        self.db.flush()
        return record
