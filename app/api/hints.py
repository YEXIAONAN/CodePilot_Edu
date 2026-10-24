"""分层提示接口。"""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.deps import require_demo_token
from app.core.errors import ApiError
from app.db.session import get_db
from app.schemas.hint import HintOut, HintRequest
from app.services import hint_service

router = APIRouter(
    prefix="/submissions",
    tags=["hints"],
    dependencies=[Depends(require_demo_token)],
)


@router.post("/{submission_id}/hints", response_model=HintOut)
async def request_hint(
    payload: HintRequest,
    submission_id: str = Path(pattern=r"^sub-[0-9a-f]{12}$"),
    db: Session = Depends(get_db),
) -> HintOut:
    try:
        return await hint_service.request_hint(db, submission_id, payload.level)
    except hint_service.HintNotFoundError as exc:
        raise ApiError("SUBMISSION_NOT_FOUND", "提交记录不存在", status_code=404) from exc
    except hint_service.HintNotAvailableError as exc:
        raise ApiError("HINT_NOT_AVAILABLE", str(exc), status_code=400) from exc
    except hint_service.HintLevelError as exc:
        raise ApiError(
            "HINT_LEVEL_INVALID",
            str(exc),
            status_code=400,
            detail=str(exc.next_level) if exc.next_level else None,
        ) from exc
