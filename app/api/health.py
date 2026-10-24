"""健康检查：区分 API 进程存活、MySQL 依赖存活与评测环境状态。"""

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.problem import HealthOut
from app.services import judge_service

router = APIRouter(tags=["health"])

VERSION = "0.2.0"


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    started = time.perf_counter()
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    latency_ms = int((time.perf_counter() - started) * 1000)

    return HealthOut(
        status="ok" if database_status == "ok" else "degraded",
        version=VERSION,
        api="ok",
        database=database_status == "ok",
        database_status=database_status,
        database_latency_ms=latency_ms,
        docker=judge_service.docker_status(),
    )
