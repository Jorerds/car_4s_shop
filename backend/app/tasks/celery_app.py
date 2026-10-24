"""Celery 应用定义：Redis 为 Broker，异步执行短信发送、导出等耗时任务"""

from celery import Celery
from loguru import logger

from app.core.config import settings

celery_app = Celery(
    "ai_4s",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.sms"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    task_default_retry_delay=60,   # 失败默认 1 分钟后重试
    task_max_retries=3,            # 最多重试 3 次
)

__all__ = ["celery_app", "logger"]
