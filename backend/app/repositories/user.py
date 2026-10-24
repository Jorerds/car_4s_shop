"""数据访问层：用户表查询封装，Service 层不直接写 SQLAlchemy 查询"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """用户数据访问：按标识查询与创建"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        """按账号查询用户（销售/管理员登录用）"""
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_phone(self, phone: str) -> User | None:
        """按手机号查询用户（顾客登录用）"""
        stmt = select(User).where(User.phone == phone)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, user: User) -> User:
        """新增用户并落库"""
        self.db.add(user)
        self.db.flush()
        return user
