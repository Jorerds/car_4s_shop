"""车型模块接口测试：C 端展示（列表筛选/详情）与管理端维护（CRUD/配置/图片）"""

from app.core.security import create_access_token, hash_password
from app.models.car_model import CarModel, CarModelConfig, CarModelImage
from app.models.user import User


def _create_model(db_session, name="星辉 L7", brand="星辉汽车", energy="纯电",
                  body="轿车", price=189900, status="on_sale"):
    """测试夹具：写入一款车型，返回 ORM 对象"""
    model = CarModel(
        name=name, brand=brand, series="L系", guide_price=price,
        body_type=body, energy_type=energy, status=status,
    )
    db_session.add(model)
    db_session.flush()
    return model


def _add_config(db_session, model, group, name, value):
    """给车型加一条配置参数（autoflush 关闭，需显式 flush 才能被后续查询看到）"""
    db_session.add(CarModelConfig(
        model_id=model.id, group_name=group, param_name=name, param_value=value
    ))
    db_session.flush()


def _add_image(db_session, model, url, is_main=False, sort=0):
    """给车型加一张图片（同上，显式 flush）"""
    db_session.add(CarModelImage(model_id=model.id, url=url, is_main=is_main, sort=sort))
    db_session.flush()


def _admin_headers(db_session, username="admin01"):
    """创建管理员并返回带 JWT 的请求头"""
    user = User(role="admin", username=username,
                password_hash=hash_password("pass1234"), name="管理员", status="active")
    db_session.add(user)
    db_session.flush()
    return {"Authorization": f"Bearer {create_access_token(user.id, 'admin')}"}


class TestModelList_无筛选_仅返回在售车型:
    def test_停售车型不出现在列表(self, client, db_session):
        _create_model(db_session, name="在售车型")
        _create_model(db_session, name="停售车型", status="off_sale")

        resp = client.get("/api/v1/models")

        assert resp.status_code == 200
        names = [item["name"] for item in resp.json()["data"]["items"]]
        assert names == ["在售车型"]
        assert resp.json()["data"]["total"] == 1


class TestModelList_组合筛选_返回匹配结果:
    def test_按能源类型与价格区间筛选(self, client, db_session):
        _create_model(db_session, name="纯电A", energy="纯电", price=150000)
        _create_model(db_session, name="纯电B", energy="纯电", price=250000)
        _create_model(db_session, name="燃油C", energy="燃油", price=150000)

        resp = client.get("/api/v1/models",
                          params={"energy_type": "纯电", "min_price": 100000, "max_price": 200000})

        names = [item["name"] for item in resp.json()["data"]["items"]]
        assert names == ["纯电A"]


class TestModelList_价格排序_按指定顺序返回:
    def test_价格从低到高(self, client, db_session):
        _create_model(db_session, name="贵车", price=300000)
        _create_model(db_session, name="便宜车", price=100000)

        resp = client.get("/api/v1/models", params={"sort": "price_asc"})

        names = [item["name"] for item in resp.json()["data"]["items"]]
        assert names == ["便宜车", "贵车"]


class TestModelDetail_存在车型_返回图片与分组配置:
    def test_详情包含图片集与六组配置(self, client, db_session):
        model = _create_model(db_session)
        _add_image(db_session, model, "/uploads/a.png", is_main=True)
        _add_config(db_session, model, "动力", "最大功率", "272Ps")
        _add_config(db_session, model, "安全", "辅助驾驶", "L2+")

        resp = client.get(f"/api/v1/models/{model.id}")

        data = resp.json()["data"]
        assert data["images"] == ["/uploads/a.png"]
        assert data["configs"]["动力"] == [{"param_name": "最大功率", "param_value": "272Ps"}]
        assert data["configs"]["安全"][0]["param_value"] == "L2+"


class TestModelDetail_停售车型_返回404:
    def test_停售详情不可见(self, client, db_session):
        model = _create_model(db_session, status="off_sale")

        resp = client.get(f"/api/v1/models/{model.id}")

        assert resp.status_code == 404


class TestAdminCreateModel_合法参数且管理员_创建成功:
    def test_创建后默认在售(self, client, db_session):
        headers = _admin_headers(db_session)

        resp = client.post("/api/v1/admin/models", headers=headers, json={
            "name": "新车型", "brand": "星辉汽车", "series": "L系",
            "guide_price": 199900, "body_type": "轿车", "energy_type": "纯电",
        })

        assert resp.status_code == 200
        model_id = resp.json()["data"]["id"]
        # 创建后 C 端立即可见
        detail = client.get(f"/api/v1/models/{model_id}").json()["data"]
        assert detail["name"] == "新车型"


class TestAdminCreateModel_非管理员_返回403:
    def test_顾客角色无权访问管理接口(self, client, db_session):
        customer = User(role="customer", phone="13900000001", name="顾客", status="active")
        db_session.add(customer)
        db_session.flush()
        headers = {"Authorization": f"Bearer {create_access_token(customer.id, 'customer')}"}

        resp = client.post("/api/v1/admin/models", headers=headers, json={
            "name": "X", "brand": "B", "series": "S",
            "guide_price": 100000, "body_type": "轿车", "energy_type": "纯电",
        })

        assert resp.status_code == 403

    def test_未登录无权访问管理接口(self, client):
        resp = client.post("/api/v1/admin/models", json={
            "name": "X", "brand": "B", "series": "S",
            "guide_price": 100000, "body_type": "轿车", "energy_type": "纯电",
        })

        assert resp.status_code == 401


class TestAdminReplaceConfigs_整体替换_配置更新生效:
    def test_替换后旧配置被清除(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)
        _add_config(db_session, model, "动力", "旧参数", "旧值")

        resp = client.put(f"/api/v1/admin/models/{model.id}/configs", headers=headers, json={
            "configs": [
                {"group_name": "舒适", "param_name": "座椅加热", "param_value": "前排标配"},
            ]
        })

        assert resp.status_code == 200
        detail = client.get(f"/api/v1/models/{model.id}").json()["data"]
        assert "动力" not in detail["configs"]
        assert detail["configs"]["舒适"][0]["param_name"] == "座椅加热"


class TestAdminReplaceConfigs_非法分组名_返回422:
    def test_分组名不在六组之内被拒绝(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)

        resp = client.put(f"/api/v1/admin/models/{model.id}/configs", headers=headers, json={
            "configs": [{"group_name": "外观", "param_name": "颜色", "param_value": "白"}]
        })

        assert resp.status_code == 422


class TestAdminUpdateStatus_停售_C端列表不再返回:
    def test_更新状态为停售(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)

        resp = client.put(f"/api/v1/admin/models/{model.id}", headers=headers, json={
            "name": model.name, "brand": model.brand, "series": model.series,
            "guide_price": model.guide_price, "body_type": model.body_type,
            "energy_type": model.energy_type, "status": "off_sale",
        })

        assert resp.status_code == 200
        assert client.get("/api/v1/models").json()["data"]["total"] == 0


class TestAdminSetMainImage_设为主图_列表主图更新:
    def test_设置后列表返回新主图(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)
        client.post(f"/api/v1/admin/models/{model.id}/images", headers=headers,
                    json={"url": "/uploads/old.png", "is_main": True})
        resp = client.post(f"/api/v1/admin/models/{model.id}/images", headers=headers,
                           json={"url": "/uploads/new.png"})
        new_image_id = resp.json()["data"]["id"]

        client.put(f"/api/v1/admin/models/{model.id}/images/{new_image_id}/main", headers=headers)

        list_resp = client.get("/api/v1/models").json()["data"]
        assert list_resp["items"][0]["main_image"] == "/uploads/new.png"

    def test_其他车型的图片返回404(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)
        other = _create_model(db_session, name="另一款")

        resp = client.put(f"/api/v1/admin/models/{model.id}/images/9999/main", headers=headers)
        assert resp.status_code == 404
        # 归属校验：用另一车型的图片 ID 设主图也应失败
        img_resp = client.post(f"/api/v1/admin/models/{other.id}/images", headers=headers,
                               json={"url": "/uploads/x.png"})
        resp = client.put(f"/api/v1/admin/models/{model.id}/images/{img_resp.json()['data']['id']}/main",
                          headers=headers)
        assert resp.status_code == 404


class TestAdminDetail_停售车型_管理端仍可查看:
    def test_停售车详情含状态与配置(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session, status="off_sale")
        _add_config(db_session, model, "动力", "最大功率", "272Ps")

        resp = client.get(f"/api/v1/admin/models/{model.id}", headers=headers)

        data = resp.json()["data"]
        assert data["status"] == "off_sale"
        assert data["configs"]["动力"][0]["param_value"] == "272Ps"


class TestAdminAddImage_设为主图_原主图被取消:
    def test_同一车型仅一张主图(self, client, db_session):
        headers = _admin_headers(db_session)
        model = _create_model(db_session)
        client.post(f"/api/v1/admin/models/{model.id}/images", headers=headers,
                    json={"url": "/uploads/old.png", "is_main": True})

        client.post(f"/api/v1/admin/models/{model.id}/images", headers=headers,
                    json={"url": "/uploads/new.png", "is_main": True})

        detail = client.get(f"/api/v1/models/{model.id}").json()["data"]
        # 列表主图取最新设为主图的一张
        list_resp = client.get("/api/v1/models").json()["data"]
        assert list_resp["items"][0]["main_image"] == "/uploads/new.png"
        assert len(detail["images"]) == 2
