"""车型相关 ORM 模型：车型主表、图片集、配置参数（键值对）"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class CarModel(Base):
    """车型主表：基础信息与销售状态"""

    __tablename__ = "car_model"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), index=True)          # 车型名称
    brand: Mapped[str] = mapped_column(String(30), index=True)         # 品牌
    series: Mapped[str] = mapped_column(String(30))                    # 车系
    guide_price: Mapped[int] = mapped_column(Integer)                  # 指导价（元）
    body_type: Mapped[str] = mapped_column(String(20), index=True)     # 车身类型：轿车/SUV/MPV 等
    energy_type: Mapped[str] = mapped_column(String(20), index=True)   # 能源类型：燃油/纯电/混动/增程 等
    status: Mapped[str] = mapped_column(String(20), default="on_sale")  # on_sale 在售 / off_sale 停售
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 图片与配置随车型一同加载/级联删除
    images: Mapped[list["CarModelImage"]] = relationship(
        back_populates="model", cascade="all, delete-orphan", order_by="CarModelImage.sort"
    )
    configs: Mapped[list["CarModelConfig"]] = relationship(
        back_populates="model", cascade="all, delete-orphan", order_by="CarModelConfig.id"
    )


class CarModelImage(Base):
    """车型图片集：主图 + 多图，sort 控制展示顺序"""

    __tablename__ = "car_model_image"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("car_model.id"), index=True)
    url: Mapped[str] = mapped_column(String(255))                  # 图片访问路径，如 /uploads/xxx.png
    is_main: Mapped[bool] = mapped_column(default=False)           # 是否主图（列表/卡片用）
    sort: Mapped[int] = mapped_column(Integer, default=0)          # 展示顺序，小在前

    model: Mapped[CarModel] = relationship(back_populates="images")


class CarModelConfig(Base):
    """车型配置参数：六组键值对（动力/底盘/车身/安全/舒适/科技）"""

    __tablename__ = "car_model_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("car_model.id"), index=True)
    group_name: Mapped[str] = mapped_column(String(20))   # 分组：动力/底盘/车身/安全/舒适/科技
    param_name: Mapped[str] = mapped_column(String(50))   # 参数名
    param_value: Mapped[str] = mapped_column(String(100)) # 参数值

    model: Mapped[CarModel] = relationship(back_populates="configs")
