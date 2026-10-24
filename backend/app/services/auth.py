"""业务逻辑层：认证相关用例（账号密码登录、手机号登录），不感知 HTTP 细节"""

from app.core.exceptions import BizException
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user import UserRepository


class AuthService:
    """认证业务逻辑：校验凭证并签发令牌"""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def login_by_account(self, username: str, password: str) -> dict:
        """销售/管理员账号密码登录，成功返回 JWT 与用户信息"""
        user = self.user_repo.get_by_username(username)
        # 用户不存在或密码不匹配时给出统一提示，避免账号枚举
        if user is None or not verify_password(password, user.password_hash or ""):
            raise BizException(code=1001, message="账号或密码错误", http_status=401)
        if user.status != "active":
            raise BizException(code=1002, message="账号已停用", http_status=403)
        if user.role not in ("sales", "admin"):
            raise BizException(code=1003, message="请使用顾客端手机号登录", http_status=403)

        token = create_access_token(user.id, user.role)
        return {
            "token": token,
            "user": {"id": user.id, "name": user.name, "role": user.role},
        }

    def login_by_phone(self, phone: str) -> dict:
        """顾客手机号登录：无账号则自动注册（验证码在路由层校验）"""
        user = self.user_repo.get_by_phone(phone)
        if user is None:
            user = self.user_repo.create(User(role="customer", phone=phone, name="顾客", status="active"))
        if user.status != "active":
            raise BizException(code=1002, message="账号已停用", http_status=403)

        token = create_access_token(user.id, user.role)
        return {
            "token": token,
            "user": {"id": user.id, "name": user.name, "role": user.role},
        }
