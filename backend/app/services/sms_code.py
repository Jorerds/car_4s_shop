"""短信验证码服务：发送（防刷限频）与校验，存储后端可插拔（Redis / 内存）

测试环境注入内存存储，避免依赖外部 Redis；生产走 Redis
"""

import random
import time
from typing import Protocol

from app.core.exceptions import BizException
from app.core.redis import get_redis
from app.integrations.sms import get_sms_sender

CODE_TTL_SECONDS = 300        # 验证码有效期 5 分钟
RESEND_INTERVAL = 60          # 同号码重发间隔 60 秒
DAILY_LIMIT = 10              # 同号码单日上限
VERIFY_MAX_ATTEMPTS = 5       # 连续校验失败次数上限，超限验证码作废


class CodeStore(Protocol):
    """验证码存储接口：生产 Redis 实现，测试内存实现"""

    def set(self, key: str, value: str, ttl: int) -> None: ...
    def get(self, key: str) -> str | None: ...
    def delete(self, key: str) -> None: ...
    def incr(self, key: str, ttl: int) -> int: ...


class RedisCodeStore:
    """Redis 存储实现：验证码 + 限频计数"""

    def __init__(self):
        self.redis = get_redis()

    def set(self, key: str, value: str, ttl: int) -> None:
        self.redis.setex(key, ttl, value)

    def get(self, key: str) -> str | None:
        return self.redis.get(key)

    def delete(self, key: str) -> None:
        self.redis.delete(key)

    def incr(self, key: str, ttl: int) -> int:
        # 首次计数时设置过期（当日有效）
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, ttl)
        return count


class DictCodeStore:
    """内存存储实现：仅用于测试，不保证多进程一致性"""

    def __init__(self):
        self._data: dict[str, tuple[str, float]] = {}
        self._counters: dict[str, tuple[int, float]] = {}

    def set(self, key: str, value: str, ttl: int) -> None:
        self._data[key] = (value, time.time() + ttl)

    def get(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None or item[1] < time.time():
            self._data.pop(key, None)
            return None
        return item[0]

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def incr(self, key: str, ttl: int) -> int:
        item = self._counters.get(key)
        count = 1 if item is None or item[1] < time.time() else item[0] + 1
        self._counters[key] = (count, time.time() + ttl)
        return count


def _key(phone: str) -> str:
    return f"sms:code:{phone}"


class SmsCodeService:
    """验证码业务：限频发送 + 防爆破校验"""

    def __init__(self, store: CodeStore | None = None):
        self.store = store or RedisCodeStore()

    def send_code(self, phone: str) -> str:
        """发送验证码：返回验证码（mock 模式下供开发调试，生产短信通道送达）"""
        # 限频：60 秒内仅 1 条
        if self.store.get(f"sms:lock:{phone}"):
            raise BizException(code=429, message="发送过于频繁，请 60 秒后再试", http_status=429)
        # 限频：单日上限
        day_count = self.store.incr(f"sms:day:{phone}", 86400)
        if day_count > DAILY_LIMIT:
            raise BizException(code=429, message="该手机号今日验证码已达上限", http_status=429)

        code = f"{random.randint(0, 999999):06d}"
        self.store.set(_key(phone), code, CODE_TTL_SECONDS)
        self.store.set(f"sms:lock:{phone}", "1", RESEND_INTERVAL)
        get_sms_sender().send_code(phone, code)
        return code

    def verify_code(self, phone: str, code: str) -> None:
        """校验验证码：通过即销毁；失败累计 5 次作废"""
        expected = self.store.get(_key(phone))
        if expected is None:
            raise BizException(code=400, message="验证码已过期，请重新获取")
        if expected != code:
            attempts = self.store.incr(f"sms:fail:{phone}", CODE_TTL_SECONDS)
            if attempts >= VERIFY_MAX_ATTEMPTS:
                self.store.delete(_key(phone))
            raise BizException(code=400, message="验证码错误")
        self.store.delete(_key(phone))
        self.store.delete(f"sms:fail:{phone}")
