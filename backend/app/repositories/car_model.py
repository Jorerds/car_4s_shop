"""车型数据访问：查询、创建、更新与配置/图片维护"""

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.car_model import CarModel, CarModelConfig, CarModelImage


class CarModelRepository:
    """车型表查询封装"""

    def __init__(self, db: Session):
        self.db = db

    def _exec(self, stmt: Select):
        """执行查询：populate_existing 强制刷新身份映射中的既有对象及其关系集合。

        本会话若已加载过某车型（如先查后改），普通查询不会刷新其已加载的
        images/configs 集合，会读到过期数据；该选项确保读到最新库内状态
        """
        return self.db.execute(stmt.execution_options(populate_existing=True))

    def _base_stmt(self) -> Select:
        """公共查询：预加载图片与配置，避免 N+1"""
        return select(CarModel).options(
            selectinload(CarModel.images), selectinload(CarModel.configs)
        )

    def get_by_id(self, model_id: int) -> CarModel | None:
        """按 ID 查询车型（含图片配置）"""
        return self._exec(
            self._base_stmt().where(CarModel.id == model_id)
        ).scalar_one_or_none()

    def list_public(
        self,
        *,
        brand: str | None,
        energy_type: str | None,
        body_type: str | None,
        min_price: int | None,
        max_price: int | None,
        order_by,
        page: int,
        page_size: int,
    ) -> tuple[list[CarModel], int]:
        """C 端列表：仅在售车型，组合筛选 + 分页，返回 (列表, 总数)"""
        stmt = self._base_stmt().where(CarModel.status == "on_sale")
        count_stmt = select(func.count()).select_from(CarModel).where(CarModel.status == "on_sale")

        # 筛选条件同时应用到列表与计数查询
        filters = []
        if brand:
            filters.append(CarModel.brand == brand)
        if energy_type:
            filters.append(CarModel.energy_type == energy_type)
        if body_type:
            filters.append(CarModel.body_type == body_type)
        if min_price is not None:
            filters.append(CarModel.guide_price >= min_price)
        if max_price is not None:
            filters.append(CarModel.guide_price <= max_price)

        for f in filters:
            stmt = stmt.where(f)
            count_stmt = count_stmt.where(f)

        total = self.db.execute(count_stmt).scalar_one()
        items = self._exec(
            stmt.order_by(order_by).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(items), total

    def list_admin(
        self, *, keyword: str | None, page: int, page_size: int
    ) -> tuple[list[CarModel], int]:
        """管理端列表：全量状态，支持名称/品牌/车系关键字搜索"""
        stmt = self._base_stmt()
        count_stmt = select(func.count()).select_from(CarModel)
        if keyword:
            like = f"%{keyword}%"
            cond = (CarModel.name.like(like) | CarModel.brand.like(like)
                    | CarModel.series.like(like))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = self.db.execute(count_stmt).scalar_one()
        items = self._exec(
            stmt.order_by(CarModel.id.desc()).offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return list(items), total

    def create(self, model: CarModel) -> CarModel:
        """新增车型"""
        self.db.add(model)
        self.db.flush()
        return model

    def list_brands(self) -> list[str]:
        """C 端筛选项：在售车型的品牌去重列表"""
        stmt = (
            select(CarModel.brand).where(CarModel.status == "on_sale")
            .distinct().order_by(CarModel.brand)
        )
        return list(self.db.execute(stmt).scalars().all())

    # ---- 图片维护 ----

    def add_image(self, image: CarModelImage) -> CarModelImage:
        self.db.add(image)
        self.db.flush()
        return image

    def get_image(self, image_id: int) -> CarModelImage | None:
        return self.db.get(CarModelImage, image_id)

    def clear_main_images(self, model_id: int) -> None:
        """取消该车型所有图片的主图标记（用于切换主图）

        必须走 ORM 对象删除/更新而非 query().update()：后者绕过会话状态，
        同会话后续查询会因身份映射缓存读到过期值（SQLite 主键复用加剧该问题）
        """
        for image in self.db.scalars(
            select(CarModelImage).where(
                CarModelImage.model_id == model_id, CarModelImage.is_main.is_(True)
            )
        ):
            image.is_main = False
        # 先落库修改再过期：过期会丢弃未 flush 的内存改动，顺序不能反
        self.db.flush()
        self.db.expire_all()

    # ---- 配置维护 ----

    def replace_configs(self, model_id: int, configs: list[CarModelConfig]) -> None:
        """配置整体替换：先删后插，由调用方事务保证原子性

        删除必须经 ORM 对象标记，保证会话身份映射与数据库一致
        """
        for existing in self.db.scalars(
            select(CarModelConfig).where(CarModelConfig.model_id == model_id)
        ):
            self.db.delete(existing)
        self.db.flush()  # 先落库删除，避免新旧记录主键冲突
        self.db.add_all(configs)
        self.db.flush()
        # 删除-重插会让身份映射残留旧对象，统一过期保证同会话后续读取一致
        self.db.expire_all()
