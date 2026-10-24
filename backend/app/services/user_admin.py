"""账号管理业务：管理员创建/停用销售与管理员账号"""

from sqlalchemy import select

from app.core.exceptions import BizException
from app.core.security import hash_password
from app.models.user import User
from app.schemas.customer import UserCreateRequest, UserItem
from sqlalchemy.orm import Session


class UserAdminService:
    """账号管理用例（仅管理员）"""

    def __init__(self, db: Session):
        self.db = db

    def list_users(self) -> dict:
        """账号列表：销售与管理员（不含顾客）"""
        users = list(self.db.scalars(
            select(User).where(User.role.in_(["sales", "admin"])).order_by(User.id.desc())
        ).all())
        return {
            "items": [
                UserItem(
                    id=u.id, username=u.username or "", name=u.name or "",
                    role=u.role, status=u.status,
                    created_at=u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
                ).model_dump()
                for u in users
            ]
        }

    def create_user(self, body: UserCreateRequest) -> dict:
        """创建账号：账号唯一，密码哈希存储"""
        exists = self.db.scalar(select(User).where(User.username == body.username))
        if exists:
            raise BizException(code=400, message="账号已存在")
        user = User(
            role=body.role, username=body.username,
            password_hash=hash_password(body.password), name=body.name, status="active",
        )
        self.db.add(user)
        self.db.flush()
        return {"id": user.id}

    def set_status(self, user_id: int, status: str) -> None:
        """启用/停用账号（不能停用自己，避免管理员自锁）"""
        user = self.db.get(User, user_id)
        if user is None or user.role not in ("sales", "admin"):
            raise BizException(code=404, message="账号不存在", http_status=404)
        if status == "disabled" and user.username == "admin":
            raise BizException(code=400, message="内置管理员账号不可停用")
        user.status = status
        self.db.flush()
