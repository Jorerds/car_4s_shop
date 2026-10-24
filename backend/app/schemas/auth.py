"""Pydantic 模型：认证接口请求/响应定义"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict

from app.schemas.testdrive import _not_blank


class AccountLoginRequest(BaseModel):
    """账号密码登录请求：字段为空时给出中文提示"""
    # validate_default：字段缺失时默认值也要走校验，否则空请求体会漏过非空检查
    model_config = ConfigDict(validate_default=True)

    username: Annotated[str | None, _not_blank("账号")] = None
    password: Annotated[str | None, _not_blank("密码")] = None


class LoginUser(BaseModel):
    """登录响应中的用户信息"""
    id: int
    name: str | None
    role: str


class LoginResponse(BaseModel):
    """登录响应：JWT 令牌 + 用户信息"""
    token: str
    user: LoginUser
