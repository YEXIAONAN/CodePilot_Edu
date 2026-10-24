"""统计聚合查询。所有数字均来自真实提交与提示记录，禁止硬编码。"""

from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import SubmissionStatus
from app.models import HintRecord, Problem, Submission

_ACCEPTED = SubmissionStatus.ACCEPTED.value
_SYSTEM_ERROR = SubmissionStatus.SYSTEM_ERROR.value


def student_totals(db: Session, student_id: str) -> tuple[int, int]:
    statement = select(
        func.count(Submission.id),
        func.coalesce(
            func.sum(case((Submission.status == _ACCEPTED, 1), else_=0)), 0
        ),
    ).where(Submission.student_id == student_id)
    total, accepted = db.execute(statement).one()
    return int(total or 0), int(accepted or 0)


def student_per_problem(db: Session, student_id: str) -> list[tuple[int, str, int, int]]:
    statement = (
        select(
            Problem.id,
            Problem.title,
            func.count(Submission.id),
            func.coalesce(func.sum(case((Submission.status == _ACCEPTED, 1), else_=0)), 0),
        )
        .join(Submission, Submission.problem_id == Problem.id)
        .where(Submission.student_id == student_id)
        .group_by(Problem.id, Problem.title)
        .order_by(Problem.id)
    )
    return [(int(row[0]), str(row[1]), int(row[2]), int(row[3])) for row in db.execute(statement)]


def student_error_distribution(db: Session, student_id: str) -> dict[str, int]:
    statement = (
        select(Submission.error_category, func.count(Submission.id))
        .where(
            Submission.student_id == student_id,
            Submission.status != _ACCEPTED,
            Submission.status != _SYSTEM_ERROR,
        )
        .group_by(Submission.error_category)
    )
    return {str(row[0]): int(row[1]) for row in db.execute(statement)}


def student_hint_usage(db: Session, student_id: str) -> tuple[dict[int, int], int]:
    statement = (
        select(HintRecord.hint_level, func.count(HintRecord.id))
        .join(Submission, Submission.id == HintRecord.submission_id)
        .where(
            Submission.student_id == student_id,
            HintRecord.is_unlocked.is_(True),
        )
        .group_by(HintRecord.hint_level)
    )
    by_level = {int(row[0]): int(row[1]) for row in db.execute(statement)}
    fallback = db.scalar(
        select(func.count(HintRecord.id))
        .join(Submission, Submission.id == HintRecord.submission_id)
        .where(
            Submission.student_id == student_id,
            HintRecord.is_unlocked.is_(True),
            HintRecord.is_fallback.is_(True),
        )
    )
    return by_level, int(fallback or 0)


def teacher_totals(db: Session) -> tuple[int, int, int]:
    statement = select(
        func.count(Submission.id),
        func.count(distinct(Submission.student_id)),
        func.coalesce(func.sum(case((Submission.status == _ACCEPTED, 1), else_=0)), 0),
    )
    total, students, accepted = db.execute(statement).one()
    return int(total or 0), int(students or 0), int(accepted or 0)


def teacher_per_problem(db: Session) -> list[tuple[int, str, int, int, int]]:
    statement = (
        select(
            Problem.id,
            Problem.title,
            func.count(Submission.id),
            func.coalesce(func.sum(case((Submission.status == _ACCEPTED, 1), else_=0)), 0),
            func.count(distinct(Submission.student_id)),
        )
        .join(Submission, Submission.problem_id == Problem.id)
        .group_by(Problem.id, Problem.title)
        .order_by(Problem.id)
    )
    return [
        (int(row[0]), str(row[1]), int(row[2]), int(row[3]), int(row[4]))
        for row in db.execute(statement)
    ]


def teacher_error_distribution(db: Session) -> dict[str, int]:
    statement = (
        select(Submission.error_category, func.count(Submission.id))
        .where(
            Submission.status != _ACCEPTED,
            Submission.status != _SYSTEM_ERROR,
        )
        .group_by(Submission.error_category)
    )
    return {str(row[0]): int(row[1]) for row in db.execute(statement)}


def teacher_system_error_count(db: Session) -> int:
    statement = select(func.count(Submission.id)).where(
        Submission.status == _SYSTEM_ERROR
    )
    return int(db.scalar(statement) or 0)


def teacher_knowledge_point_errors(db: Session) -> list[tuple[str, int]]:
    statement = (
        select(Submission.diagnosis_knowledge_point, func.count(Submission.id))
        .where(
            Submission.status != _ACCEPTED,
            Submission.status != _SYSTEM_ERROR,
            Submission.diagnosis_knowledge_point != "",
        )
        .group_by(Submission.diagnosis_knowledge_point)
        .order_by(func.count(Submission.id).desc())
    )
    return [(str(row[0]), int(row[1])) for row in db.execute(statement)]


def completed_problem_count(db: Session) -> int:
    statement = (
        select(func.count(distinct(Submission.problem_id)))
        .where(Submission.status == _ACCEPTED)
    )
    return int(db.scalar(statement) or 0)


def teacher_hint_usage(db: Session) -> tuple[dict[int, int], int]:
    statement = (
        select(HintRecord.hint_level, func.count(HintRecord.id))
        .where(HintRecord.is_unlocked.is_(True))
        .group_by(HintRecord.hint_level)
    )
    by_level = {int(row[0]): int(row[1]) for row in db.execute(statement)}
    fallback = db.scalar(
        select(func.count(HintRecord.id)).where(
            HintRecord.is_unlocked.is_(True),
            HintRecord.is_fallback.is_(True),
        )
    )
    return by_level, int(fallback or 0)


def teacher_pending_tutoring(db: Session) -> list[tuple]:
    """按透明规则计算待辅导列表。

    - 同一学生同一题至少 3 次学生代码失败，且最近一次仍未通过；
    - 或该学生在该题已解锁第 3 层提示，且最近一次仍未通过；
    - 最近一次已通过则移出；
    - SYSTEM_ERROR 不计入学生失败，也不作为“最近一次学生提交”。
    """
    student_subs = (
        select(
            Submission.id.label("submission_id"),
            Submission.student_id.label("student_id"),
            Submission.problem_id.label("problem_id"),
            Submission.status.label("status"),
            Submission.submitted_at.label("submitted_at"),
            func.row_number()
            .over(
                partition_by=(Submission.student_id, Submission.problem_id),
                order_by=(Submission.submitted_at.desc(), Submission.id.desc()),
            )
            .label("rn"),
            func.count()
            .over(partition_by=(Submission.student_id, Submission.problem_id))
            .label("submission_count"),
            func.sum(case((Submission.status != _ACCEPTED, 1), else_=0))
            .over(partition_by=(Submission.student_id, Submission.problem_id))
            .label("failure_count"),
        )
        .where(Submission.status != _SYSTEM_ERROR)
        .subquery()
    )
    latest = select(student_subs).where(student_subs.c.rn == 1).subquery()
    max_hints = (
        select(
            Submission.student_id.label("student_id"),
            Submission.problem_id.label("problem_id"),
            func.max(HintRecord.hint_level).label("max_hint_level"),
        )
        .join(HintRecord, HintRecord.submission_id == Submission.id)
        .where(HintRecord.is_unlocked.is_(True))
        .group_by(Submission.student_id, Submission.problem_id)
        .subquery()
    )
    max_hint_level = func.coalesce(max_hints.c.max_hint_level, 0)

    statement = (
        select(
            latest.c.student_id,
            latest.c.problem_id,
            Problem.title,
            latest.c.submission_id,
            latest.c.status,
            latest.c.submission_count,
            latest.c.failure_count,
            max_hint_level,
            latest.c.submitted_at,
        )
        .join(Problem, Problem.id == latest.c.problem_id)
        .outerjoin(
            max_hints,
            and_(
                max_hints.c.student_id == latest.c.student_id,
                max_hints.c.problem_id == latest.c.problem_id,
            ),
        )
        .where(
            latest.c.status != _ACCEPTED,
            or_(latest.c.failure_count >= 3, max_hint_level >= 3),
        )
        .order_by(latest.c.submitted_at.desc())
    )
    return [
        (
            str(row[0]),
            int(row[1]),
            str(row[2]),
            str(row[3]),
            str(row[4]),
            int(row[5]),
            int(row[6]),
            int(row[7]),
            row[8],
        )
        for row in db.execute(statement)
    ]
