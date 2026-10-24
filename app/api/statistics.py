"""学生进度与教师统计接口。"""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.deps import require_demo_token
from app.db.session import get_db
from app.schemas.statistics import StudentProgressOut, TeacherOverviewOut
from app.services import statistics_service

router = APIRouter(tags=["statistics"], dependencies=[Depends(require_demo_token)])


@router.get("/students/{student_id}/progress", response_model=StudentProgressOut)
def student_progress(
    student_id: str = Path(
        min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    ),
    db: Session = Depends(get_db),
) -> StudentProgressOut:
    return statistics_service.get_student_progress(db, student_id)


@router.get("/teacher/overview", response_model=TeacherOverviewOut)
def teacher_overview(db: Session = Depends(get_db)) -> TeacherOverviewOut:
    return statistics_service.get_teacher_overview(db)
