"""销售端路由：预约确认/拒绝/试驾记录、可分配车辆、站内通知"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_sales_service, require_role
from app.core.exceptions import ok
from app.schemas.sales import ConfirmRequest, RecordRequest, RejectRequest
from app.services.sales import SalesService

router = APIRouter(tags=["销售端"])


@router.get("/sales/appointments")
def list_sales_appointments(
    status: str = Query(default="pending", pattern="^(pending|confirmed|finished|rejected|cancelled)$"),
    current_user: dict = Depends(require_role("sales", "admin")),
    service: SalesService = Depends(get_sales_service),
) -> dict:
    """预约列表：待确认为公共池，其余仅看自己处理的"""
    return ok(service.list_appointments(status, current_user["id"]))


@router.get("/sales/vehicles")
def list_assignable_vehicles(
    model_id: int = Query(gt=0),
    current_user: dict = Depends(require_role("sales", "admin")),
    service: SalesService = Depends(get_sales_service),
) -> dict:
    """某车型可分配的试驾车（可用状态）"""
    return ok(service.list_assignable_vehicles(model_id))


@router.post("/sales/appointments/{appointment_id}/confirm")
def confirm_appointment(
    appointment_id: int,
    body: ConfirmRequest,
    current_user: dict = Depends(require_role("sales", "admin")),
    service: SalesService = Depends(get_sales_service),
) -> dict:
    """确认预约并分配试驾车（同时段车辆唯一）"""
    service.confirm(appointment_id, body.vehicle_id, current_user["id"])
    return ok(message="已确认并通知顾客")


@router.post("/sales/appointments/{appointment_id}/reject")
def reject_appointment(
    appointment_id: int,
    body: RejectRequest,
    current_user: dict = Depends(require_role("sales", "admin")),
    service: SalesService = Depends(get_sales_service),
) -> dict:
    """拒绝预约（释放名额并通知顾客）"""
    service.reject(appointment_id, body.reason, current_user["id"])
    return ok(message="已拒绝并通知顾客")


@router.post("/sales/appointments/{appointment_id}/record")
def record_test_drive(
    appointment_id: int,
    body: RecordRequest,
    current_user: dict = Depends(require_role("sales", "admin")),
    service: SalesService = Depends(get_sales_service),
) -> dict:
    """登记试驾结果：完成（含反馈）或爽约"""
    service.record(appointment_id, body, current_user["id"])
    return ok(message="登记成功")


@router.get("/notifications/mine")
def list_my_notifications(
    current_user: dict = Depends(require_role("customer")),
    service: SalesService = Depends(get_sales_service),
) -> dict:
    """我的站内通知（顾客，含未读数）"""
    return ok(service.list_notifications(current_user["phone"]))


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(require_role("customer")),
    service: SalesService = Depends(get_sales_service),
) -> dict:
    """标记通知已读"""
    service.mark_read(notification_id, current_user["phone"])
    return ok(message="ok")
