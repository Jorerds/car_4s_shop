"""Redis 客户端：单例懒加载，供验证码、缓存等使用"""

import redis

from app.core.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """获取全局 Redis 客户端（decode_responses 便于存取字符串）"""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client
