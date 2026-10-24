"""试驾时段路由：C 端可约时段查询；管理端试驾车维护与时段批量生成"""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_testdrive_service, require_role
from app.core.exceptions import ok
from app.schemas.testdrive import (
    SlotBatchGenerateRequest,
    VehicleCreateRequest,
    VehicleUpdateRequest,
)
from app.services.testdrive import TestDriveService

# C 端公开接口
public_router = APIRouter(tags=["试驾时段-顾客端"])


@public_router.get("/slots")
def list_available_slots(
    model_id: int = Query(gt=0),
    date: date = Query(),
    service: TestDriveService = Depends(get_testdrive_service),
) -> dict:
    """某日可约时段（仅返回有余量的）"""
    return ok({"items": service.list_available_slots(model_id, date)})


# 管理端接口
admin_router = APIRouter(prefix="/admin", tags=["试驾资源-管理端"])


@admin_router.get("/vehicles")
def admin_list_vehicles(
    _: dict = Depends(require_role("admin")),
    service: TestDriveService = Depends(get_testdrive_service),
) -> dict:
    """试驾车列表"""
    return ok({"items": service.list_vehicles()})


@admin_router.post("/vehicles")
def admin_create_vehicle(
    body: VehicleCreateRequest,
    _: dict = Depends(require_role("admin")),
    service: TestDriveService = Depends(get_testdrive_service),
) -> dict:
    """新增试驾车"""
    return ok(service.create_vehicle(body))


@admin_router.put("/vehicles/{vehicle_id}")
def admin_update_vehicle(
    vehicle_id: int,
    body: VehicleUpdateRequest,
    _: dict = Depends(require_role("admin")),
    service: TestDriveService = Depends(get_testdrive_service),
) -> dict:
    """更新试驾车状态（可用/停用）"""
    service.update_vehicle_status(vehicle_id, body.status)
    return ok(message="更新成功")


@admin_router.post("/slots/batch")
def admin_batch_generate_slots(
    body: SlotBatchGenerateRequest,
    _: dict = Depends(require_role("admin")),
    service: TestDriveService = Depends(get_testdrive_service),
) -> dict:
    """批量生成试驾时段（已存在的跳过）"""
    return ok(service.batch_generate_slots(body))


@admin_router.get("/slots")
def admin_list_day_slots(
    model_id: int = Query(gt=0),
    date: date = Query(),
    _: dict = Depends(require_role("admin")),
    service: TestDriveService = Depends(get_testdrive_service),
) -> dict:
    """某日全部时段（含已约满，管理端视角）"""
    return ok({"items": service.list_day_slots(model_id, date)})
