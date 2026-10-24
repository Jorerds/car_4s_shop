"""Pydantic 模型：试驾资源与预约接口请求/响应定义"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from pydantic_core import PydanticCustomError

# 时段格式 HH:MM（粒度 1 小时）
TIME_SLOT_PATTERN = r"^([01]\d|2[0-3]):00$"


def _not_blank(label: str):
    """生成非空校验器：字段为空时抛出中文友好错误，而非 Pydantic 默认英文提示"""
    def validator(value: str | None) -> str:
        if value is None or not value.strip():
            raise PydanticCustomError("blank", f"{label}不能为空")
        return value.strip()
    # 必须显式包 BeforeValidator：裸函数放在 Annotated 元数据中不会被 Pydantic 自动应用
    return BeforeValidator(validator)


class VehicleCreateRequest(BaseModel):
    """创建试驾车"""
    plate_no: str = Field(min_length=5, max_length=20)
    model_id: int = Field(gt=0)


class VehicleUpdateRequest(BaseModel):
    """更新试驾车状态"""
    status: str = Field(pattern="^(available|disabled)$")


class SlotBatchGenerateRequest(BaseModel):
    """批量生成试驾时段：指定日期列表与小时时段"""
    model_config = ConfigDict(validate_default=True)

    model_id: int = Field(gt=0)
    dates: list[date] = Field(min_length=1, max_length=31)
    time_slots: list[str] = Field(min_length=1, max_length=12)
    capacity: int = Field(default=1, ge=1, le=20)


class SmsCodeRequest(BaseModel):
    """发送短信验证码"""
    phone: str = Field(pattern=r"^1\d{10}$")


class PhoneLoginRequest(BaseModel):
    """手机号 + 验证码登录"""
    phone: str = Field(pattern=r"^1\d{10}$")
    code: str = Field(min_length=4, max_length=6)


class AppointmentCreateRequest(BaseModel):
    """提交预约：游客必须带验证码，登录顾客免验证码"""
    model_config = ConfigDict(validate_default=True)

    model_id: int = Field(gt=0)
    slot_id: int = Field(gt=0)
    customer_name: Annotated[str | None, _not_blank("姓名")] = None
    phone: str = Field(pattern=r"^1\d{10}$")
    code: str | None = Field(default=None, min_length=4, max_length=6)
    remark: str | None = Field(default=None, max_length=200)
