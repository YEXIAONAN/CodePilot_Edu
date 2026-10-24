"""基础接口测试：题目查询、参数校验、非公开用例不泄露、令牌与依赖故障。"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import get_db
from app.main import app


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "ok"
    assert body["database"] is True
    assert body["database_status"] == "ok"
    assert body["database_latency_ms"] >= 0


def test_api_requires_demo_token_on_all_routes() -> None:
    with TestClient(app) as anonymous:
        requests = [
            anonymous.get("/api/v1/problems"),
            anonymous.get("/api/v1/problems/1"),
            anonymous.get("/api/v1/submissions/sub-000000000000"),
            anonymous.post(
                "/api/v1/submissions",
                json={
                    "problem_id": 1,
                    "student_id": "demo-student-01",
                    "language": "c",
                    "source_code": "int main(void){return 0;}",
                },
            ),
            anonymous.post(
                "/api/v1/submissions/sub-000000000000/hints", json={"level": 1}
            ),
            anonymous.get("/api/v1/students/demo-student-01/progress"),
            anonymous.get("/api/v1/teacher/overview"),
        ]
        for response in requests:
            assert response.status_code == 401, response.text
            assert response.json()["error"]["code"] == "UNAUTHORIZED"
        # 健康检查不属于 /api/v1，保持免令牌可访问
        assert anonymous.get("/health").status_code == 200


def test_token_missing_on_server_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "demo_token", "")
    with TestClient(app) as anonymous:
        response = anonymous.get("/api/v1/problems")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DEMO_TOKEN_NOT_CONFIGURED"


def test_database_unavailable_returns_503(client: TestClient) -> None:
    bad_engine = create_engine(
        "mysql+pymysql://codepilot@127.0.0.1:1/codepilot_edu",
        connect_args={"connect_timeout": 1},
    )
    BadSession = sessionmaker(bind=bad_engine, autoflush=False, expire_on_commit=False)

    def bad_db():
        db = BadSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = bad_db
    try:
        response = client.get("/api/v1/problems")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"

        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["api"] == "ok"
        assert health.json()["database"] is False
        assert health.json()["database_status"] == "unavailable"
    finally:
        app.dependency_overrides.clear()
        bad_engine.dispose()


def test_list_problems(client: TestClient) -> None:
    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    problems = response.json()
    assert len(problems) == 3
    assert {item["id"] for item in problems} == {1, 2, 3}


def test_problem_detail_hides_hidden_cases(client: TestClient) -> None:
    response = client.get("/api/v1/problems/1")
    assert response.status_code == 200
    raw = response.text
    body = response.json()
    assert len(body["public_cases"]) == 2
    # 非公开用例的输入与预期输出不得出现在响应中
    assert "5050" not in raw
    assert '"100\\n"' not in raw and '"10\\n"' not in raw


def test_problem_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/problems/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROBLEM_NOT_FOUND"


def test_submission_validation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/submissions",
        json={
            "problem_id": 1,
            "student_id": "demo-student-01",
            "language": "python",
            "source_code": "print(1)",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_submission_id_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/submissions/not-a-submission-id")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_submission_source_size_limit(client: TestClient) -> None:
    response = client.post(
        "/api/v1/submissions",
        json={
            "problem_id": 1,
            "student_id": "demo-student-02",
            "language": "c",
            "source_code": "/*" + "x" * (17 * 1024) + "*/",
        },
    )
    assert response.status_code == 422


def test_submission_unknown_problem(client: TestClient) -> None:
    response = client.post(
        "/api/v1/submissions",
        json={
            "problem_id": 999,
            "student_id": "demo-student-03",
            "language": "c",
            "source_code": "int main(void){return 0;}",
        },
    )
    assert response.status_code == 404


def test_submission_rejected_when_docker_unavailable(client: TestClient, monkeypatch) -> None:
    from app.services import judge_service

    monkeypatch.setattr(judge_service, "_check_docker", lambda force=False: (False, False))
    response = client.post(
        "/api/v1/submissions",
        json={
            "problem_id": 1,
            "student_id": "demo-student-04",
            "language": "c",
            "source_code": "#include <stdio.h>\nint main(void){printf(\"15\\n\");return 0;}",
        },
    )
    # 安全红线：Docker 不可用时明确报错，绝不回退宿主机执行
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "JUDGE_UNAVAILABLE"
