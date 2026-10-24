"""试驾资源数据访问：试驾车与时段库存"""

from datetime import date

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.testdrive import TestDriveSlot, TestDriveVehicle


class TestDriveRepository:
    """试驾车与时段查询封装"""

    def __init__(self, db: Session):
        self.db = db

    # ---- 试驾车 ----

    def list_vehicles(self) -> list[TestDriveVehicle]:
        return list(self.db.scalars(select(TestDriveVehicle).order_by(TestDriveVehicle.id.desc())).all())

    def get_vehicle_by_plate(self, plate_no: str) -> TestDriveVehicle | None:
        return self.db.scalar(select(TestDriveVehicle).where(TestDriveVehicle.plate_no == plate_no))

    def get_vehicle(self, vehicle_id: int) -> TestDriveVehicle | None:
        return self.db.get(TestDriveVehicle, vehicle_id)

    def add_vehicle(self, vehicle: TestDriveVehicle) -> TestDriveVehicle:
        self.db.add(vehicle)
        self.db.flush()
        return vehicle

    # ---- 时段 ----

    def get_slot(self, slot_id: int) -> TestDriveSlot | None:
        return self.db.get(TestDriveSlot, slot_id)

    def get_slot_by_key(self, model_id: int, slot_date: date, time_slot: str) -> TestDriveSlot | None:
        return self.db.scalar(
            select(TestDriveSlot).where(
                TestDriveSlot.model_id == model_id,
                TestDriveSlot.slot_date == slot_date,
                TestDriveSlot.time_slot == time_slot,
            )
        )

    def add_slot(self, slot: TestDriveSlot) -> TestDriveSlot:
        self.db.add(slot)
        self.db.flush()
        return slot

    def list_slots(self, model_id: int, slot_date: date) -> list[TestDriveSlot]:
        """管理端：某日全部时段（含已约满）"""
        return list(self.db.scalars(
            select(TestDriveSlot)
            .where(TestDriveSlot.model_id == model_id, TestDriveSlot.slot_date == slot_date)
            .order_by(TestDriveSlot.time_slot)
        ).all())

    def list_available_slots(self, model_id: int, slot_date: date) -> list[TestDriveSlot]:
        """C 端：仅返回有余量的时段"""
        return list(self.db.scalars(
            select(TestDriveSlot).where(
                TestDriveSlot.model_id == model_id,
                TestDriveSlot.slot_date == slot_date,
                TestDriveSlot.booked_count < TestDriveSlot.capacity,
            ).order_by(TestDriveSlot.time_slot)
        ).all())

    def occupy_slot(self, slot_id: int) -> bool:
        """原子占用一个名额：条件更新防并发超约，返回是否成功"""
        result = self.db.execute(
            update(TestDriveSlot)
            .where(TestDriveSlot.id == slot_id, TestDriveSlot.booked_count < TestDriveSlot.capacity)
            .values(booked_count=TestDriveSlot.booked_count + 1)
        )
        return result.rowcount == 1

    def release_slot(self, slot_id: int) -> None:
        """释放一个名额（取消/拒绝时调用）"""
        self.db.execute(
            update(TestDriveSlot)
            .where(TestDriveSlot.id == slot_id, TestDriveSlot.booked_count > 0)
            .values(booked_count=TestDriveSlot.booked_count - 1)
        )
