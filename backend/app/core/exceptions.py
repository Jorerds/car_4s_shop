"""业务异常定义与全局异常处理器：统一响应体格式 {code, message, data}"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class BizException(Exception):
    """业务异常：携带业务错误码与可读信息，由全局处理器转为统一响应"""

    def __init__(self, code: int, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status


def ok(data=None, message: str = "成功") -> dict:
    """统一成功响应体"""
    return {"code": 200, "message": message, "data": data}


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，保证任何异常都返回统一格式响应"""

    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException):
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # 参数校验失败时取第一条错误信息；去掉 FastAPI 注入的 "body." 前缀，直接给出字段级提示
        first_error = exc.errors()[0]
        field_path = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
        message = f"{field_path}: {first_error['msg']}" if field_path else first_error["msg"]
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": message, "data": None},
        )
