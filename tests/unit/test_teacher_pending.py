"""教师待辅导列表：规则必须由真实记录计算，且可解释。"""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models import HintRecord, Submission, new_submission_id


def _add_submission(
    db,
    student_id: str,
    status: str,
    minutes_ago: int,
) -> str:
    submission = Submission(
        id=new_submission_id(),
        student_id=student_id,
        problem_id=1,
        source_code="#include <stdio.h>\nint main(void){return 0;}/* 中文注释 */",
        language="c",
        status=status,
        error_category="NONE" if status == "ACCEPTED" else "OUTPUT_MISMATCH",
        passed_cases=0,
        total_cases=4,
        execution_time_ms=10,
        diagnosis_knowledge_point="循环结构",
        diagnosis_evidence="公开用例 1 未通过",
        diagnosis_source="RULE",
        diagnosis_confidence="MEDIUM",
        submitted_at=utcnow() - timedelta(minutes=minutes_ago),
    )
    db.add(submission)
    db.flush()
    return submission.id


def test_teacher_pending_tutoring_rules(client: TestClient) -> None:
    db = SessionLocal()
    try:
        # A：3 次失败，最近一次仍未通过 → 应进入待辅导
        for minutes in (3, 2, 1):
            _add_submission(db, "pending-3fails", "WRONG_ANSWER", minutes)

        # B：3 次失败后最近一次通过 → 应移出
        for minutes in (5, 4, 3):
            _add_submission(db, "pending-passed", "WRONG_ANSWER", minutes)
        _add_submission(db, "pending-passed", "ACCEPTED", 1)

        # C：仅 1 次失败，但已解锁第 3 层 → 应进入待辅导
        submission_c = _add_submission(db, "pending-hint3", "WRONG_ANSWER", 2)
        db.add(
            HintRecord(
                submission_id=submission_c,
                hint_level=3,
                hint_content="第三层提示",
                source="RULE",
                is_fallback=True,
                is_unlocked=True,
            )
        )

        # D：2 次失败 + 最后一次 SYSTEM_ERROR → 系统错误不计学生错，且不算最近学生提交
        _add_submission(db, "pending-sys", "WRONG_ANSWER", 5)
        _add_submission(db, "pending-sys", "WRONG_ANSWER", 4)
        _add_submission(db, "pending-sys", "SYSTEM_ERROR", 1)

        # E：只有 2 次失败 → 未达到阈值
        _add_submission(db, "pending-2fails", "WRONG_ANSWER", 3)
        _add_submission(db, "pending-2fails", "WRONG_ANSWER", 2)

        # F：有第 3 层记录但尚未解锁 → 不计入最高已解锁层级
        submission_f = _add_submission(db, "pending-locked-hint", "WRONG_ANSWER", 2)
        db.add(
            HintRecord(
                submission_id=submission_f,
                hint_level=3,
                hint_content="第三层提示（未解锁）",
                source="AI",
                is_fallback=False,
                is_unlocked=False,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/teacher/overview")
    assert response.status_code == 200
    body = response.json()
    rows = {item["student_id"]: item for item in body["pending_tutoring"]}

    assert "pending-3fails" in rows
    assert rows["pending-3fails"]["failure_count"] == 3
    assert rows["pending-3fails"]["last_status"] == "WRONG_ANSWER"
    assert rows["pending-3fails"]["problem_id"] == 1

    assert "pending-hint3" in rows
    assert rows["pending-hint3"]["max_hint_level"] == 3
    assert rows["pending-hint3"]["failure_count"] == 1

    assert "pending-passed" not in rows
    assert "pending-sys" not in rows
    assert "pending-2fails" not in rows
    assert "pending-locked-hint" not in rows
    assert body["system_error_count"] >= 1
    assert body["pending_tutoring_rule"]
