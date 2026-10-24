"""测试夹具：所有数据库测试连接真实 MySQL 测试库，不使用 SQLite 顶替。

安全约束：
- TEST_DATABASE_URL 必须显式提供，且库名必须以 _test 结尾；
- 测试启动时会重建该测试库的表，不会触碰主库。
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("AI_ENABLED", "false")

from sqlalchemy.engine import make_url  # noqa: E402

from app.core.config import settings  # noqa: E402

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or settings.test_database_url
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "缺少 TEST_DATABASE_URL：pytest 必须连接真实 MySQL 测试库。"
        "请在 .env 中配置 mysql+pymysql://.../codepilot_edu_test?..."
    )
if not TEST_DATABASE_URL.startswith("mysql+pymysql://"):
    raise RuntimeError("TEST_DATABASE_URL 仅支持 mysql+pymysql://，禁止 SQLite")

_test_db_name = make_url(TEST_DATABASE_URL).database or ""
_main_db_name = make_url(settings.database_url).database or ""
if not _test_db_name.endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL 的库名必须以 _test 结尾，避免误删主库")
if _test_db_name == _main_db_name:
    raise RuntimeError("TEST_DATABASE_URL 不能与 DATABASE_URL 指向同一个库")

# 在导入 engine 之前改写配置，确保测试进程只连接测试库。
settings.database_url = TEST_DATABASE_URL
settings.demo_token = settings.demo_token or "test-demo-token"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DEMO_TOKEN"] = settings.demo_token

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from scripts.seed_data import seed  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
seed()


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        test_client.headers["X-Demo-Token"] = settings.demo_token
        yield test_client
