"""分层提示请求与响应模型。"""

from pydantic import BaseModel, Field


class HintRequest(BaseModel):
    level: int = Field(ge=1, le=3)


class HintOut(BaseModel):
    submission_id: str
    level: int
    source: str
    knowledge_point: str
    hint: str
    is_fallback: bool
