"""客户跟进业务：客户列表、认领/分配、详情聚合、跟进登记自动流转状态"""

from sqlalchemy import select

from app.core.exceptions import BizException
from app.models.car_model import CarModel
from app.models.customer import Customer, FollowUpRecord
from app.models.testdrive import Appointment
from app.models.user import User
from app.repositories.appointment import CustomerRepository
from app.schemas.customer import CustomerDetail, CustomerItem, FollowUpCreateRequest, FollowUpItem

# 客户状态与跟进类型的映射（登记跟进即自动流转状态）
CUSTOMER_STATUS_TEXT = {"new": "新线索", "following": "跟进中", "test_driven": "已试驾", "deal": "已成交"}
FOLLOW_UP_TYPE_TEXT = {"phone": "电话", "visit": "到店", "test_drive": "试驾", "deal": "成交"}
FOLLOW_UP_TO_STATUS = {"test_drive": "test_driven", "deal": "deal"}


class CustomerService:
    """客户跟进业务用例"""

    def __init__(self, repo: CustomerRepository):
        self.repo = repo

    def list_customers(self, scope: str, sales_id: int) -> dict:
        """客户列表：mine 我的客户 / pool 公共池（未分配）"""
        customers = self.repo.list_by_scope(scope, sales_id)
        sales_names = self._sales_names([c.sales_id for c in customers if c.sales_id])
        return {
            "items": [
                CustomerItem(
                    id=c.id, name=c.name, phone=c.phone, status=c.status,
                    status_text=CUSTOMER_STATUS_TEXT.get(c.status, c.status),
                    sales_name=sales_names.get(c.sales_id),
                    created_at=c.created_at.strftime("%Y-%m-%d") if c.created_at else "",
                ).model_dump()
                for c in customers
            ]
        }

    def claim(self, customer_id: int, sales_id: int) -> None:
        """销售认领公共池线索：仅未分配可认领，先到先得"""
        customer = self.repo.get(customer_id)
        if customer is None:
            raise BizException(code=404, message="客户不存在", http_status=404)
        if customer.sales_id is not None:
            raise BizException(code=400, message="该线索已被分配，不能认领")
        customer.sales_id = sales_id
        self.repo.db.flush()

    def assign(self, customer_id: int, sales_id: int) -> None:
        """管理员分配线索给销售"""
        customer = self.repo.get(customer_id)
        sales = self.repo.db.get(User, sales_id)
        if customer is None or sales is None or sales.role != "sales" or sales.status != "active":
            raise BizException(code=404, message="客户或销售不存在", http_status=404)
        customer.sales_id = sales_id
        self.repo.db.flush()

    def detail(self, customer_id: int, sales_id: int, is_admin: bool) -> dict:
        """客户详情：基本信息 + 预约记录 + 跟进时间线；非管理员仅可看自己的客户"""
        customer = self.repo.get(customer_id)
        if customer is None:
            raise BizException(code=404, message="客户不存在", http_status=404)
        if not is_admin and customer.sales_id != sales_id:
            raise BizException(code=404, message="客户不存在", http_status=404)

        appointments = self.repo.db.scalars(
            select(Appointment).where(Appointment.customer_phone == customer.phone)
            .order_by(Appointment.id.desc())
        ).all()
        model_names = self._model_names([a.model_id for a in appointments])
        slots = {s.id: s for s in (self._slot(a.slot_id) for a in appointments) if s}
        follow_ups = self.repo.list_follow_ups(customer_id)
        sales_names = self._sales_names([f.sales_id for f in follow_ups])

        return CustomerDetail(
            id=customer.id, name=customer.name, phone=customer.phone,
            status=customer.status, status_text=CUSTOMER_STATUS_TEXT.get(customer.status, customer.status),
            sales_name=self._sales_names([customer.sales_id]).get(customer.sales_id),
            appointments=[
                {
                    "id": a.id, "model_name": model_names.get(a.model_id, ""),
                    "slot_date": str(slots[a.slot_id].slot_date) if a.slot_id in slots else "",
                    "time_slot": slots[a.slot_id].time_slot if a.slot_id in slots else "",
                    "status": a.status,
                }
                for a in appointments
            ],
            follow_ups=[
                FollowUpItem(
                    id=f.id, type=f.type, type_text=FOLLOW_UP_TYPE_TEXT.get(f.type, f.type),
                    content=f.content, sales_name=sales_names.get(f.sales_id, ""),
                    next_follow_at=f.next_follow_at.strftime("%Y-%m-%d %H:%M") if f.next_follow_at else None,
                    created_at=f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "",
                ).model_dump()
                for f in follow_ups
            ],
        ).model_dump()

    def add_follow_up(self, customer_id: int, body: FollowUpCreateRequest, sales_id: int) -> dict:
        """添加跟进：仅归属销售可操作；按类型自动流转客户状态"""
        customer = self.repo.get(customer_id)
        if customer is None or customer.sales_id != sales_id:
            raise BizException(code=404, message="客户不存在", http_status=404)

        record = self.repo.add_follow_up(FollowUpRecord(
            customer_id=customer_id, sales_id=sales_id,
            type=body.type, content=body.content, next_follow_at=body.next_follow_at,
        ))
        # 状态自动流转：试驾→已试驾，成交→已成交；其余置为跟进中
        customer.status = FOLLOW_UP_TO_STATUS.get(body.type, "following")
        self.repo.db.flush()
        return {"id": record.id}

    def _slot(self, slot_id: int):
        from app.models.testdrive import TestDriveSlot
        return self.repo.db.get(TestDriveSlot, slot_id)

    def _model_names(self, model_ids: list[int]) -> dict[int, str]:
        ids = set(model_ids)
        if not ids:
            return {}
        rows = self.repo.db.execute(select(CarModel.id, CarModel.name).where(CarModel.id.in_(ids)))
        return {row[0]: row[1] for row in rows.all()}

    def _sales_names(self, sales_ids: list[int | None]) -> dict[int, str]:
        ids = {sid for sid in sales_ids if sid}
        if not ids:
            return {}
        rows = self.repo.db.execute(select(User.id, User.name).where(User.id.in_(ids)))
        return {row[0]: row[1] for row in rows.all()}
