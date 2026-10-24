"""题目相关响应模型。非公开用例不出现在任何响应中。"""

from pydantic import BaseModel, ConfigDict


class PublicCase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    input_data: str
    expected_output: str


class ProblemListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    difficulty: str
    knowledge_points: list[str]


class ProblemDetail(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str
    knowledge_points: list[str]
    input_description: str
    output_description: str
    sample_input: str
    sample_output: str
    public_cases: list[PublicCase]


class HealthOut(BaseModel):
    status: str
    version: str
    # api 表示 API 进程存活；database/database_status 表示 MySQL 依赖状态。
    api: str = "ok"
    database: bool
    database_status: str
    database_latency_ms: int = 0
    docker: bool
