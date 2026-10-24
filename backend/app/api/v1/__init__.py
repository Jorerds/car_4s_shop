"""v1 路由聚合：所有业务模块在此挂载"""

from fastapi import APIRouter

from app.api.v1 import admin, appointments, auth, auth_ext, customers, files, health, models, reports, sales, slots

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(auth_ext.router)
api_router.include_router(models.router)
api_router.include_router(slots.public_router)
api_router.include_router(appointments.router)
api_router.include_router(admin.router)
api_router.include_router(slots.admin_router)
api_router.include_router(sales.router)
api_router.include_router(reports.router)
api_router.include_router(customers.router)
api_router.include_router(files.router)
