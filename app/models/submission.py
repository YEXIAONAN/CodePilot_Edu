"""提交记录与评测详情模型。"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow

_TABLE_OPTS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}


def new_submission_id() -> str:
    return f"sub-{uuid.uuid4().hex[:12]}"


class Submission(Base):
    __tablename__ = "submissions"
    # 学生历史与教师待辅导查询都按 (student_id, problem_id, submitted_at) 过滤/排序。
    __table_args__ = (
        Index("ix_submissions_student_problem_time", "student_id", "problem_id", "submitted_at"),
        _TABLE_OPTS,
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_submission_id)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False)
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problems.id"), nullable=False, index=True
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="c")

    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_category: Mapped[str] = mapped_column(String(40), nullable=False, default="UNKNOWN_ERROR")
    passed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    diagnosis_knowledge_point: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    diagnosis_evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    diagnosis_source: Mapped[str] = mapped_column(String(8), nullable=False, default="RULE")
    diagnosis_confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="UNDETERMINED")
    # 结构化诊断（category / knowledge_point / evidence / possible_cause / source / certainty）
    diagnosis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")

    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    details: Mapped[list["EvaluationDetail"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class EvaluationDetail(Base):
    __tablename__ = "evaluation_details"
    __table_args__ = (_TABLE_OPTS,)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 仅公开用例保存输出摘要，非公开用例一律留空，避免泄露评测数据
    actual_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_output: Mapped[str] = mapped_column(Text, nullable=False, default="")

    submission: Mapped[Submission] = relationship(back_populates="details")
