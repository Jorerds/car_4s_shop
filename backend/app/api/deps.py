"""API 依赖注入：数据库会话、当前用户解析、角色鉴权"""

from collections.abc import Callable

import jwt
from fastapi import Depends, Header

from app.core.db import get_db
from app.core.exceptions import BizException
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.appointment import AppointmentRepository, CustomerRepository
from app.repositories.car_model import CarModelRepository
from app.repositories.sales import SalesRepository
from app.repositories.testdrive import TestDriveRepository
from app.repositories.user import UserRepository
from app.services.appointment import AppointmentService
from app.services.auth import AuthService
from app.services.car_model import CarModelService
from app.services.reports import ReportService
from app.services.customer import CustomerService
from app.services.sales import SalesService
from app.services.sms_code import SmsCodeService
from app.services.testdrive import TestDriveService
from app.services.user_admin import UserAdminService


def get_auth_service(db=Depends(get_db)) -> AuthService:
    """组装认证服务：注入用户仓储"""
    return AuthService(UserRepository(db))


def get_car_model_service(db=Depends(get_db)) -> CarModelService:
    """组装车型服务：注入车型仓储"""
    return CarModelService(CarModelRepository(db))


def get_sms_code_service() -> SmsCodeService:
    """组装验证码服务：默认 Redis 存储（测试用依赖覆盖为内存存储）"""
    return SmsCodeService()


def get_testdrive_service(db=Depends(get_db)) -> TestDriveService:
    """组装试驾资源服务"""
    return TestDriveService(TestDriveRepository(db))


def get_appointment_service(
    db=Depends(get_db), sms_code: SmsCodeService = Depends(get_sms_code_service)
) -> AppointmentService:
    """组装预约服务：注入预约/线索/时段仓储与验证码服务"""
    return AppointmentService(
        AppointmentRepository(db), CustomerRepository(db), TestDriveRepository(db), sms_code
    )


def get_sales_service(db=Depends(get_db)) -> SalesService:
    """组装销售端服务"""
    return SalesService(SalesRepository(db), TestDriveRepository(db))


def get_customer_service(db=Depends(get_db)) -> CustomerService:
    """组装客户跟进服务"""
    return CustomerService(CustomerRepository(db))


def get_user_admin_service(db=Depends(get_db)) -> UserAdminService:
    """组装账号管理服务"""
    return UserAdminService(db)


def get_report_service(db=Depends(get_db)) -> ReportService:
    """组装报表服务"""
    return ReportService(db)


def get_current_user(
    authorization: str = Header(default=""),
    db=Depends(get_db),
) -> dict:
    """解析 Bearer Token 为当前用户身份，无效则抛 401"""
    if not authorization.startswith("Bearer "):
        raise BizException(code=401, message="未登录或登录已过期", http_status=401)
    try:
        payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    except jwt.PyJWTError:
        raise BizException(code=401, message="未登录或登录已过期", http_status=401)

    user_id = int(payload["sub"])
    # 校验用户仍有效（未被停用），角色以数据库为准防止权限漂移
    user = db.get(User, user_id)
    if user is None or user.status != "active":
        raise BizException(code=401, message="账号不存在或已停用", http_status=401)
    return {"id": user.id, "name": user.name, "role": user.role, "phone": user.phone}


def require_role(*roles: str) -> Callable:
    """角色鉴权工厂：仅允许指定角色访问，用法 Depends(require_role("admin"))"""
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise BizException(code=403, message="无权访问", http_status=403)
        return current_user
    return checker


def get_current_user_optional(
    authorization: str = Header(default=""),
    db=Depends(get_db),
) -> dict | None:
    """可选登录：无 token 或 token 无效时返回 None（游客），不抛异常"""
    if not authorization.startswith("Bearer "):
        return None
    try:
        payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, ValueError):
        return None
    if user is None or user.status != "active":
        return None
    return {"id": user.id, "name": user.name, "role": user.role, "phone": user.phone}
