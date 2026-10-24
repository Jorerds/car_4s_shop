"""pytest 公共夹具：测试库用内存 SQLite，通过依赖覆盖注入，隔离外部服务"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app

# 内存 SQLite + StaticPool：多连接共享同一份内存数据，保证事务可见性
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def init_database():
    """测试会话级初始化：创建全部表结构"""
    Base.metadata.create_all(test_engine)
    yield


@pytest.fixture()
def db_session():
    """单个测试用例的独立数据库会话，用例结束回滚保证隔离"""
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db_session):
    """FastAPI 测试客户端：数据库依赖覆盖为测试会话"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
