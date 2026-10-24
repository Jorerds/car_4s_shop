"""短信异步任务：投递 Celery 队列，避免阻塞请求线程"""

from app.integrations.sms import get_sms_sender
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="sms.send_code")
def send_code_task(self, phone: str, code: str) -> bool:
    """异步发送验证码，失败自动重试"""
    try:
        return get_sms_sender().send_code(phone, code)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, name="sms.send_notify")
def send_notify_task(self, phone: str, template: str, params: dict) -> bool:
    """异步发送业务通知短信，失败自动重试"""
    try:
        return get_sms_sender().send_notify(phone, template, params)
    except Exception as exc:
        raise self.retry(exc=exc)
