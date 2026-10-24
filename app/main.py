"""FastAPI 应用入口。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.api import health, hints, problems, statistics, submissions
from app.core.config import settings
from app.core.errors import ApiError
from app.db.session import engine
from app.services import judge_service
import app.models  # noqa: F401  确保模型注册到 Base.metadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 建表由 scripts/init_db.py 负责；启动不执行 DDL，避免数据库不可用时
    # 整个进程起不来，也避免业务账号需要建表权限。
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("database_ready")
    except Exception as exc:  # noqa: BLE001  数据库不可用时仍启动 API，由接口返回依赖故障
        logger.warning("database_unavailable_at_startup type=%s", type(exc).__name__)
    if not settings.demo_token:
        logger.warning("demo_token_missing")
    judge_service.cleanup_stale_containers()
    logger.info("app_started judge_docker_ready=%s", judge_service.docker_status())
    yield


app = FastAPI(
    title="CodePilot Edu Backend",
    description="基于 AI 错因诊断与学习行为分析的 C 语言智能实训平台（P0）",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Demo-Token"],
)


@app.exception_handler(ApiError)
async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数不合法",
                "detail": f"{'.'.join(str(part) for part in first.get('loc', []))}: {first.get('msg', '')}",
            }
        },
    )


async def database_unavailable_handler(_request: Request, exc: Exception) -> JSONResponse:
    # 只暴露依赖故障，不回退 SQLite/内存库，也不把内部连接信息返回给客户端。
    logger.error("database_unavailable type=%s", type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "数据库依赖不可用，请稍后重试",
                "detail": None,
            }
        },
    )


for _db_exc_type in (OperationalError, InterfaceError, SQLAlchemyTimeoutError):
    app.add_exception_handler(_db_exc_type, database_unavailable_handler)


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception type=%s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务内部错误",
                "detail": None,
            }
        },
    )


app.include_router(health.router)
app.include_router(problems.router, prefix=settings.api_prefix)
app.include_router(submissions.router, prefix=settings.api_prefix)
app.include_router(hints.router, prefix=settings.api_prefix)
app.include_router(statistics.router, prefix=settings.api_prefix)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
