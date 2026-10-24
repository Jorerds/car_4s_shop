"""短信服务抽象：接口定义、模拟实现与按配置选择实现"""

from app.core.config import settings


class SmsSender:
    """短信发送接口：所有实现必须提供这两个方法"""

    def send_code(self, phone: str, code: str) -> bool:
        """发送登录/预约验证码"""
        raise NotImplementedError

    def send_notify(self, phone: str, template: str, params: dict) -> bool:
        """发送业务通知（预约确认/拒绝等）"""
        raise NotImplementedError


class MockSmsSender(SmsSender):
    """开发模拟实现：短信写入结构化日志，同时落 Redis 供测试读取验证码"""

    def send_code(self, phone: str, code: str) -> bool:
        from app.tasks.celery_app import logger
        logger.info(f"[MOCK SMS] code to {phone}: {code}")
        _store_code_in_redis(phone, code)
        return True

    def send_notify(self, phone: str, template: str, params: dict) -> bool:
        from app.tasks.celery_app import logger
        logger.info(f"[MOCK SMS] notify to {phone}, template={template}, params={params}")
        return True


def _store_code_in_redis(phone: str, code: str) -> None:
    """验证码写入 Redis（TTL 5 分钟），模拟实现也走真实存储，便于联调"""
    import redis
    client = redis.Redis.from_url(settings.REDIS_URL)
    client.setex(f"sms:code:{phone}", 300, code)


def get_sms_sender() -> SmsSender:
    """按配置选择短信实现：mock / aliyun / tencent"""
    if settings.SMS_PROVIDER == "mock":
        return MockSmsSender()
    raise ValueError(f"未知短信服务商: {settings.SMS_PROVIDER}（aliyun/tencent 实现待接入）")
