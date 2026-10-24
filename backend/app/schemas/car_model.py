"""Pydantic 模型：车型接口请求/响应定义"""

from pydantic import BaseModel, ConfigDict, Field

# 配置参数六分组（PRD 3.3），前后端共用的合法取值
CONFIG_GROUPS = ("动力", "底盘", "车身", "安全", "舒适", "科技")


class ModelCreateRequest(BaseModel):
    """管理端创建车型请求"""
    model_config = ConfigDict(validate_default=True)

    name: str = Field(min_length=1, max_length=50)
    brand: str = Field(min_length=1, max_length=30)
    series: str = Field(min_length=1, max_length=30)
    guide_price: int = Field(gt=0, description="指导价（元）")
    body_type: str = Field(min_length=1, max_length=20)
    energy_type: str = Field(min_length=1, max_length=20)


class ModelUpdateRequest(ModelCreateRequest):
    """管理端更新车型请求：额外允许调整销售状态"""
    status: str = Field(default="on_sale", pattern="^(on_sale|off_sale)$")


class ModelListItem(BaseModel):
    """C 端车型列表项"""
    id: int
    name: str
    brand: str
    energy_type: str
    body_type: str
    guide_price: int
    main_image: str | None  # 主图 URL，无图时为 None


class ModelDetail(BaseModel):
    """C 端车型详情：基础信息 + 图片集 + 分组配置"""
    id: int
    name: str
    brand: str
    series: str
    guide_price: int
    body_type: str
    energy_type: str
    images: list[str]
    # 配置按六组分组：{ "动力": [{param_name, param_value}, ...], ... }
    configs: dict[str, list[dict[str, str]]]


class AdminModelListItem(ModelListItem):
    """管理端车型列表项：额外含车系与销售状态"""
    model_config = ConfigDict(from_attributes=True)

    series: str
    status: str


class CompareRequest(BaseModel):
    """车型对比请求：2-3 款车型 ID"""
    model_ids: list[int] = Field(min_length=2, max_length=3)


class ConfigItem(BaseModel):
    """单条配置参数"""
    group_name: str = Field(pattern="^(动力|底盘|车身|安全|舒适|科技)$")
    param_name: str = Field(min_length=1, max_length=50)
    param_value: str = Field(min_length=1, max_length=100)


class ConfigReplaceRequest(BaseModel):
    """配置整体替换请求：全量覆盖，避免差量合并的复杂度"""
    configs: list[ConfigItem] = Field(max_length=200)


class ImageAddRequest(BaseModel):
    """为车型添加图片"""
    url: str = Field(min_length=1, max_length=255)
    is_main: bool = False
    sort: int = 0


class ImageItem(BaseModel):
    """图片信息"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    is_main: bool
    sort: int
