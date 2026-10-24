"""统计服务：把聚合查询结果组装为接口响应。"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories import statistics_repo, submission_repo
from app.schemas.statistics import (
    HintUsage,
    KnowledgePointError,
    PendingTutoringItem,
    ProblemOverview,
    ProblemProgress,
    StudentProgressOut,
    TeacherOverviewOut,
)
from app.schemas.submission import SubmissionListItem


def _hint_usage(by_level: dict[int, int], fallback: int) -> HintUsage:
    return HintUsage(
        level_1=by_level.get(1, 0),
        level_2=by_level.get(2, 0),
        level_3=by_level.get(3, 0),
        fallback_count=fallback,
    )


def get_student_progress(db: Session, student_id: str, recent_limit: int = 10) -> StudentProgressOut:
    total, accepted = statistics_repo.student_totals(db, student_id)
    per_problem_rows = statistics_repo.student_per_problem(db, student_id)
    error_distribution = statistics_repo.student_error_distribution(db, student_id)
    by_level, fallback = statistics_repo.student_hint_usage(db, student_id)
    recent = submission_repo.list_recent(db, student_id, recent_limit)

    return StudentProgressOut(
        student_id=student_id,
        total_submissions=total,
        accepted_count=accepted,
        error_category_distribution=error_distribution,
        per_problem=[
            ProblemProgress(
                problem_id=row[0], title=row[1], submissions=row[2], accepted=row[3]
            )
            for row in per_problem_rows
        ],
        hint_usage=_hint_usage(by_level, fallback),
        recent_submissions=[
            SubmissionListItem(
                submission_id=item.id,
                problem_id=item.problem_id,
                status=item.status,
                error_category=item.error_category,
                passed_cases=item.passed_cases,
                total_cases=item.total_cases,
                execution_time_ms=item.execution_time_ms,
                submitted_at=item.submitted_at,
            )
            for item in recent
        ],
    )


def get_teacher_overview(db: Session) -> TeacherOverviewOut:
    total, students, accepted = statistics_repo.teacher_totals(db)
    per_problem_rows = statistics_repo.teacher_per_problem(db)
    error_distribution = statistics_repo.teacher_error_distribution(db)
    knowledge_rows = statistics_repo.teacher_knowledge_point_errors(db)
    completed = statistics_repo.completed_problem_count(db)
    by_level, fallback = statistics_repo.teacher_hint_usage(db)
    system_error_count = statistics_repo.teacher_system_error_count(db)
    pending_rows = statistics_repo.teacher_pending_tutoring(db)

    return TeacherOverviewOut(
        total_submissions=total,
        distinct_students=students,
        accepted_submissions=accepted,
        per_problem=[
            ProblemOverview(
                problem_id=row[0],
                title=row[1],
                submissions=row[2],
                accepted=row[3],
                unique_students=row[4],
            )
            for row in per_problem_rows
        ],
        error_distribution=error_distribution,
        knowledge_point_errors=[
            KnowledgePointError(knowledge_point=row[0], count=row[1])
            for row in knowledge_rows
        ],
        completed_problem_count=completed,
        hint_usage=_hint_usage(by_level, fallback),
        system_error_count=system_error_count,
        pending_tutoring=[
            PendingTutoringItem(
                student_id=row[0],
                problem_id=row[1],
                problem_title=row[2],
                last_submission_id=row[3],
                last_status=row[4],
                submission_count=row[5],
                failure_count=row[6],
                max_hint_level=row[7],
                last_submitted_at=row[8],
            )
            for row in pending_rows
        ],
        generated_at=datetime.now(timezone.utc),
    )
