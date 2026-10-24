"""预约路由：提交预约（游客/登录顾客）、我的预约、取消"""

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_appointment_service,
    get_current_user_optional,
    require_role,
)
from app.core.exceptions import ok
from app.schemas.testdrive import AppointmentCreateRequest
from app.services.appointment import AppointmentService

router = APIRouter(prefix="/appointments", tags=["预约试驾"])


@router.post("")
def create_appointment(
    body: AppointmentCreateRequest,
    current_user: dict | None = Depends(get_current_user_optional),
    service: AppointmentService = Depends(get_appointment_service),
) -> dict:
    """提交预约：游客需短信验证码，登录顾客免验证码"""
    return ok(service.create(body, current_user))


@router.get("/mine")
def list_my_appointments(
    current_user: dict = Depends(require_role("customer")),
    service: AppointmentService = Depends(get_appointment_service),
) -> dict:
    """我的预约列表（登录顾客）"""
    return ok({"items": service.list_mine(current_user["phone"]) if current_user.get("phone") else []})


@router.post("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    current_user: dict = Depends(require_role("customer")),
    service: AppointmentService = Depends(get_appointment_service),
) -> dict:
    """取消预约：开始前 2 小时外可取消，名额自动释放"""
    service.cancel(appointment_id, current_user["phone"])
    return ok(message="取消成功")
