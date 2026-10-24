"""试驾资源与预约 ORM 模型：试驾车、试驾时段（库存）、预约单"""

from datetime import date, datetime

from sqlalchemy import CHAR, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class TestDriveVehicle(Base):
    """试驾车：车牌唯一，归属某车型，可停用"""

    __tablename__ = "test_drive_vehicle"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_no: Mapped[str] = mapped_column(String(20), unique=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("car_model.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="available")  # available 可用 / disabled 停用
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    model: Mapped["CarModel"] = relationship()


class TestDriveSlot(Base):
    """试驾时段库存：车型 × 日期 × 1 小时时段，容量与已约数

    扣减必须走条件更新（booked_count < capacity），防止并发超约
    """

    __tablename__ = "test_drive_slot"
    __table_args__ = (
        UniqueConstraint("model_id", "slot_date", "time_slot", name="uq_slot_model_date_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("car_model.id"), index=True)
    slot_date: Mapped[date] = mapped_column(Date, index=True)
    time_slot: Mapped[str] = mapped_column(CHAR(5))       # 时段起点，如 09:00（粒度 1 小时）
    capacity: Mapped[int] = mapped_column(Integer)        # 可约容量
    booked_count: Mapped[int] = mapped_column(Integer, default=0)  # 已占用（含待确认）


class Appointment(Base):
    """试驾预约单：状态机主体（PRD 4.2）

    提交即占用时段名额；拒绝/取消释放名额
    """

    __tablename__ = "appointment"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(50))
    customer_phone: Mapped[str] = mapped_column(String(20), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customer.id"), index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("car_model.id"), index=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("test_drive_slot.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending 待确认 / confirmed 已确认 / rejected 已拒绝 / cancelled 已取消 / completed 已完成 / no_show 已爽约
    sales_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))     # 处理销售
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("test_drive_vehicle.id"))  # 分配试驾车
    reject_reason: Mapped[str | None] = mapped_column(String(200))
    remark: Mapped[str | None] = mapped_column(String(200))                  # 顾客备注
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TestDriveRecord(Base):
    """试驾记录：试驾完成/爽约登记，关联预约（一对一），含顾客反馈

    评分 1-5 + 文字评价；drive_time 默认登记时间
    """

    __tablename__ = "test_drive_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointment.id"), unique=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("test_drive_vehicle.id"))
    drive_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    feedback_score: Mapped[int | None] = mapped_column()  # 1-5 星
    feedback_text: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
