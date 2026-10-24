"""真实 MySQL 行为测试：驱动、字符集、中文往返、种子幂等。"""

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.db.session import SessionLocal, engine
from app.models import Problem, Submission, TestCase as ProblemTestCase, new_submission_id
from scripts.seed_data import seed


def test_engine_is_real_mysql_utf8mb4() -> None:
    assert engine.url.drivername == "mysql+pymysql"
    with engine.connect() as connection:
        charset = connection.execute(text("SELECT @@character_set_database")).scalar()
        storage_engine = connection.execute(
            text("SELECT @@default_storage_engine")
        ).scalar()
    assert charset == "utf8mb4"
    assert str(storage_engine).lower() == "innodb"


def test_chinese_text_round_trip(client: TestClient) -> None:
    db = SessionLocal()
    try:
        submission_id = new_submission_id()
        source_code = (
            "#include <stdio.h>\n"
            "int main(void){ /* 中文注释：循环求和 */ printf(\"0\\n\"); return 0; }\n"
        )
        submission = Submission(
            id=submission_id,
            student_id="chinese-student-01",
            problem_id=1,
            source_code=source_code,
            language="c",
            status="WRONG_ANSWER",
            error_category="OUTPUT_MISMATCH",
            passed_cases=0,
            total_cases=4,
            execution_time_ms=12,
            diagnosis_knowledge_point="循环结构",
            diagnosis_evidence="公开用例 1 未通过：预期输出「15」，实际输出「0」",
            diagnosis_source="RULE",
            diagnosis_confidence="MEDIUM",
            diagnosis_json={
                "category": "OUTPUT_MISMATCH",
                "knowledge_point": "循环结构",
                "evidence": "公开用例 1 未通过：预期输出「15」，实际输出「0」",
                "possible_cause": "循环边界可能少执行一次",
                "source": "RULE",
                "confidence": "MEDIUM",
                "certainty": "待确认",
            },
        )
        db.add(submission)
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        stored = db.get(Submission, submission_id)
        assert stored is not None
        assert "中文注释" in stored.source_code
        assert stored.diagnosis_json["possible_cause"] == "循环边界可能少执行一次"
        assert "循环结构" in stored.diagnosis_knowledge_point
    finally:
        db.close()

    response = client.get(f"/api/v1/submissions/{submission_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["diagnosis"]["possible_cause"] == "循环边界可能少执行一次"
    assert body["diagnosis"]["certainty"] == "待确认"
    assert "预期输出「15」" in body["diagnosis"]["evidence"]

    problem = client.get("/api/v1/problems/1")
    assert problem.status_code == 200
    assert problem.json()["title"] == "1 到 N 求和"


def test_seed_is_idempotent_and_preserves_history() -> None:
    db = SessionLocal()
    try:
        before_problems = db.scalar(select(func.count()).select_from(Problem))
        before_cases = db.scalar(select(func.count()).select_from(ProblemTestCase))
        before_submissions = db.scalar(select(func.count()).select_from(Submission))
    finally:
        db.close()

    seed()

    db = SessionLocal()
    try:
        after_problems = db.scalar(select(func.count()).select_from(Problem))
        after_cases = db.scalar(select(func.count()).select_from(ProblemTestCase))
        after_submissions = db.scalar(select(func.count()).select_from(Submission))
    finally:
        db.close()

    assert before_problems == after_problems == 3
    assert before_cases == after_cases
    assert before_submissions == after_submissions
