"""文件上传路由：车型图片上传（管理员），保存到本地磁盘并返回访问 URL"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import require_role
from app.core.config import settings
from app.core.exceptions import BizException, ok

router = APIRouter(prefix="/files", tags=["文件"])

# 允许的图片扩展名与大小上限（5MB，Nginx 层另有 10MB 限制）
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE = 5 * 1024 * 1024


@router.post("/upload")
async def upload_image(
    file: UploadFile,
    _: dict = Depends(require_role("admin")),
) -> dict:
    """上传单张图片：校验类型与大小，按 年月/UUID 命名落盘"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BizException(code=400, message="仅支持 jpg/png/webp 格式图片")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise BizException(code=400, message="图片大小不能超过 5MB")

    # 按月分目录，避免单目录文件过多；文件名用 UUID 防碰撞
    from datetime import datetime
    sub_dir = datetime.now().strftime("%Y%m")
    save_dir = Path(settings.UPLOAD_DIR) / sub_dir
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    (save_dir / filename).write_bytes(content)

    # 访问路径与 Nginx /uploads/ 直出规则对应
    return ok({"url": f"/uploads/{sub_dir}/{filename}"})
