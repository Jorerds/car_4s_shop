"""数据库连接与会话管理：引擎创建与依赖注入用 Session"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# 连接池默认配置，单店规模足够
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类，Alembic 自动迁移以此为扫描入口"""


def get_db() -> Session:
    """FastAPI 依赖注入：请求级数据库会话，异常时回滚，结束后关闭"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
