"""统一错误响应结构。"""

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
