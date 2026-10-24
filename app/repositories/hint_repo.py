"""提示记录的数据访问。"""

from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.models import HintRecord


def list_for_submission(db: Session, submission_id: str) -> list[HintRecord]:
    statement = (
        select(HintRecord)
        .where(HintRecord.submission_id == submission_id)
        .order_by(HintRecord.hint_level)
    )
    return list(db.scalars(statement))


def get_level(db: Session, submission_id: str, level: int) -> HintRecord | None:
    statement = select(HintRecord).where(
        HintRecord.submission_id == submission_id,
        HintRecord.hint_level == level,
    )
    return db.scalars(statement).first()


def upsert_levels(db: Session, submission_id: str, rows: list[dict]) -> None:
    """按 (submission_id, hint_level) 幂等写入。

    并发请求同一层级时，唯一约束 + ON DUPLICATE KEY 决定谁先落库；
    后到者不覆盖已有内容，随后回读第一条记录返回，保证同一层级只有一份有效内容。
    """
    for row in rows:
        statement = mysql_insert(HintRecord).values(
            submission_id=submission_id,
            hint_level=row["hint_level"],
            hint_content=row["hint_content"],
            source=row["source"],
            is_fallback=row["is_fallback"],
            is_unlocked=row["is_unlocked"],
        )
        statement = statement.on_duplicate_key_update(
            hint_level=statement.inserted.hint_level
        )
        db.execute(statement)
    db.flush()


def unlock_level(db: Session, submission_id: str, level: int) -> bool:
    result = db.execute(
        update(HintRecord)
        .where(
            HintRecord.submission_id == submission_id,
            HintRecord.hint_level == level,
        )
        .values(is_unlocked=True)
    )
    return bool(result.rowcount)
