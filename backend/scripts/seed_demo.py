"""演示数据种子：创建 3 款车型及配置、SVG 占位车图

用法（在项目根目录执行）：
    PYTHONPATH=backend .venv/Scripts/python backend/scripts/seed_demo.py

幂等：已存在的车型（按名称）跳过，可重复执行。
"""

from pathlib import Path
from datetime import date, timedelta

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.car_model import CarModel, CarModelConfig, CarModelImage
from app.models.testdrive import TestDriveSlot, TestDriveVehicle
from app.models.user import User
from sqlalchemy import select

# 演示车型数据：配置参数按六组组织
DEMO_MODELS = [
    {
        "name": "星辉 L7", "brand": "星辉汽车", "series": "星辉 L 系",
        "guide_price": 189900, "body_type": "轿车", "energy_type": "纯电",
        "configs": [
            ("动力", "最大功率", "272Ps"), ("动力", "CLTC 续航", "620km"),
            ("动力", "零百加速", "5.9s"),
            ("底盘", "前悬架", "双叉臂式"), ("底盘", "后悬架", "五连杆式"),
            ("车身", "长×宽×高", "4920×1920×1500mm"), ("车身", "轴距", "2920mm"),
            ("安全", "辅助驾驶", "L2+ 级"), ("安全", "气囊", "全车 8 气囊"),
            ("舒适", "座椅加热", "前排标配"), ("舒适", "音响", "12 扬声器"),
            ("科技", "座舱芯片", "高通 8155"), ("科技", "中控屏幕", "15.6 英寸"),
        ],
    },
    {
        "name": "曜岩 S5", "brand": "曜岩", "series": "曜岩 S 系",
        "guide_price": 245000, "body_type": "SUV", "energy_type": "混动",
        "configs": [
            ("动力", "最大功率", "320Ps"), ("动力", "综合续航", "1100km"),
            ("底盘", "驱动形式", "双电机四驱"), ("底盘", "前悬架", "麦弗逊式"),
            ("车身", "长×宽×高", "4750×1905×1680mm"), ("车身", "轴距", "2800mm"),
            ("安全", "辅助驾驶", "L2 级"), ("安全", "气囊", "全车 6 气囊"),
            ("舒适", "座椅加热", "前后排标配"), ("舒适", "天窗", "全景可开启"),
            ("科技", "座舱芯片", "高通 8295"), ("科技", "中控屏幕", "14.6 英寸"),
        ],
    },
    {
        "name": "长风 M3", "brand": "长风", "series": "长风 M 系",
        "guide_price": 219800, "body_type": "MPV", "energy_type": "燃油",
        "configs": [
            ("动力", "最大功率", "237Ps"), ("动力", "变速箱", "8AT 手自一体"),
            ("底盘", "前悬架", "麦弗逊式"), ("底盘", "后悬架", "扭力梁式"),
            ("车身", "长×宽×高", "5140×1920×1920mm"), ("车身", "轴距", "3000mm"),
            ("安全", "辅助驾驶", "定速巡航"), ("安全", "气囊", "全车 6 气囊"),
            ("舒适", "座椅布局", "2+2+3 七座"), ("舒适", "后排配置", "独立空调"),
            ("科技", "中控屏幕", "10.25 英寸"), ("科技", "液晶仪表", "7 英寸"),
        ],
    },
]


def _write_placeholder_svg(model_name: str, filename: str) -> str:
    """生成灰色 SVG 占位车图到上传目录，返回访问 URL（幂等）"""
    upload_dir = Path(settings.UPLOAD_DIR) / "demo"
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / filename
    if not path.exists():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450">'
            '<rect width="100%" height="100%" fill="#F5F7F9"/>'
            '<text x="50%" y="50%" font-size="40" fill="#98A1AC" '
            'text-anchor="middle" dominant-baseline="middle" '
            f'font-family="sans-serif">{model_name}</text></svg>'
        )
        path.write_text(svg, encoding="utf-8")
    return f"/uploads/demo/{filename}"


def seed_models(db) -> int:
    """按名称幂等创建演示车型，返回新增数量"""
    created = 0
    for demo in DEMO_MODELS:
        exists = db.execute(
            select(CarModel).where(CarModel.name == demo["name"])
        ).scalar_one_or_none()
        if exists:
            continue

        model = CarModel(
            name=demo["name"], brand=demo["brand"], series=demo["series"],
            guide_price=demo["guide_price"], body_type=demo["body_type"],
            energy_type=demo["energy_type"], status="on_sale",
        )
        db.add(model)
        db.flush()

        # 每款车型 3 张占位图，首张为主图
        for i in range(1, 4):
            url = _write_placeholder_svg(demo["name"], f"demo-{model.name.split()[-1]}-{i}.svg")
            db.add(CarModelImage(model_id=model.id, url=url, is_main=(i == 1), sort=i))

        for group, param, value in demo["configs"]:
            db.add(CarModelConfig(
                model_id=model.id, group_name=group, param_name=param, param_value=value
            ))
        created += 1
    return created


def seed_testdrive_resources(db) -> None:
    """演示试驾车与时段：每车型 2 台车，未来 7 天 10:00-16:00 整点时段，容量 2（幂等）"""
    models = list(db.scalars(select(CarModel)).all())
    for model in models:
        # 试驾车（按车牌幂等）
        for i in range(1, 3):
            plate = f"沪A·D{model.id:03d}{i}"
            exists = db.execute(
                select(TestDriveVehicle).where(TestDriveVehicle.plate_no == plate)
            ).scalar_one_or_none()
            if not exists:
                db.add(TestDriveVehicle(plate_no=plate, model_id=model.id, status="available"))
        # 未来 7 天时段（整点 10-16，容量 2；已存在跳过）
        for offset in range(1, 8):
            slot_date = date.today() + timedelta(days=offset)
            for hour in range(10, 17):
                time_slot = f"{hour:02d}:00"
                exists = db.execute(
                    select(TestDriveSlot).where(
                        TestDriveSlot.model_id == model.id,
                        TestDriveSlot.slot_date == slot_date,
                        TestDriveSlot.time_slot == time_slot,
                    )
                ).scalar_one_or_none()
                if not exists:
                    db.add(TestDriveSlot(
                        model_id=model.id, slot_date=slot_date,
                        time_slot=time_slot, capacity=2, booked_count=0,
                    ))


def seed_admin(db) -> None:
    """确保管理员账号存在（与初始账号一致，幂等）"""
    exists = db.execute(select(User).where(User.username == "admin")).scalar_one_or_none()
    if not exists:
        db.add(User(role="admin", username="admin",
                    password_hash=hash_password("Admin@123456"), name="店管理员"))


def main() -> None:
    """种子入口：开事务，全部成功才提交"""
    db = SessionLocal()
    try:
        seed_admin(db)
        created = seed_models(db)
        seed_testdrive_resources(db)
        db.commit()
        print(f"种子完成：新增车型 {created} 款，试驾车/时段已就绪，管理员账号就绪")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
