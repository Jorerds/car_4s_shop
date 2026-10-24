"""ORM 模型聚合：便于外部统一导入"""

from app.core.db import Base
from app.models.audit import AuditLog
from app.models.car_model import CarModel, CarModelConfig, CarModelImage
from app.models.customer import Customer, FollowUpRecord
from app.models.notification import Notification
from app.models.stat import ModelStatDaily
from app.models.testdrive import Appointment, TestDriveRecord, TestDriveSlot, TestDriveVehicle
from app.models.user import User

__all__ = [
    "Base", "User", "Customer", "FollowUpRecord", "CarModel", "CarModelImage", "CarModelConfig",
    "TestDriveVehicle", "TestDriveSlot", "Appointment", "TestDriveRecord",
    "Notification", "ModelStatDaily", "AuditLog",
]
