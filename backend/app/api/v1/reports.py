"""报表路由：四类统计查询与 Excel/CSV 导出（仅管理员）"""

from datetime import date

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import get_report_service, require_role
from app.core.exceptions import ok
from app.services.reports import ReportService, default_range

router = APIRouter(prefix="/reports", tags=["统计报表"])


def _range(start: date | None, end: date | None) -> tuple[date, date]:
    """日期范围缺省时取近 30 天"""
    default_start, default_end = default_range()
    return start or default_start, end or default_end


@router.get("/booking")
def booking_report(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    _: dict = Depends(require_role("admin")),
    service: ReportService = Depends(get_report_service),
) -> dict:
    """预约/转化：趋势 + 漏斗 + 爽约率"""
    s, e = _range(start, end)
    return ok(service.booking(s, e))


@router.get("/sales")
def sales_report(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    _: dict = Depends(require_role("admin")),
    service: ReportService = Depends(get_report_service),
) -> dict:
    """销售业绩：跟进量/确认/试驾完成/成交量排行"""
    s, e = _range(start, end)
    return ok({"items": service.sales(s, e)})


@router.get("/customer")
def customer_report(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    _: dict = Depends(require_role("admin")),
    service: ReportService = Depends(get_report_service),
) -> dict:
    """客户报表：新增趋势 + 状态分布"""
    s, e = _range(start, end)
    return ok(service.customer(s, e))


@router.get("/model")
def model_heat_report(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    _: dict = Depends(require_role("admin")),
    service: ReportService = Depends(get_report_service),
) -> dict:
    """车型热度：浏览/对比/预约排行"""
    s, e = _range(start, end)
    return ok({"items": service.model_heat(s, e)})


@router.post("/{report_type}/export")
def export_report(
    report_type: str = Path(pattern="^(booking|sales|customer|model)$"),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    format: str = Query(default="excel", pattern="^(excel|csv)$"),
    current_user: dict = Depends(require_role("admin")),
    service: ReportService = Depends(get_report_service),
) -> dict:
    """导出报表（Excel/CSV），写审计日志"""
    s, e = _range(start, end)
    return ok(service.export(report_type, s, e, format, current_user["id"]))
