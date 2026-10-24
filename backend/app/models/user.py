"""用户模型：顾客/销售顾问/店管理员三种角色，支撑 RBAC"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    """系统用户：顾客用手机号登录，销售/管理员用账号密码登录"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 角色：customer=顾客 sales=销售顾问 admin=店管理员
    role: Mapped[str] = mapped_column(String(20), index=True)
    # 顾客用手机号，销售/管理员用账号，二选一
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/disabled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
