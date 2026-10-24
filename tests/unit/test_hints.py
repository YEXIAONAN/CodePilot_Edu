"""分层提示测试：层级不可跳、并发唯一、AI 不可用时如实标记 RULE 降级。"""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import HintRecord, Submission
from app.services import hint_service


def _create_failed_submission(student_id: str, status: str = "WRONG_ANSWER") -> str:
    db = SessionLocal()
    try:
        submission = Submission(
            student_id=student_id,
            problem_id=1,
            source_code="#include <stdio.h>\nint main(void){return 0;}",
            language="c",
            status=status,
            error_category="OUTPUT_MISMATCH",
            passed_cases=0,
            total_cases=2,
            execution_time_ms=10,
            diagnosis_knowledge_point="循环结构",
            diagnosis_evidence="公开用例 1 未通过：预期输出「15」，实际输出「0」",
            diagnosis_source="RULE",
            diagnosis_confidence="MEDIUM",
        )
        db.add(submission)
        db.commit()
        return submission.id
    finally:
        db.close()


def test_hint_level_cannot_skip(client: TestClient) -> None:
    submission_id = _create_failed_submission("hint-student-01")
    response = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 3}
    )
    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "HINT_LEVEL_INVALID"
    assert body["detail"] == "1"


def test_hint_falls_back_to_rule_when_ai_disabled(client: TestClient) -> None:
    submission_id = _create_failed_submission("hint-student-02")
    response = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == 1
    assert body["source"] == "RULE"
    assert body["is_fallback"] is True
    assert body["hint"]

    second = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 2}
    )
    assert second.status_code == 200
    assert second.json()["level"] == 2
    assert second.json()["hint"] != body["hint"]


def test_hint_is_stable_when_requested_twice(client: TestClient) -> None:
    submission_id = _create_failed_submission("hint-student-03")
    first = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 1}
    )
    again = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 1}
    )
    assert first.json()["hint"] == again.json()["hint"]


def test_hint_rejected_for_accepted_submission(client: TestClient) -> None:
    submission_id = _create_failed_submission("hint-student-04", status="ACCEPTED")
    response = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 1}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "HINT_NOT_AVAILABLE"


def test_hint_rejected_for_system_error_submission(client: TestClient) -> None:
    submission_id = _create_failed_submission("hint-student-07", status="SYSTEM_ERROR")
    response = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 1}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "HINT_NOT_AVAILABLE"


def test_pregenerated_locked_levels_cannot_be_skipped(client: TestClient) -> None:
    submission_id = _create_failed_submission("hint-student-05")
    db = SessionLocal()
    try:
        db.add_all(
            [
                HintRecord(
                    submission_id=submission_id,
                    hint_level=1,
                    hint_content="第一层内容",
                    source="AI",
                    is_fallback=False,
                    is_unlocked=True,
                ),
                HintRecord(
                    submission_id=submission_id,
                    hint_level=2,
                    hint_content="第二层内容",
                    source="AI",
                    is_fallback=False,
                    is_unlocked=False,
                ),
                HintRecord(
                    submission_id=submission_id,
                    hint_level=3,
                    hint_content="第三层内容",
                    source="AI",
                    is_fallback=False,
                    is_unlocked=False,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    skipped = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 3}
    )
    assert skipped.status_code == 400
    assert skipped.json()["error"]["code"] == "HINT_LEVEL_INVALID"

    second = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 2}
    )
    assert second.status_code == 200
    assert second.json()["hint"] == "第二层内容"

    third = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 3}
    )
    assert third.status_code == 200
    assert third.json()["hint"] == "第三层内容"


async def test_concurrent_same_level_hint_creates_one_record() -> None:
    submission_id = _create_failed_submission("hint-student-06")

    async def request_once():
        db = SessionLocal()
        try:
            return await hint_service.request_hint(db, submission_id, 1)
        finally:
            db.close()

    first, second = await asyncio.gather(request_once(), request_once())
    assert first.hint == second.hint

    db = SessionLocal()
    try:
        count = db.scalar(
            select(func.count())
            .select_from(HintRecord)
            .where(
                HintRecord.submission_id == submission_id,
                HintRecord.hint_level == 1,
            )
        )
        assert count == 1
    finally:
        db.close()
