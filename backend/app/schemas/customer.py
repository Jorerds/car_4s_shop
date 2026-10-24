"""Pydantic 模型：客户跟进与账号管理"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.testdrive import _not_blank


class FollowUpCreateRequest(BaseModel):
    """添加跟进记录"""
    model_config = ConfigDict(validate_default=True)

    type: Literal["phone", "visit", "test_drive", "deal"]
    content: Annotated[str | None, _not_blank("跟进内容")] = None
    next_follow_at: datetime | None = None


class CustomerItem(BaseModel):
    """客户列表项"""
    id: int
    name: str
    phone: str
    status: str
    status_text: str
    sales_name: str | None
    created_at: str


class FollowUpItem(BaseModel):
    """跟进记录（时间线条目）"""
    id: int
    type: str
    type_text: str
    content: str
    sales_name: str
    next_follow_at: str | None
    created_at: str


class CustomerDetail(BaseModel):
    """客户详情：基本信息 + 预约 + 试驾 + 跟进时间线"""
    id: int
    name: str
    phone: str
    status: str
    status_text: str
    sales_name: str | None
    appointments: list[dict]
    follow_ups: list[FollowUpItem]


class UserCreateRequest(BaseModel):
    """创建销售/管理员账号"""
    model_config = ConfigDict(validate_default=True)

    username: Annotated[str | None, _not_blank("账号")] = None
    password: Annotated[str | None, _not_blank("密码")] = None
    name: Annotated[str | None, _not_blank("姓名")] = None
    role: Literal["sales", "admin"] = "sales"


class UserItem(BaseModel):
    """账号列表项"""
    id: int
    username: str
    name: str
    role: str
    status: str
    created_at: str
