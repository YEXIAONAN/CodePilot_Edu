"""端到端演示脚本（P0 验收主线）。

链路：正确代码 ACCEPTED → 语法错 COMPILATION_ERROR → WRONG_ANSWER 显示真实差异
→ 请求第 1 层 → 尝试第 3 层被拒 → 请求第 2 层 → 再提交 ACCEPTED → 学生/教师记录。

前置：后端已启动（默认 http://127.0.0.1:8000），MySQL 与 Docker 评测环境就绪。
用法：
    python scripts/demo.py
令牌从 .env 的 DEMO_TOKEN 读取，并作为 X-Demo-Token 发送。
"""

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
STUDENT_ID = "demo-student-01"
CODES_DIR = ROOT / "tests" / "fixtures" / "codes"

WRONG_CODE = (CODES_DIR / "problem1_wrong_boundary.c").read_text(encoding="utf-8")
CORRECT_CODE = (CODES_DIR / "problem1_accepted.c").read_text(encoding="utf-8")
COMPILE_ERROR_CODE = (CODES_DIR / "problem1_compile_error.c").read_text(encoding="utf-8")


def _title(text: str) -> None:
    print(f"\n{'=' * 60}\n{text}\n{'=' * 60}")


def _submit(client: httpx.Client, source_code: str, label: str) -> dict:
    response = client.post(
        "/api/v1/submissions",
        json={
            "problem_id": 1,
            "student_id": STUDENT_ID,
            "language": "c",
            "source_code": source_code,
        },
    )
    print(f"  HTTP {response.status_code}  {label}")
    if response.status_code != 200:
        print(f"  提交失败：{response.text}")
        print("  请确认 MySQL、Docker Desktop 与 judge-c:latest 镜像均就绪。")
        raise SystemExit(1)
    result = response.json()
    print(
        f"  状态: {result['status']}  "
        f"通过 {result['passed_cases']}/{result['total_cases']}"
    )
    diagnosis = result.get("diagnosis") or {}
    if diagnosis:
        print(
            f"  错因: {diagnosis.get('category')}  "
            f"置信: {diagnosis.get('confidence')}  确定程度: {diagnosis.get('certainty')}"
        )
        print(f"  可能原因: {diagnosis.get('possible_cause')}")
        print(f"  证据: {diagnosis.get('evidence')}")
    if result["status"] == "COMPILATION_ERROR":
        print(f"  编译信息: {result['message'][:300]}")
    for case in result["cases"]:
        if case["is_public"]:
            print(
                f"    用例 {case['case_index']}（公开） {case['status']}"
                f" 预期「{(case['expected_output'] or '').strip()}」"
                f" 实际「{(case['actual_output'] or '').strip()}」"
            )
        else:
            print(f"    用例 {case['case_index']}（非公开） {case['status']}")
    return result


def main() -> int:
    if not settings.demo_token:
        print("DEMO_TOKEN 未配置：接口会失败关闭。请先在 .env 中设置。")
        return 1

    headers = {"X-Demo-Token": settings.demo_token}
    client = httpx.Client(base_url=BASE_URL, headers=headers, timeout=60)

    _title("1. 查看题目列表")
    problems = client.get("/api/v1/problems")
    if problems.status_code != 200:
        print(f"  HTTP {problems.status_code}: {problems.text}")
        return 1
    for item in problems.json():
        print(f"  [{item['id']}] {item['title']}  知识点: {'、'.join(item['knowledge_points'])}")

    _title("2. 正确代码 → ACCEPTED")
    _submit(client, CORRECT_CODE, "基线：正确解")

    _title("3. 语法错误代码 → COMPILATION_ERROR")
    _submit(client, COMPILE_ERROR_CODE, "语法错误")

    _title("4. 边界错误代码 → WRONG_ANSWER 与真实差异")
    wrong = _submit(client, WRONG_CODE, "循环边界错误")
    submission_id = wrong["submission_id"]

    _title("5. 请求第 1 层提示")
    first = client.post(f"/api/v1/submissions/{submission_id}/hints", json={"level": 1})
    if first.status_code != 200:
        print(f"  第 1 层失败：{first.status_code} {first.text}")
        return 1
    body = first.json()
    print(f"  source={body['source']} fallback={body['is_fallback']}")
    print(f"  {body['hint']}")

    _title("6. 尝试跳过第 2 层，直接请求第 3 层（应被拒绝）")
    skipped = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 3}
    )
    print(f"  HTTP {skipped.status_code}  {skipped.json().get('error', {})}")
    if skipped.status_code != 400:
        print("  预期 400 HINT_LEVEL_INVALID，但实际未被拒绝。")
        return 1

    _title("7. 按顺序请求第 2 层")
    second = client.post(
        f"/api/v1/submissions/{submission_id}/hints", json={"level": 2}
    )
    if second.status_code != 200:
        print(f"  第 2 层失败：{second.status_code} {second.text}")
        return 1
    body = second.json()
    print(f"  source={body['source']} fallback={body['is_fallback']}")
    print(f"  {body['hint']}")

    _title("8. 修改后再次提交 → ACCEPTED")
    fixed = _submit(client, CORRECT_CODE, "修正后")

    _title("9. 查看学生学习记录")
    progress = client.get(f"/api/v1/students/{STUDENT_ID}/progress").json()
    print(f"  总提交: {progress['total_submissions']}  通过: {progress['accepted_count']}")
    print(f"  错因分布: {progress['error_category_distribution']}")
    print(f"  提示使用: {progress['hint_usage']}")

    _title("10. 查看教师待辅导列表与汇总")
    overview = client.get("/api/v1/teacher/overview").json()
    print(f"  提交总数: {overview['total_submissions']}  学生数: {overview['distinct_students']}")
    print(f"  已完成题目数: {overview['completed_problem_count']}")
    print(f"  错误分布: {overview['error_distribution']}")
    print(f"  知识点错误分布: {overview['knowledge_point_errors']}")
    print(f"  规则: {overview['pending_tutoring_rule']}")
    print(f"  待辅导条目: {len(overview['pending_tutoring'])}")
    for item in overview["pending_tutoring"][:5]:
        print(
            f"    {item['student_id']} / 题目 {item['problem_id']} / "
            f"最近 {item['last_status']} / 失败 {item['failure_count']} / "
            f"最高解锁层 {item['max_hint_level']}"
        )

    print(f"\n最终提交：{fixed['submission_id']}  状态 {fixed['status']}")
    print("演示流程完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
