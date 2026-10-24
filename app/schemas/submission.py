"""提交与评测响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class SubmissionCreate(BaseModel):
    problem_id: int = Field(gt=0)
    student_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    language: Literal["c"]
    source_code: str = Field(min_length=1)

    @field_validator("source_code")
    @classmethod
    def check_source_size(cls, value: str) -> str:
        if len(value.encode("utf-8")) > settings.max_source_bytes:
            raise ValueError(f"source_code 超过 {settings.max_source_bytes} 字节限制")
        return value


class DiagnosisOut(BaseModel):
    category: str
    knowledge_point: str
    evidence: str
    source: str
    confidence: str
    possible_cause: str = ""
    certainty: str = ""


class CaseResultOut(BaseModel):
    case_index: int
    is_public: bool
    status: str
    execution_time_ms: int
    expected_output: str | None = None
    actual_output: str | None = None
    error_message: str | None = None


class SubmissionResultOut(BaseModel):
    submission_id: str
    problem_id: int
    status: str
    passed_cases: int
    total_cases: int
    execution_time_ms: int
    diagnosis: DiagnosisOut | None = None
    message: str = ""
    cases: list[CaseResultOut] = []


class SubmissionListItem(BaseModel):
    submission_id: str
    problem_id: int
    status: str
    error_category: str
    passed_cases: int
    total_cases: int
    execution_time_ms: int
    submitted_at: datetime
