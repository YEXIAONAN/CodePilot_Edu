"""集成测试：真实 Docker 评测链路（T01-T10）。

运行前提：Docker Desktop 已启动，且已构建 judge-c:latest 镜像：
    docker build -t judge-c:latest runner/
未满足时整组自动跳过，并在测试报告中如实记录跳过原因。
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services import judge_service

CODES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "codes"

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(
        not judge_service.docker_status(),
        reason="Docker 评测环境不可用（需 Docker Desktop 与 judge-c:latest 镜像）",
    ),
]


def _submit(client: TestClient, problem_id: int, student_id: str, filename: str):
    source = (CODES_DIR / filename).read_text(encoding="utf-8")
    return client.post(
        "/api/v1/submissions",
        json={
            "problem_id": problem_id,
            "student_id": student_id,
            "language": "c",
            "source_code": source,
        },
    )


@pytest.mark.parametrize(
    ("problem_id", "filename"),
    [
        (1, "problem1_accepted.c"),
        (2, "problem2_accepted.c"),
        (3, "problem3_accepted.c"),
    ],
)
def test_t01_accepted(client: TestClient, problem_id: int, filename: str) -> None:
    response = _submit(client, problem_id, f"t01-student-p{problem_id}", filename)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ACCEPTED"
    assert body["passed_cases"] == body["total_cases"]
    assert body["diagnosis"] is None


def test_t02_compilation_error(client: TestClient) -> None:
    response = _submit(client, 1, "t02-student", "problem1_compile_error.c")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPILATION_ERROR"
    assert body["diagnosis"]["category"] == "SYNTAX_ERROR"
    assert "error" in body["message"].lower()


def test_t03_boundary_error_is_wrong_answer_not_overclaimed(client: TestClient) -> None:
    response = _submit(client, 1, "t03-student", "problem1_wrong_boundary.c")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "WRONG_ANSWER"
    # 证据不足时不得直接断言循环边界错误
    assert body["diagnosis"]["category"] in {"OUTPUT_MISMATCH", "UNKNOWN_ERROR"}


def test_t04_output_format_mismatch(client: TestClient) -> None:
    response = _submit(client, 1, "t04-student", "problem1_wrong_format.c")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "WRONG_ANSWER"
    assert body["passed_cases"] == 0


def test_t05_time_limit_exceeded(client: TestClient) -> None:
    response = _submit(client, 1, "t05-student", "problem1_timeout.c")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "TIME_LIMIT_EXCEEDED"


def test_t06_runtime_error(client: TestClient) -> None:
    response = _submit(client, 1, "t06-student", "problem1_runtime_error.c")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"RUNTIME_ERROR", "RESOURCE_LIMIT_EXCEEDED"}


def test_t10_huge_output_is_contained(client: TestClient) -> None:
    response = _submit(client, 1, "t10-student", "problem1_huge_output.c")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"RESOURCE_LIMIT_EXCEEDED", "TIME_LIMIT_EXCEEDED"}
    # 响应体不得被学生程序的巨量输出撑爆
    assert len(response.content) < 20000


def test_no_stale_containers_after_runs(client: TestClient) -> None:
    import subprocess

    listing = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "name=judge-"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert listing.stdout.strip() == ""
