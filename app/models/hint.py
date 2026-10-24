"""分层提示记录模型。同一提交同一层级只允许一份有效记录。"""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utcnow

_TABLE_OPTS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}


class HintRecord(Base):
    __tablename__ = "hint_records"
    # 唯一约束同时充当 (submission_id, hint_level) 查询索引。
    __table_args__ = (
        UniqueConstraint(
            "submission_id", "hint_level", name="uq_hint_records_submission_level"
        ),
        _TABLE_OPTS,
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False)
    hint_content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(8), nullable=False, default="RULE")
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # AI 可一次生成三层，但未轮到请求的层级先存为未解锁；只有被正式返回后才计入统计。
    is_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
