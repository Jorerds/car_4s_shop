# 4S店线上车辆展示与预约试驾系统

线上车辆展示与预约试驾系统：顾客在线浏览车型、对比配置、预约试驾；销售顾问确认预约、跟进客户；店管理员维护车型与时段、查看统计报表。

- 需求文档：[docs/PRD.md](docs/PRD.md)
- 技术方案：[docs/技术方案.md](docs/技术方案.md)
- 开发进度：[docs/开发进度.md](docs/开发进度.md)
- 测试报告：[docs/测试报告.md](docs/测试报告.md)

## 技术栈

- 后端：FastAPI + SQLAlchemy 2 + MySQL 8 + Redis 7 + Celery 5
- 前端：Vue 3 + Vite 多入口（顾客端 H5：TailwindCSS；管理端：Element Plus + ECharts）
- 部署：Docker Compose（Nginx + 后端 + Celery Worker + MySQL + Redis）

## 目录结构

```
ai_4s/
├── backend/          # FastAPI 后端（api/services/repositories 三层）
├── frontend/         # Vue3 前端（src/h5 顾客端 + src/admin 管理端）
├── deploy/           # Nginx 配置
├── docs/             # PRD、技术方案、开发进度、测试报告
├── .venv/            # Python 虚拟环境（不提交）
└── docker-compose.yml
```

## 本地开发

### 后端

```bash
# 1. 准备虚拟环境（已存在则跳过创建）
python -m venv .venv

# 2. 安装依赖
.venv/Scripts/pip install -r backend/requirements.txt

# 3. 启动 MySQL 与 Redis（Docker，已配置好端口隔离）
docker compose up -d mysql redis

# 4. 配置环境变量
cp .env.example .env

# 5. 数据库迁移（首次，在项目根目录执行）
./.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head

# 6. 启动 API 服务
cd backend && ../.venv/Scripts/uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev          # 顾客端 http://localhost:5273 ，管理端 http://localhost:5273/admin/
```

### 运行测试

```bash
cd backend && ../.venv/Scripts/python -m pytest tests/ -q
```

## 生产部署

```bash
cp .env.example .env   # 修改 JWT_SECRET 与 MySQL 密码
cd frontend && npm install && npm run build   # 构建前端到 frontend/dist
docker compose up -d --build
docker compose exec backend alembic upgrade head   # 首次：执行数据库迁移
```

访问：`http://<服务器IP>/`（顾客端）、`http://<服务器IP>/admin/`（管理端）。
