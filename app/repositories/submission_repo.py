"""提交记录的数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EvaluationDetail, Submission


def add(db: Session, submission: Submission) -> Submission:
    db.add(submission)
    db.flush()
    return submission


def add_details(db: Session, details: list[EvaluationDetail]) -> None:
    if details:
        db.add_all(details)


def get(db: Session, submission_id: str) -> Submission | None:
    return db.get(Submission, submission_id)


def list_recent(db: Session, student_id: str, limit: int = 10) -> list[Submission]:
    statement = (
        select(Submission)
        .where(Submission.student_id == student_id)
        .order_by(Submission.submitted_at.desc(), Submission.id.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))
