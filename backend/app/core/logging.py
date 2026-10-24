"""日志模块：loguru 结构化 JSON 日志，统一拦截 stdlib logging"""

import logging
import sys

from loguru import logger


def setup_logging() -> None:
    """初始化全局日志：JSON 格式输出到 stdout，兼容 uvicorn 等第三方库日志"""

    # 移除 loguru 默认 handler
    logger.remove()

    # 业务日志（JSON 结构化，便于检索与追踪 request_id）
    logger.add(
        sys.stdout,
        serialize=True,
        level="INFO",
        format="{message}",
    )

    # 将标准库 logging 转发到 loguru，统一日志出口
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
