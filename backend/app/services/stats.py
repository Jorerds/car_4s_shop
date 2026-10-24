"""热度统计业务：浏览/对比事件的当日累加"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stat import ModelStatDaily


class StatService:
    """车型热度统计：写入口径统一走这里，报表查询在报表迭代实现"""

    def __init__(self, db: Session):
        self.db = db

    def record_view(self, model_id: int) -> None:
        """记录一次车型详情浏览"""
        self._increment(model_id, "view_count")

    def record_compare(self, model_ids: list[int]) -> None:
        """记录对比参与：每款车型各计一次"""
        for model_id in model_ids:
            self._increment(model_id, "compare_count")

    def _increment(self, model_id: int, field: str) -> None:
        """当日计数 +1：有记录则累加，无记录则建行；行锁防并发（MySQL）"""
        today = date.today()
        row = self.db.scalar(
            select(ModelStatDaily)
            .where(ModelStatDaily.model_id == model_id, ModelStatDaily.stat_date == today)
            .with_for_update()
        )
        if row is None:
            row = ModelStatDaily(model_id=model_id, stat_date=today)
            self.db.add(row)
            self.db.flush()
        setattr(row, field, getattr(row, field) + 1)
        self.db.flush()
