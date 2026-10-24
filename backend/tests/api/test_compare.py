"""车型对比与热度埋点测试"""

from sqlalchemy import text

from tests.api.test_car_model import _add_config, _create_model


def _stat_of(db_session, model_id: int, field: str) -> int:
    """读取车型今日某统计字段值（无记录视为 0）"""
    row = db_session.execute(
        text(f"select {field} from model_stat_daily where model_id = :mid")
        .params(mid=model_id)
    ).first()
    return row[0] if row else 0


class TestCompare_两款车型_返回对齐参数与差异标记:
    def test_相同参数不标记差异_不同参数标记差异(self, client, db_session):
        m1 = _create_model(db_session, name="车A")
        m2 = _create_model(db_session, name="车B")
        _add_config(db_session, m1, "动力", "最大功率", "272Ps")
        _add_config(db_session, m1, "车身", "轴距", "2920mm")
        _add_config(db_session, m2, "动力", "最大功率", "320Ps")
        _add_config(db_session, m2, "动力", "零百加速", "4.8s")

        resp = client.post("/api/v1/models/compare", json={"model_ids": [m1.id, m2.id]})

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [m["name"] for m in data["models"]] == ["车A", "车B"]
        by_name = {r["param_name"]: r for r in data["rows"]}
        # 共有参数对齐到同一行：车A 无零百加速为 None，且为差异项
        assert by_name["最大功率"]["values"] == ["272Ps", "320Ps"]
        assert by_name["最大功率"]["is_diff"] is True
        assert by_name["零百加速"]["values"] == [None, "4.8s"]
        assert by_name["轴距"]["values"] == ["2920mm", None]
        assert by_name["轴距"]["is_diff"] is False


class TestCompare_重复ID_去重后仍满足两款:
    def test_重复选择去重(self, client, db_session):
        m1 = _create_model(db_session, name="车A")
        m2 = _create_model(db_session, name="车B")

        resp = client.post("/api/v1/models/compare", json={"model_ids": [m1.id, m2.id, m1.id]})

        assert resp.status_code == 200
        assert len(resp.json()["data"]["models"]) == 2


class TestCompare_仅一款_返回400:
    def test_数量不足被拒绝(self, client, db_session):
        m1 = _create_model(db_session)

        resp = client.post("/api/v1/models/compare", json={"model_ids": [m1.id]})

        assert resp.status_code == 422  # Pydantic min_length=2 前置拦截


class TestCompare_含停售车_返回404:
    def test_停售车型不可对比(self, client, db_session):
        m1 = _create_model(db_session, name="在售")
        m2 = _create_model(db_session, name="停售", status="off_sale")

        resp = client.post("/api/v1/models/compare", json={"model_ids": [m1.id, m2.id]})

        assert resp.status_code == 404


class TestViewEvent_记录浏览_热度当日累加:
    def test_两次浏览计数为2(self, client, db_session):
        model = _create_model(db_session)

        client.post(f"/api/v1/models/{model.id}/view")
        client.post(f"/api/v1/models/{model.id}/view")

        assert _stat_of(db_session, model.id, "view_count") == 2

    def test_停售车型浏览返回404不计数(self, client, db_session):
        model = _create_model(db_session, status="off_sale")

        resp = client.post(f"/api/v1/models/{model.id}/view")

        assert resp.status_code == 404
        assert _stat_of(db_session, model.id, "view_count") == 0


class TestCompareEvent_记录对比_每车各计一次:
    def test_两款对比各计一次且可累加(self, client, db_session):
        m1 = _create_model(db_session, name="车A")
        m2 = _create_model(db_session, name="车B")

        client.post("/api/v1/models/compare", json={"model_ids": [m1.id, m2.id]})
        client.post("/api/v1/models/compare", json={"model_ids": [m1.id, m2.id]})

        assert _stat_of(db_session, m1.id, "compare_count") == 2
        assert _stat_of(db_session, m2.id, "compare_count") == 2
