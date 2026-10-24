"""应用入口：FastAPI 实例创建、中间件与路由注册"""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging

setup_logging()

# 上传目录（车型图片）本地开发由后端直出，生产由 Nginx 直出
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True)


def create_app() -> FastAPI:
    """应用工厂：集中注册异常处理、路由与静态资源"""
    app = FastAPI(title=settings.APP_NAME, docs_url="/api/docs", openapi_url="/api/openapi.json")
    register_exception_handlers(app)
    app.include_router(api_router)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
    app.mount("/exports", StaticFiles(directory=settings.EXPORT_DIR), name="exports")
    return app


app = create_app()
