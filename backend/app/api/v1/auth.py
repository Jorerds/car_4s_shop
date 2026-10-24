"""认证路由：验证码、手机号登录、账号密码登录"""

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service
from app.core.exceptions import ok
from app.schemas.auth import AccountLoginRequest, LoginResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login-by-account", response_model=None)
def login_by_account(
    body: AccountLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """销售/管理员账号密码登录，返回 JWT"""
    return ok(LoginResponse(**auth_service.login_by_account(body.username, body.password)).model_dump())
