"""站内通知模型：按接收人手机号投递，登录后按手机号拉取"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Notification(Base):
    """站内通知：确认/拒绝等事件触达顾客（游客预约的手机号，登录后按手机号可见）"""

    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)  # 接收人手机号
    content: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
