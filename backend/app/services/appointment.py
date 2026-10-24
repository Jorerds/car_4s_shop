"""预约业务：提交（防超约/去重/线索建档）、我的预约、取消（2 小时限制）"""

from datetime import datetime, timedelta

from app.core.exceptions import BizException
from app.models.testdrive import Appointment
from app.repositories.appointment import AppointmentRepository, CustomerRepository
from app.repositories.testdrive import TestDriveRepository
from app.schemas.testdrive import AppointmentCreateRequest
from app.services.sms_code import SmsCodeService

# 试驾开始前 2 小时内不可取消（PRD 3.6）
CANCEL_CUTOFF_HOURS = 2

APPOINTMENT_STATUS_TEXT = {
    "pending": "待确认", "confirmed": "已确认", "rejected": "已拒绝",
    "cancelled": "已取消", "completed": "已完成", "no_show": "已爽约",
}


class AppointmentService:
    """预约业务用例"""

    def __init__(
        self,
        appointment_repo: AppointmentRepository,
        customer_repo: CustomerRepository,
        testdrive_repo: TestDriveRepository,
        sms_code: SmsCodeService,
    ):
        self.appointment_repo = appointment_repo
        self.customer_repo = customer_repo
        self.testdrive_repo = testdrive_repo
        self.sms_code = sms_code

    def create(self, body: AppointmentCreateRequest, current_user: dict | None) -> dict:
        """提交预约：校验时段 → 身份/验证码 → 去重 → 原子占额 → 建档下单"""
        slot = self.testdrive_repo.get_slot(body.slot_id)
        if slot is None or slot.model_id != body.model_id:
            raise BizException(code=400, message="试驾时段无效")
        if self._slot_start(slot) <= datetime.now():
            raise BizException(code=400, message="该时段已过期，请选择其他时段")

        # 登录顾客免验证码（身份已确认）；游客必须校验短信验证码
        is_customer = current_user is not None and current_user.get("role") == "customer"
        name = body.customer_name
        if is_customer:
            name = name or current_user.get("name") or "顾客"
        else:
            if not body.code:
                raise BizException(code=400, message="请先获取短信验证码")
            self.sms_code.verify_code(body.phone, body.code)

        # 去重：同手机号同车型同时间段仅允许一条有效预约
        if self.appointment_repo.find_active_same_day(body.phone, body.model_id, body.slot_id):
            raise BizException(code=400, message="您已预约过该时段，请勿重复提交")

        # 原子占额：条件更新失败即已约满，整体事务回滚不影响其他预约
        if not self.testdrive_repo.occupy_slot(body.slot_id):
            raise BizException(code=400, message="该时段已约满，请选择其他时段")

        # 预约即建档：以手机号合并客户线索
        customer = self.customer_repo.upsert_by_phone(body.phone, name)
        appointment = self.appointment_repo.add(Appointment(
            customer_name=name, customer_phone=body.phone, customer_id=customer.id,
            model_id=body.model_id, slot_id=body.slot_id,
            status="pending", remark=body.remark,
        ))
        return {"id": appointment.id, "status": appointment.status}

    def list_mine(self, phone: str) -> list[dict]:
        """我的预约：含车型名与时段信息，供状态展示与取消判断"""
        appointments = self.appointment_repo.list_by_phone(phone)
        model_names = self._model_names([a.model_id for a in appointments])
        slots = {s.id: s for s in (self.testdrive_repo.get_slot(a.slot_id) for a in appointments) if s}
        return [
            {
                "id": a.id, "model_name": model_names.get(a.model_id, ""),
                "slot_date": str(slots[a.slot_id].slot_date) if a.slot_id in slots else "",
                "time_slot": slots[a.slot_id].time_slot if a.slot_id in slots else "",
                "status": a.status, "status_text": APPOINTMENT_STATUS_TEXT.get(a.status, a.status),
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
            }
            for a in appointments
        ]

    def cancel(self, appointment_id: int, phone: str) -> None:
        """取消预约：仅本人、待确认/已确认、开始前 2 小时外可取消，取消后释放名额"""
        appointment = self.appointment_repo.get(appointment_id)
        if appointment is None or appointment.customer_phone != phone:
            raise BizException(code=404, message="预约不存在", http_status=404)
        if appointment.status not in ("pending", "confirmed"):
            raise BizException(code=400, message="当前状态不可取消")

        slot = self.testdrive_repo.get_slot(appointment.slot_id)
        if slot and self._slot_start(slot) - timedelta(hours=CANCEL_CUTOFF_HOURS) <= datetime.now():
            raise BizException(code=400, message=f"试驾开始前 {CANCEL_CUTOFF_HOURS} 小时内不可取消")

        appointment.status = "cancelled"
        self.testdrive_repo.release_slot(appointment.slot_id)
        self.testdrive_repo.db.flush()

    @staticmethod
    def _slot_start(slot) -> datetime:
        """时段开始时间：日期 + 整点"""
        hour = int(slot.time_slot.split(":")[0])
        return datetime.combine(slot.slot_date, datetime.min.time()) + timedelta(hours=hour)

    def _model_names(self, model_ids: list[int]) -> dict[int, str]:
        from sqlalchemy import select
        from app.models.car_model import CarModel
        ids = set(model_ids)
        if not ids:
            return {}
        rows = self.testdrive_repo.db.execute(select(CarModel.id, CarModel.name).where(CarModel.id.in_(ids)))
        return {row[0]: row[1] for row in rows.all()}
