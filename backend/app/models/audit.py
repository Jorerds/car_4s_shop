"""审计日志模型：关键操作（如报表导出）留痕"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditLog(Base):
    """审计日志：操作人、动作、明细，导出等敏感行为留痕（PRD 数据合规要求）"""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column()
    action: Mapped[str] = mapped_column(String(50))    # 如 export
    detail: Mapped[str] = mapped_column(String(500))   # 如 booking/excel/2026-09-01~2026-10-01
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
