"""应用配置模块：集中管理环境变量与应用配置，支持 .env 覆盖"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 位于项目根目录（backend/app/core/config.py 向上 3 层），
# 固定绝对定位，避免依赖执行目录导致读不到配置
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置：数据库、Redis、JWT、短信服务商等"""

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    # 应用
    APP_NAME: str = "4S店线上车辆展示与预约试驾系统"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = "mysql+pymysql://root:root@127.0.0.1:3306/ai_4s?charset=utf8mb4"

    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 12

    # 短信服务商：mock=开发模拟 / aliyun / tencent（上线前切换）
    SMS_PROVIDER: str = "mock"

    # 文件存储：默认锚定项目根目录，避免依赖执行目录导致路径漂移
    UPLOAD_DIR: str = str(PROJECT_ROOT / "data" / "uploads")
    EXPORT_DIR: str = str(PROJECT_ROOT / "data" / "exports")


# 全局单例，避免重复解析
settings = Settings()
