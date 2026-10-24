"""Pydantic 模型：销售端确认/拒绝/试驾记录与通知"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.testdrive import _not_blank


class ConfirmRequest(BaseModel):
    """确认预约并分配试驾车"""
    vehicle_id: int = Field(gt=0)


class RejectRequest(BaseModel):
    """拒绝预约（必填原因）"""
    model_config = ConfigDict(validate_default=True)

    reason: Annotated[str | None, _not_blank("拒绝原因")] = None


class RecordRequest(BaseModel):
    """登记试驾结果：完成（可带评分与文字反馈）或爽约"""
    model_config = ConfigDict(validate_default=True)

    result: Literal["completed", "no_show"]
    feedback_score: int | None = Field(default=None, ge=1, le=5)
    feedback_text: str | None = Field(default=None, max_length=500)


class SalesAppointmentItem(BaseModel):
    """销售端预约列表项"""
    id: int
    model_id: int
    model_name: str
    customer_name: str
    customer_phone: str
    slot_date: str
    time_slot: str
    status: str
    remark: str | None
    vehicle_plate: str | None
    reject_reason: str | None
    created_at: str
