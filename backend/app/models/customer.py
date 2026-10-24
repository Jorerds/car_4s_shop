"""客户线索与跟进模型：预约即建档（手机号唯一），跟进过程沉淀"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Customer(Base):
    """客户线索：以手机号为唯一标识合并；状态随业务流转（new/following/test_driven/deal）"""

    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    sales_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))  # 归属销售，线索池为 None
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class FollowUpRecord(Base):
    """跟进记录：电话/到店/试驾/成交四类，含内容与下次跟进计划"""

    __tablename__ = "follow_up_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), index=True)
    sales_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    type: Mapped[str] = mapped_column(String(20))  # phone 电话 / visit 到店 / test_drive 试驾 / deal 成交
    content: Mapped[str] = mapped_column(String(500))
    next_follow_at: Mapped[datetime | None] = mapped_column(DateTime)  # 下次跟进计划
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
