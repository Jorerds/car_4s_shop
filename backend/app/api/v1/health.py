"""健康检查路由：容器编排与监控探活使用"""

from fastapi import APIRouter

from app.core.config import settings
from app.core.exceptions import ok

router = APIRouter(tags=["健康检查"])


@router.get("/health")
def health() -> dict:
    """返回服务名与运行状态（统一响应格式，供编排探活与监控使用）"""
    return ok({"status": "ok", "app": settings.APP_NAME})
