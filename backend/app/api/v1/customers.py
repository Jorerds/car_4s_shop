"""客户跟进与账号管理路由"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_customer_service, get_user_admin_service, require_role
from app.core.db import get_db
from app.core.exceptions import ok
from app.schemas.customer import FollowUpCreateRequest, UserCreateRequest
from app.services.customer import CustomerService
from app.services.user_admin import UserAdminService

router = APIRouter(tags=["客户跟进与账号"])


@router.get("/sales/customers")
def list_customers(
    scope: str = Query(default="mine", pattern="^(mine|pool)$"),
    current_user: dict = Depends(require_role("sales", "admin")),
    service: CustomerService = Depends(get_customer_service),
) -> dict:
    """客户列表：mine 我的客户 / pool 公共池（未分配，可认领）"""
    return ok(service.list_customers(scope, current_user["id"]))


@router.post("/sales/customers/{customer_id}/claim")
def claim_customer(
    customer_id: int,
    current_user: dict = Depends(require_role("sales", "admin")),
    service: CustomerService = Depends(get_customer_service),
) -> dict:
    """认领公共池线索（先到先得）"""
    service.claim(customer_id, current_user["id"])
    return ok(message="认领成功")


@router.get("/sales/customers/{customer_id}")
def get_customer_detail(
    customer_id: int,
    current_user: dict = Depends(require_role("sales", "admin")),
    service: CustomerService = Depends(get_customer_service),
) -> dict:
    """客户详情：基本信息 + 预约记录 + 跟进时间线（非管理员仅自己的客户）"""
    return ok(service.detail(customer_id, current_user["id"], current_user["role"] == "admin"))


@router.post("/sales/customers/{customer_id}/follow-ups")
def add_follow_up(
    customer_id: int,
    body: FollowUpCreateRequest,
    current_user: dict = Depends(require_role("sales", "admin")),
    service: CustomerService = Depends(get_customer_service),
) -> dict:
    """添加跟进记录：按类型自动流转客户状态"""
    return ok(service.add_follow_up(customer_id, body, current_user["id"]))


@router.put("/admin/customers/{customer_id}/assign")
def assign_customer(
    customer_id: int,
    sales_id: int = Query(gt=0),
    _: dict = Depends(require_role("admin")),
    service: CustomerService = Depends(get_customer_service),
) -> dict:
    """管理员分配线索给销售"""
    service.assign(customer_id, sales_id)
    return ok(message="分配成功")


@router.get("/admin/users")
def list_users(
    _: dict = Depends(require_role("admin")),
    service: UserAdminService = Depends(get_user_admin_service),
) -> dict:
    """账号列表（销售/管理员）"""
    return ok(service.list_users())


@router.post("/admin/users")
def create_user(
    body: UserCreateRequest,
    _: dict = Depends(require_role("admin")),
    service: UserAdminService = Depends(get_user_admin_service),
) -> dict:
    """创建销售/管理员账号"""
    return ok(service.create_user(body))


@router.put("/admin/users/{user_id}/status")
def set_user_status(
    user_id: int,
    status: str = Query(pattern="^(active|disabled)$"),
    _: dict = Depends(require_role("admin")),
    service: UserAdminService = Depends(get_user_admin_service),
) -> dict:
    """启用/停用账号"""
    service.set_status(user_id, status)
    return ok(message="更新成功")
