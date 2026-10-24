"""车型业务逻辑：C 端展示与管理端维护"""

from sqlalchemy import asc, desc

from app.core.exceptions import BizException
from app.models.car_model import CarModel, CarModelConfig, CarModelImage
from app.repositories.car_model import CarModelRepository
from app.schemas.car_model import (
    ConfigItem,
    ImageAddRequest,
    ModelCreateRequest,
    ModelUpdateRequest,
)
from app.services.stats import StatService

# C 端排序白名单：防止传任意字段排序
SORT_OPTIONS = {
    "newest": desc(CarModel.id),
    "price_asc": asc(CarModel.guide_price),
    "price_desc": desc(CarModel.guide_price),
}


def main_image_of(model: CarModel) -> str | None:
    """取主图 URL：优先 is_main，否则取 sort 最小的一张；无图返回 None"""
    if not model.images:
        return None
    main = next((img for img in model.images if img.is_main), model.images[0])
    return main.url


class CarModelService:
    """车型业务用例"""

    def __init__(self, repo: CarModelRepository):
        self.repo = repo

    # ---- C 端 ----

    def list_public(self, query: dict) -> dict:
        """C 端列表：筛选 + 排序 + 分页"""
        order_by = SORT_OPTIONS.get(query["sort"], SORT_OPTIONS["newest"])
        items, total = self.repo.list_public(
            brand=query.get("brand"),
            energy_type=query.get("energy_type"),
            body_type=query.get("body_type"),
            min_price=query.get("min_price"),
            max_price=query.get("max_price"),
            order_by=order_by,
            page=query["page"],
            page_size=query["page_size"],
        )
        return {
            "items": [
                {
                    "id": m.id, "name": m.name, "brand": m.brand,
                    "energy_type": m.energy_type, "body_type": m.body_type,
                    "guide_price": m.guide_price, "main_image": main_image_of(m),
                }
                for m in items
            ],
            "total": total,
        }

    def get_public_detail(self, model_id: int) -> dict:
        """C 端详情：停售或不存在返回 404（不暴露存在性）"""
        model = self.repo.get_by_id(model_id)
        if model is None or model.status != "on_sale":
            raise BizException(code=404, message="车型不存在或已停售", http_status=404)

        # 配置按六组归类，保持前端展示稳定
        configs: dict[str, list[dict[str, str]]] = {}
        for cfg in model.configs:
            configs.setdefault(cfg.group_name, []).append(
                {"param_name": cfg.param_name, "param_value": cfg.param_value}
            )
        return {
            "id": model.id, "name": model.name, "brand": model.brand,
            "series": model.series, "guide_price": model.guide_price,
            "body_type": model.body_type, "energy_type": model.energy_type,
            "images": [img.url for img in model.images],
            "configs": configs,
        }

    def list_filter_options(self) -> dict:
        """C 端筛选项：品牌去重列表"""
        return {"brands": self.repo.list_brands()}

    # ---- C 端：对比 ----

    def compare(self, model_ids: list[int]) -> dict:
        """2-3 款车型参数对比：按（组, 参数名）对齐，标记差异项，并记录对比事件"""
        # 去重保序：同一车型重复选择只算一款
        ids = list(dict.fromkeys(model_ids))
        if not 2 <= len(ids) <= 3:
            raise BizException(code=400, message="请选择 2-3 款车型进行对比")
        models = [self.repo.get_by_id(i) for i in ids]
        if any(m is None or m.status != "on_sale" for m in models):
            raise BizException(code=404, message="车型不存在或已停售", http_status=404)

        # 对齐：以 (分组, 参数名) 为行，跨车型取值，缺省为 None
        rows: list[dict] = []
        row_index: dict[tuple[str, str], int] = {}
        for idx, model in enumerate(models):
            for cfg in model.configs:
                key = (cfg.group_name, cfg.param_name)
                if key not in row_index:
                    row_index[key] = len(rows)
                    rows.append({
                        "group": cfg.group_name, "param_name": cfg.param_name,
                        "values": [None] * len(models),
                    })
                rows[row_index[key]]["values"][idx] = cfg.param_value
        # 差异项：非空取值去重后超过 1 种即为差异
        for row in rows:
            non_null = [v for v in row["values"] if v is not None]
            row["is_diff"] = len(set(non_null)) > 1

        StatService(self.repo.db).record_compare(ids)
        return {
            "models": [
                {
                    "id": m.id, "name": m.name, "guide_price": m.guide_price,
                    "energy_type": m.energy_type, "body_type": m.body_type,
                    "main_image": main_image_of(m),
                }
                for m in models
            ],
            "rows": rows,
        }

    def record_view(self, model_id: int) -> None:
        """记录车型详情浏览（车型需在售）"""
        model = self.repo.get_by_id(model_id)
        if model is None or model.status != "on_sale":
            raise BizException(code=404, message="车型不存在或已停售", http_status=404)
        StatService(self.repo.db).record_view(model_id)

    # ---- 管理端 ----

    def list_admin(self, keyword: str | None, page: int, page_size: int) -> dict:
        """管理端列表：全量状态"""
        items, total = self.repo.list_admin(keyword=keyword, page=page, page_size=page_size)
        return {
            "items": [
                {
                    "id": m.id, "name": m.name, "brand": m.brand, "series": m.series,
                    "energy_type": m.energy_type, "body_type": m.body_type,
                    "guide_price": m.guide_price, "status": m.status,
                    "main_image": main_image_of(m),
                }
                for m in items
            ],
            "total": total,
        }

    def create(self, body: ModelCreateRequest) -> dict:
        """创建车型，默认在售"""
        model = self.repo.create(CarModel(
            name=body.name, brand=body.brand, series=body.series,
            guide_price=body.guide_price, body_type=body.body_type,
            energy_type=body.energy_type, status="on_sale",
        ))
        return {"id": model.id}

    def update(self, model_id: int, body: ModelUpdateRequest) -> None:
        """更新车型信息与销售状态"""
        model = self._get_or_404(model_id)
        model.name = body.name
        model.brand = body.brand
        model.series = body.series
        model.guide_price = body.guide_price
        model.body_type = body.body_type
        model.energy_type = body.energy_type
        model.status = body.status
        self.repo.db.flush()

    def replace_configs(self, model_id: int, items: list[ConfigItem]) -> None:
        """配置整体替换"""
        self._get_or_404(model_id)
        configs = [
            CarModelConfig(
                model_id=model_id, group_name=i.group_name,
                param_name=i.param_name, param_value=i.param_value,
            )
            for i in items
        ]
        self.repo.replace_configs(model_id, configs)

    def add_image(self, model_id: int, body: ImageAddRequest) -> dict:
        """添加图片；若标记为主图则取消其他主图"""
        self._get_or_404(model_id)
        if body.is_main:
            self.repo.clear_main_images(model_id)
        image = self.repo.add_image(CarModelImage(
            model_id=model_id, url=body.url, is_main=body.is_main, sort=body.sort,
        ))
        return {"id": image.id}

    def delete_image(self, model_id: int, image_id: int) -> None:
        """删除图片，校验归属防止越权操作他人车型"""
        image = self.repo.get_image(image_id)
        if image is None or image.model_id != model_id:
            raise BizException(code=404, message="图片不存在", http_status=404)
        self.repo.db.delete(image)
        self.repo.db.flush()

    def _group_configs(self, model: CarModel) -> dict[str, list[dict[str, str]]]:
        """配置按六组归类，保持前端展示稳定"""
        configs: dict[str, list[dict[str, str]]] = {}
        for cfg in model.configs:
            configs.setdefault(cfg.group_name, []).append(
                {"param_name": cfg.param_name, "param_value": cfg.param_value}
            )
        return configs

    def admin_detail(self, model_id: int) -> dict:
        """管理端详情：含停售车在内的完整信息（图片 + 分组配置 + 状态）"""
        model = self._get_or_404(model_id)
        return {
            "id": model.id, "name": model.name, "brand": model.brand,
            "series": model.series, "guide_price": model.guide_price,
            "body_type": model.body_type, "energy_type": model.energy_type,
            "status": model.status,
            "images": [
                {"id": img.id, "url": img.url, "is_main": img.is_main, "sort": img.sort}
                for img in model.images
            ],
            "configs": self._group_configs(model),
        }

    def set_main_image(self, model_id: int, image_id: int) -> None:
        """设置主图：校验归属后取消其他主图标记"""
        model = self._get_or_404(model_id)
        image = next((img for img in model.images if img.id == image_id), None)
        if image is None:
            raise BizException(code=404, message="图片不存在", http_status=404)
        self.repo.clear_main_images(model_id)
        image.is_main = True
        self.repo.db.flush()

    def _get_or_404(self, model_id: int) -> CarModel:
        """管理端按 ID 取车型，不存在抛 404"""
        model = self.repo.get_by_id(model_id)
        if model is None:
            raise BizException(code=404, message="车型不存在", http_status=404)
        return model
