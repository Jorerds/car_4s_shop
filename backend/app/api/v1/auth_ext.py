"""认证路由扩展：短信验证码发送、手机号登录（顾客端）"""

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service, get_sms_code_service
from app.core.config import settings
from app.core.exceptions import ok
from app.schemas.auth import LoginResponse
from app.schemas.testdrive import PhoneLoginRequest, SmsCodeRequest
from app.services.auth import AuthService
from app.services.sms_code import SmsCodeService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/sms-code")
def send_sms_code(
    body: SmsCodeRequest,
    sms_code: SmsCodeService = Depends(get_sms_code_service),
) -> dict:
    """发送短信验证码（60 秒重发限制、单日 10 条上限）

    mock 短信模式下返回 dev_code 便于开发调试，生产模式不返回
    """
    code = sms_code.send_code(body.phone)
    data = {"sent": True}
    if settings.SMS_PROVIDER == "mock":
        data["dev_code"] = code
    return ok(data)


@router.post("/login-by-phone", response_model=None)
def login_by_phone(
    body: PhoneLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    sms_code: SmsCodeService = Depends(get_sms_code_service),
) -> dict:
    """顾客手机号 + 验证码登录（验证通过即销毁，自动注册）"""
    sms_code.verify_code(body.phone, body.code)
    return ok(LoginResponse(**auth_service.login_by_phone(body.phone)).model_dump())
