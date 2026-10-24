"""提交与评测查询接口。"""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.deps import enforce_submit_rate_limit, require_demo_token
from app.core.errors import ApiError
from app.db.session import get_db
from app.schemas.submission import SubmissionCreate, SubmissionResultOut
from app.services import judge_service, submission_service

router = APIRouter(
    prefix="/submissions",
    tags=["submissions"],
    dependencies=[Depends(require_demo_token)],
)


@router.post("", response_model=SubmissionResultOut)
async def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
) -> SubmissionResultOut:
    enforce_submit_rate_limit(payload.student_id)
    try:
        return await submission_service.submit_code(db, payload)
    except submission_service.ProblemNotFoundError as exc:
        raise ApiError("PROBLEM_NOT_FOUND", str(exc), status_code=404) from exc
    except submission_service.NoTestCaseError as exc:
        raise ApiError("PROBLEM_MISCONFIGURED", str(exc), status_code=500) from exc
    except judge_service.JudgeUnavailableError as exc:
        raise ApiError("JUDGE_UNAVAILABLE", str(exc), status_code=503) from exc


@router.get("/{submission_id}", response_model=SubmissionResultOut)
def get_submission(
    submission_id: str = Path(pattern=r"^sub-[0-9a-f]{12}$"),
    db: Session = Depends(get_db),
) -> SubmissionResultOut:
    try:
        return submission_service.get_submission_result(db, submission_id)
    except submission_service.SubmissionNotFoundError as exc:
        raise ApiError("SUBMISSION_NOT_FOUND", "提交记录不存在", status_code=404) from exc
