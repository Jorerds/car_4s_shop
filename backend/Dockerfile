# 后端镜像：精简运行时，依赖锁定自 requirements.txt
FROM python:3.12-slim

WORKDIR /app

# 先拷贝依赖清单，利用构建缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
