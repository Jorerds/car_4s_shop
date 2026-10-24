"""试驾资源业务：试驾车维护与时段批量生成"""

import re

from app.core.exceptions import BizException
from app.models.testdrive import TestDriveSlot, TestDriveVehicle
from app.repositories.testdrive import TestDriveRepository
from app.schemas.testdrive import SlotBatchGenerateRequest, VehicleCreateRequest

TIME_SLOT_RE = re.compile(r"^([01]\d|2[0-3]):00$")


class TestDriveService:
    """试驾车与时段业务用例（管理端）"""

    def __init__(self, repo: TestDriveRepository):
        self.repo = repo

    # ---- 试驾车 ----

    def list_vehicles(self) -> list[dict]:
        vehicles = self.repo.list_vehicles()
        # 车型名一次性查出，避免逐条查询
        model_names = self._model_names([v.model_id for v in vehicles])
        return [
            {
                "id": v.id, "plate_no": v.plate_no, "model_id": v.model_id,
                "model_name": model_names.get(v.model_id, ""), "status": v.status,
            }
            for v in vehicles
        ]

    def create_vehicle(self, body: VehicleCreateRequest) -> dict:
        if self.repo.get_vehicle_by_plate(body.plate_no):
            raise BizException(code=400, message="车牌号已存在")
        vehicle = self.repo.add_vehicle(TestDriveVehicle(
            plate_no=body.plate_no, model_id=body.model_id, status="available"
        ))
        return {"id": vehicle.id}

    def update_vehicle_status(self, vehicle_id: int, status: str) -> None:
        vehicle = self.repo.get_vehicle(vehicle_id)
        if vehicle is None:
            raise BizException(code=404, message="试驾车不存在", http_status=404)
        vehicle.status = status
        self.repo.db.flush()

    # ---- 时段 ----

    def batch_generate_slots(self, body: SlotBatchGenerateRequest) -> dict:
        """批量生成时段：已存在的（车型+日期+时段）跳过，不重置已约数"""
        for time_slot in body.time_slots:
            if not TIME_SLOT_RE.match(time_slot):
                raise BizException(code=400, message=f"时段格式不正确：{time_slot}（应为整点 HH:00）")
        created = 0
        for slot_date in body.dates:
            for time_slot in body.time_slots:
                if self.repo.get_slot_by_key(body.model_id, slot_date, time_slot):
                    continue
                self.repo.add_slot(TestDriveSlot(
                    model_id=body.model_id, slot_date=slot_date,
                    time_slot=time_slot, capacity=body.capacity, booked_count=0,
                ))
                created += 1
        return {"created": created}

    def list_day_slots(self, model_id: int, slot_date) -> list[dict]:
        """某日时段列表（管理端）：含余量信息"""
        slots = self.repo.list_slots(model_id, slot_date)
        return [
            {
                "id": s.id, "time_slot": s.time_slot, "capacity": s.capacity,
                "booked_count": s.booked_count,
                "remaining": s.capacity - s.booked_count,
            }
            for s in slots
        ]

    def list_available_slots(self, model_id: int, slot_date) -> list[dict]:
        """可约时段（C 端）：仅返回有余量的时段"""
        slots = self.repo.list_available_slots(model_id, slot_date)
        return [
            {"id": s.id, "time_slot": s.time_slot, "remaining": s.capacity - s.booked_count}
            for s in slots
        ]

    def _model_names(self, model_ids: list[int]) -> dict[int, str]:
        """批量取车型名（去重）"""
        from sqlalchemy import select
        from app.models.car_model import CarModel
        ids = set(model_ids)
        if not ids:
            return {}
        rows = self.repo.db.execute(select(CarModel.id, CarModel.name).where(CarModel.id.in_(ids)))
        return {row[0]: row[1] for row in rows.all()}
