"""健康检查接口冒烟测试"""

from app.core.config import settings


class TestHealthEndpoint_访问健康接口_返回服务正常:
    """验证应用可启动且 /health 返回统一响应格式"""

    def test_返回200与状态ok(self, client):
        resp = client.get("/api/v1/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["data"]["status"] == "ok"
        assert body["data"]["app"] == settings.APP_NAME
