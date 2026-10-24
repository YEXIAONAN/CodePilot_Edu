"""规则诊断单元测试：验证不得凭输出不同臆断具体错因。"""

from app.core.enums import SubmissionStatus
from app.services.diagnosis_service import diagnose
from app.services.judge_service import CaseOutcome, JudgeOutcome

KNOWLEDGE_POINTS = ["循环结构", "循环边界"]


def _outcome(status: str, cases: list[CaseOutcome] | None = None) -> JudgeOutcome:
    cases = cases or []
    return JudgeOutcome(
        status=status,
        passed_cases=sum(1 for case in cases if case.status == SubmissionStatus.ACCEPTED),
        total_cases=len(cases),
        execution_time_ms=10,
        cases=cases,
    )


def test_accepted_has_no_diagnosis() -> None:
    outcome = _outcome(SubmissionStatus.ACCEPTED, [
        CaseOutcome(0, 1, True, SubmissionStatus.ACCEPTED, 3, "15", "15"),
    ])
    assert diagnose(outcome, KNOWLEDGE_POINTS, "1 到 N 求和") is None


def test_wrong_answer_with_public_evidence_is_output_mismatch() -> None:
    outcome = _outcome(SubmissionStatus.WRONG_ANSWER, [
        CaseOutcome(0, 1, True, SubmissionStatus.WRONG_ANSWER, 3, "16", "15"),
        CaseOutcome(1, 2, False, SubmissionStatus.WRONG_ANSWER, 3, "1", "1"),
    ])
    diagnosis = diagnose(outcome, KNOWLEDGE_POINTS, "1 到 N 求和")
    assert diagnosis is not None
    assert diagnosis.category == "OUTPUT_MISMATCH"
    assert "公开用例 1" in diagnosis.evidence


def test_wrong_answer_with_only_hidden_failure_is_unknown() -> None:
    outcome = _outcome(SubmissionStatus.WRONG_ANSWER, [
        CaseOutcome(0, 1, True, SubmissionStatus.ACCEPTED, 3, "15", "15"),
        CaseOutcome(1, 2, False, SubmissionStatus.WRONG_ANSWER, 3, "", ""),
    ])
    diagnosis = diagnose(outcome, KNOWLEDGE_POINTS, "1 到 N 求和")
    assert diagnosis is not None
    assert diagnosis.category == "UNKNOWN_ERROR"
    assert diagnosis.confidence == "UNDETERMINED"


def test_compilation_error_maps_to_syntax() -> None:
    outcome = JudgeOutcome(
        status=SubmissionStatus.COMPILATION_ERROR,
        passed_cases=0,
        total_cases=2,
        execution_time_ms=5,
        compile_message="main.c:3:5: error: expected ';' before '}' token",
    )
    diagnosis = diagnose(outcome, KNOWLEDGE_POINTS, "1 到 N 求和")
    assert diagnosis is not None
    assert diagnosis.category == "SYNTAX_ERROR"
    assert diagnosis.confidence == "HIGH"
    assert "expected" in diagnosis.evidence


def test_system_error_has_no_student_diagnosis() -> None:
    outcome = _outcome(SubmissionStatus.SYSTEM_ERROR)
    assert diagnose(outcome, KNOWLEDGE_POINTS, "1 到 N 求和") is None


def test_timeout_is_not_claimed_as_loop_boundary_error() -> None:
    outcome = _outcome(SubmissionStatus.TIME_LIMIT_EXCEEDED, [
        CaseOutcome(0, 1, True, SubmissionStatus.TIME_LIMIT_EXCEEDED, 2000, "", "15"),
    ])
    diagnosis = diagnose(outcome, KNOWLEDGE_POINTS, "1 到 N 求和")
    assert diagnosis is not None
    assert diagnosis.category == "UNKNOWN_ERROR"
