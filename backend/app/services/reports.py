"""报表业务：四类统计查询与 Excel/CSV 导出

导出为同步生成（单店量级秒级完成，开发期无常驻 Worker；如数据量增大可平滑改为 Celery 异步）
"""

import csv
import uuid
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.car_model import CarModel
from app.models.customer import Customer, FollowUpRecord
from app.models.stat import ModelStatDaily
from app.models.testdrive import Appointment
from app.models.user import User

APPOINTMENT_STATUS_TEXT = {
    "pending": "待确认", "confirmed": "已确认", "rejected": "已拒绝",
    "cancelled": "已取消", "completed": "已完成", "no_show": "已爽约",
}

# 报表字段定义（表头 + 取值），供导出复用
REPORT_COLUMNS = {
    "booking": ["日期", "预约量"],
    "sales": ["销售", "跟进量", "确认数", "试驾完成", "成交量", "确认率"],
    "customer": ["日期", "新增客户"],
    "model": ["车型", "浏览量", "对比次数", "预约量"],
}


class ReportService:
    """统计报表用例（仅管理员）"""

    def __init__(self, db: Session):
        self.db = db

    # ---- 预约/转化 ----

    def booking(self, start: date, end: date) -> dict:
        """预约量趋势 + 状态分布 + 转化漏斗 + 爽约率"""
        trend = self._daily_trend(Appointment.created_at, start, end)
        status_counts = dict(
            self.db.execute(
                select(Appointment.status, func.count())
                .where(func.date(Appointment.created_at) >= start, func.date(Appointment.created_at) <= end)
                .group_by(Appointment.status)
            ).all()
        )
        total = sum(status_counts.values())
        completed = status_counts.get("completed", 0)
        no_show = status_counts.get("no_show", 0)
        # 转化漏斗：预约 → 确认 → 到店试驾（完成）
        handled = completed + no_show + status_counts.get("rejected", 0) + status_counts.get("cancelled", 0)
        return {
            "trend": trend,
            "status_counts": [
                {"status": s, "label": APPOINTMENT_STATUS_TEXT[s], "count": status_counts.get(s, 0)}
                for s in APPOINTMENT_STATUS_TEXT
            ],
            "funnel": [
                {"stage": "预约提交", "value": total},
                {"stage": "销售确认", "value": status_counts.get("confirmed", 0) + completed + no_show},
                {"stage": "到店试驾", "value": completed},
            ],
            "total": total,
            "no_show_rate": round(no_show / handled * 100, 1) if handled else 0,
        }

    # ---- 销售业绩 ----

    def sales(self, start: date, end: date) -> list[dict]:
        """各销售：跟进量、确认数、试驾完成、成交量、确认率（按成交量降序）"""
        follow_ups = dict(
            self.db.execute(
                select(FollowUpRecord.sales_id, func.count())
                .where(func.date(FollowUpRecord.created_at) >= start, func.date(FollowUpRecord.created_at) <= end)
                .group_by(FollowUpRecord.sales_id)
            ).all()
        )
        appt_stats = self.db.execute(
            select(
                Appointment.sales_id,
                func.sum(case((Appointment.status == "confirmed", 1), else_=0)),
                func.sum(case((Appointment.status == "completed", 1), else_=0)),
                func.sum(case((Appointment.status.in_(["rejected", "cancelled", "no_show"]), 1), else_=0)),
            )
            .where(Appointment.sales_id.isnot(None),
                   func.date(Appointment.created_at) >= start, func.date(Appointment.created_at) <= end)
            .group_by(Appointment.sales_id)
        ).all()
        deals = dict(
            self.db.execute(
                select(FollowUpRecord.sales_id, func.count())
                .where(FollowUpRecord.type == "deal",
                       func.date(FollowUpRecord.created_at) >= start, func.date(FollowUpRecord.created_at) <= end)
                .group_by(FollowUpRecord.sales_id)
            ).all()
        )
        sales_names = self._user_names(list({sid for sid, *_ in appt_stats} | set(follow_ups)))
        items = []
        for sales_id, confirmed, completed, failed in appt_stats:
            # MySQL SUM 返回 Decimal，统一转 int 避免 JSON 序列化为字符串
            confirmed, completed, failed = int(confirmed or 0), int(completed or 0), int(failed or 0)
            handled = confirmed + completed + failed
            items.append({
                "sales_name": sales_names.get(sales_id, "未知"),
                "follow_ups": follow_ups.get(sales_id, 0),
                "confirmed": confirmed,
                "completed": completed,
                "deals": deals.get(sales_id, 0),
                "confirm_rate": round(confirmed / handled * 100, 1) if handled else 0,
            })
        # 只有跟进没有预约处理的销售也纳入
        for sales_id, count in follow_ups.items():
            if not any(sales_id == a[0] for a in appt_stats):
                items.append({
                    "sales_name": sales_names.get(sales_id, "未知"),
                    "follow_ups": count, "confirmed": 0, "completed": 0,
                    "deals": deals.get(sales_id, 0), "confirm_rate": 0,
                })
        return sorted(items, key=lambda x: x["deals"], reverse=True)

    # ---- 客户 ----

    def customer(self, start: date, end: date) -> dict:
        """新增客户趋势 + 状态分布"""
        trend = self._daily_trend(Customer.created_at, start, end)
        status_dist = [
            {"status": s, "label": label, "count": count}
            for s, label, count in self.db.execute(
                select(Customer.status, case(
                    (Customer.status == "new", "新线索"), (Customer.status == "following", "跟进中"),
                    (Customer.status == "test_driven", "已试驾"), (Customer.status == "deal", "已成交"),
                    else_=Customer.status), func.count())
                .group_by(Customer.status)
            ).all()
        ]
        return {"trend": trend, "status_dist": status_dist}

    # ---- 车型热度 ----

    def model_heat(self, start: date, end: date) -> list[dict]:
        """车型维度：浏览量/对比次数（热度表）+ 预约量，按浏览量降序"""
        stat_rows = self.db.execute(
            select(ModelStatDaily.model_id, func.sum(ModelStatDaily.view_count), func.sum(ModelStatDaily.compare_count))
            .where(ModelStatDaily.stat_date >= start, ModelStatDaily.stat_date <= end)
            .group_by(ModelStatDaily.model_id)
        ).all()
        appt_counts = dict(
            self.db.execute(
                select(Appointment.model_id, func.count())
                .where(func.date(Appointment.created_at) >= start, func.date(Appointment.created_at) <= end)
                .group_by(Appointment.model_id)
            ).all()
        )
        model_names = self._model_names([row[0] for row in stat_rows] + list(appt_counts))
        items = [
            {
                "model_name": model_names.get(model_id, "未知"),
                "views": views or 0,
                "compares": compares or 0,
                "appointments": appt_counts.get(model_id, 0),
            }
            for model_id, views, compares in stat_rows
        ]
        # 只有预约无热度记录的车型也纳入
        for model_id, count in appt_counts.items():
            if not any(row[0] == model_id for row in stat_rows):
                items.append({"model_name": model_names.get(model_id, "未知"),
                              "views": 0, "compares": 0, "appointments": count})
        return sorted(items, key=lambda x: x["views"], reverse=True)

    # ---- 导出 ----

    def export(self, report_type: str, start: date, end: date, fmt: str, operator_id: int) -> dict:
        """导出报表为 Excel/CSV，写审计日志，返回下载地址"""
        headers, rows = self._export_rows(report_type, start, end)
        export_dir = Path(settings.EXPORT_DIR)
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{report_type}-{uuid.uuid4().hex[:12]}"
        if fmt == "excel":
            path = export_dir / f"{filename}.xlsx"
            self._write_excel(path, headers, rows)
        else:
            path = export_dir / f"{filename}.csv"
            self._write_csv(path, headers, rows)
        # 导出行为审计留痕
        self.db.add(AuditLog(
            user_id=operator_id, action="export",
            detail=f"{report_type}/{fmt}/{start}~{end}",
        ))
        self.db.flush()
        return {"url": f"/exports/{path.name}"}

    def _export_rows(self, report_type: str, start: date, end: date) -> tuple[list[str], list[list]]:
        """取报表数据并展平为 (表头, 数据行)"""
        headers = REPORT_COLUMNS[report_type]
        if report_type == "booking":
            data = self.booking(start, end)
            return headers, [[row["date"], row["count"]] for row in data["trend"]]
        if report_type == "sales":
            return headers, [[r["sales_name"], r["follow_ups"], r["confirmed"], r["completed"], r["deals"], f"{r['confirm_rate']}%"]
                             for r in self.sales(start, end)]
        if report_type == "customer":
            data = self.customer(start, end)
            return headers, [[row["date"], row["count"]] for row in data["trend"]]
        data = self.model_heat(start, end)
        return headers, [[r["model_name"], r["views"], r["compares"], r["appointments"]] for r in data]

    @staticmethod
    def _write_excel(path: Path, headers: list[str], rows: list[list]) -> None:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "报表"
        ws.append(headers)
        for row in rows:
            ws.append(row)
        wb.save(path)

    @staticmethod
    def _write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
        # utf-8-sig 保证 Excel 打开中文不乱码
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

    # ---- 内部工具 ----

    def _daily_trend(self, date_column, start: date, end: date) -> list[dict]:
        """按天聚合计数，补零缺失日期，保证图表连续"""
        rows = dict(
            self.db.execute(
                select(func.date(date_column), func.count())
                .where(func.date(date_column) >= start, func.date(date_column) <= end)
                .group_by(func.date(date_column))
            ).all()
        )
        result = []
        current = start
        while current <= end:
            key = current.strftime("%Y-%m-%d")
            result.append({"date": key, "count": rows.get(key, 0)})
            current += timedelta(days=1)
        return result

    def _user_names(self, user_ids: list[int]) -> dict[int, str]:
        ids = set(user_ids)
        if not ids:
            return {}
        rows = self.db.execute(select(User.id, User.name).where(User.id.in_(ids)))
        return {row[0]: row[1] for row in rows.all()}

    def _model_names(self, model_ids: list[int]) -> dict[int, str]:
        ids = set(model_ids)
        if not ids:
            return {}
        rows = self.db.execute(select(CarModel.id, CarModel.name).where(CarModel.id.in_(ids)))
        return {row[0]: row[1] for row in rows.all()}


def default_range() -> tuple[date, date]:
    """默认统计范围：近 30 天（含今天）"""
    today = date.today()
    return today - timedelta(days=29), today
