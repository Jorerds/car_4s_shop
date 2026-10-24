"""C 端车型路由：列表（筛选/排序/分页）、详情、筛选项——全部公开访问"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_car_model_service
from app.core.exceptions import ok
from app.schemas.car_model import CompareRequest
from app.services.car_model import CarModelService

router = APIRouter(prefix="/models", tags=["车型-顾客端"])


@router.get("")
def list_models(
    brand: str | None = Query(default=None, max_length=30),
    energy_type: str | None = Query(default=None, max_length=20),
    body_type: str | None = Query(default=None, max_length=20),
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    sort: str = Query(default="newest", max_length=20),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """在售车型列表：品牌/能源/车身/价格区间筛选，价格或最新排序"""
    query = {
        "brand": brand, "energy_type": energy_type, "body_type": body_type,
        "min_price": min_price, "max_price": max_price,
        "sort": sort, "page": page, "page_size": page_size,
    }
    return ok(service.list_public(query))


@router.get("/filters")
def list_filters(
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """列表页筛选项：在售品牌去重"""
    return ok(service.list_filter_options())


@router.post("/compare")
def compare_models(
    body: CompareRequest,
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """车型对比：2-3 款参数对齐 + 差异标记，同时记录对比热度"""
    return ok(service.compare(body.model_ids))


@router.post("/{model_id}/view")
def record_model_view(
    model_id: int,
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """记录车型详情浏览（热度埋点）"""
    service.record_view(model_id)
    return ok(message="ok")


@router.get("/{model_id}")
def get_model_detail(
    model_id: int,
    service: CarModelService = Depends(get_car_model_service),
) -> dict:
    """车型详情：图片集 + 六组配置（停售返回 404）"""
    return ok(service.get_public_detail(model_id))
