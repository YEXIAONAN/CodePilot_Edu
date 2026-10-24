"""初始化 MySQL 表结构（可重复执行，不清空已有数据）。

前置：MySQL 8.4 已启动，DATABASE_URL 指向业务账号可访问的库。
建库与授权由 docker-compose.yml / scripts/mysql/01_create_test_db.sql 完成，
本脚本只负责建表与字符集校验，不执行任何 DROP。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

import app.models  # noqa: F401,E402  注册模型
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402


def _verify_mysql_environment() -> None:
    with engine.connect() as connection:
        charset, collation, storage_engine = connection.execute(
            text(
                "SELECT @@character_set_database, @@collation_database, "
                "@@default_storage_engine"
            )
        ).one()
        if charset != "utf8mb4":
            raise SystemExit(
                f"数据库字符集为 {charset}，要求 utf8mb4。请重建库或执行 "
                "ALTER DATABASE ... CHARACTER SET utf8mb4;"
            )
        if str(storage_engine).lower() != "innodb":
            raise SystemExit(f"默认存储引擎为 {storage_engine}，要求 InnoDB")

        rows = connection.execute(
            text(
                "SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE()"
            )
        ).all()
        bad = [
            (name, table_collation)
            for name, table_collation in rows
            if not str(table_collation or "").startswith("utf8mb4")
        ]
        if bad:
            raise SystemExit(f"以下表不是 utf8mb4：{bad}")

    print(f"字符集校验通过：utf8mb4 / {collation} / {storage_engine}")


def main() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        message = str(getattr(exc, "orig", exc))
        if "Unknown database" in message or "1049" in message:
            print(
                "目标数据库不存在。请先启动 MySQL 容器（docker compose up -d），"
                "或由 DBA 创建 utf8mb4 数据库并授权业务账号。",
                file=sys.stderr,
            )
        else:
            print(f"数据库连接失败：{type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from exc

    _verify_mysql_environment()
    print("MySQL 表已创建（重复执行不会清空已有提交记录）")


if __name__ == "__main__":
    main()
