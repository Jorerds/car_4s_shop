"""热度统计模型：车型每日浏览/对比次数（车型热度报表数据源）"""

from datetime import date

from sqlalchemy import Date, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ModelStatDaily(Base):
    """车型热度日统计：每车型每天一行，浏览/对比事件当日累加"""

    __tablename__ = "model_stat_daily"
    __table_args__ = (
        UniqueConstraint("model_id", "stat_date", name="uq_stat_model_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(Integer, index=True)
    stat_date: Mapped[date] = mapped_column(Date)
    view_count: Mapped[int] = mapped_column(Integer, default=0)     # 详情页浏览次数
    compare_count: Mapped[int] = mapped_column(Integer, default=0)  # 参与对比次数
