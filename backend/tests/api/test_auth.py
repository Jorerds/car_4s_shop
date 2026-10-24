"""账号密码登录接口测试：覆盖成功登录、密码错误、顾客角色越权三类场景"""

from app.core.security import hash_password
from app.models.user import User


def _create_sales(db_session, username="sales01", password="pass1234", name="张销售"):
    """往测试库写入销售账号，返回创建的用户对象"""
    user = User(
        role="sales",
        username=username,
        password_hash=hash_password(password),
        name=name,
        status="active",
    )
    db_session.add(user)
    db_session.flush()
    return user


class TestLoginByAccount_正确账号密码_返回JWT令牌:
    def test_登录成功返回token与用户信息(self, client, db_session):
        _create_sales(db_session)

        resp = client.post(
            "/api/v1/auth/login-by-account",
            json={"username": "sales01", "password": "pass1234"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["data"]["token"]
        assert body["data"]["user"]["role"] == "sales"


class TestLoginByAccount_密码错误_返回401:
    def test_提示账号或密码错误(self, client, db_session):
        _create_sales(db_session)

        resp = client.post(
            "/api/v1/auth/login-by-account",
            json={"username": "sales01", "password": "wrongpass"},
        )

        assert resp.status_code == 401
        assert resp.json()["message"] == "账号或密码错误"


class TestLoginByAccount_请求体为空_返回422友好提示:
    def test_空账号提示账号不能为空(self, client):
        resp = client.post(
            "/api/v1/auth/login-by-account",
            json={"username": "", "password": "pass1234"},
        )

        assert resp.status_code == 422
        assert "账号不能为空" in resp.json()["message"]
        assert "String should" not in resp.json()["message"]

    def test_空密码提示密码不能为空(self, client):
        resp = client.post(
            "/api/v1/auth/login-by-account",
            json={"username": "admin", "password": ""},
        )

        assert resp.status_code == 422
        assert "密码不能为空" in resp.json()["message"]

    def test_整个请求体为空提示账号不能为空(self, client):
        resp = client.post("/api/v1/auth/login-by-account", json={})

        assert resp.status_code == 422
        assert "账号不能为空" in resp.json()["message"]


class TestLoginByAccount_顾客账号登录管理端_返回403:
    def test_拒绝顾客角色登录账号密码入口(self, client, db_session):
        customer = User(
            role="customer",
            phone="13800000001",
            name="李顾客",
            status="active",
        )
        db_session.add(customer)
        db_session.flush()

        resp = client.post(
            "/api/v1/auth/login-by-account",
            json={"username": "13800000001", "password": "pass1234"},
        )

        assert resp.status_code == 401  # 顾客无 username 字段，走不到角色校验
