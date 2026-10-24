"""SQLAlchemy 声明式基类与 MySQL 通用字段类型。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase

# MySQL 的 DATETIME 不保存时区，且默认精度为秒。这里统一：
# - 存 UTC 无时区时间（展示时由前端按用户时区转换）；
# - MySQL 下使用 DATETIME(6)，避免同一秒内多次提交排序不稳定。
UTCDateTime = DateTime(timezone=False).with_variant(DATETIME(fsp=6), "mysql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass
