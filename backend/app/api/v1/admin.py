"""管理端车型路由：车型 CRUD、配置整体替换、图片维护——仅店管理员"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_car_model_service, require_role
from app.core.exceptions import ok
from app.schemas.car_model import (
    ConfigReplaceRequest,
    ImageAddRequest,
    ModelCreateRequest,
    ModelUpdateRequest,
)
from app.services.car_model import CarModelService

router = APIRouter(prefix="/admin/models", tags=["车型-管理端"])


@router.get("")
def admin_list_models(
    keyword: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    _: dict = Depends(require_role("admin")),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """管理端车型列表：全量状态 + 关键字搜索"""
    return ok(service.list_admin(keyword, page, page_size))


@router.get("/{model_id}")
def admin_get_model(
    model_id: int,
    _: dict = Depends(require_role("admin")),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """管理端详情：含停售车的完整信息（图片/配置/状态）"""
    return ok(service.admin_detail(model_id))


@router.post("")
def admin_create_model(
    body: ModelCreateRequest,
    _: dict = Depends(require_role("admin")),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """创建车型"""
    return ok(service.create(body))


@router.put("/{model_id}")
def admin_update_model(
    model_id: int,
    body: ModelUpdateRequest,
    _: dict = Depends(require_role("admin")),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """更新车型信息与销售状态"""
    service.update(model_id, body)
    return ok(message="更新成功")


@router.put("/{model_id}/configs")
def admin_replace_configs(
    model_id: int,
    body: ConfigReplaceRequest,
    _: dict = Depends(require_role("admin")),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """配置参数整体替换（六组键值对）"""
    service.replace_configs(model_id, body.configs)
    return ok(message="保存成功")


@router.post("/{model_id}/images")
def admin_add_image(
    model_id: int,
    body: ImageAddRequest,
    _: dict = Depends(require_role("admin")),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """为车型添加图片，is_main=true 时自动取消原主图"""
    return ok(service.add_image(model_id, body))


@router.put("/{model_id}/images/{image_id}/main")
def admin_set_main_image(
    model_id: int,
    image_id: int,
    _: dict = Depends(require_role("admin")),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """设置主图"""
    service.set_main_image(model_id, image_id)
    return ok(message="设置成功")


@router.delete("/{model_id}/images/{image_id}")
def admin_delete_image(
    model_id: int,
    image_id: int,
    _: dict = Depends(require_role("admin")),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """删除车型图片"""
    service.delete_image(model_id, image_id)
    return ok(message="删除成功")
