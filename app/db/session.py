"""MySQL 连接与会话管理。

- 驱动固定为 PyMySQL，连接串由 DATABASE_URL 提供（mysql+pymysql://）。
- 连接池启用 pre-ping 与 recycle，检测/替换失效连接。
- 字符集在连接串与连接参数中均固定 utf8mb4。
- 不提供任何 SQLite / 内存库回退；数据库不可用时由接口层返回 5xx。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    pool_recycle=settings.db_pool_recycle_seconds,
    pool_reset_on_return="rollback",
    connect_args={
        "connect_timeout": settings.db_connect_timeout_seconds,
        "read_timeout": settings.db_io_timeout_seconds,
        "write_timeout": settings.db_io_timeout_seconds,
        "charset": "utf8mb4",
    },
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
