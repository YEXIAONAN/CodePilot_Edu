"""规则诊断：把真实评测证据翻译成学习层面的错误归类。

原则（任务书 P0-04）：
- 诊断类别是学习归类，不等同于评测状态。
- WRONG_ANSWER 默认只给 OUTPUT_MISMATCH / UNKNOWN_ERROR，
  不得仅凭输出不同就断言学生写错了循环边界。
- 证据不足时一律返回 UNKNOWN_ERROR。
"""

from dataclasses import dataclass

from app.core.enums import Confidence, DiagnosisCategory, DiagnosisSource, SubmissionStatus
from app.services.judge_service import JudgeOutcome

_CERTAINTY_TEXT = {
    Confidence.HIGH.value: "有明确依据",
    Confidence.MEDIUM.value: "待确认",
    Confidence.LOW.value: "待确认",
    Confidence.UNDETERMINED.value: "无法判断",
}

_POSSIBLE_CAUSE = {
    DiagnosisCategory.SYNTAX_ERROR.value: "语法结构不符合 C 语言规则，例如缺少分号、括号不匹配或变量未声明",
    DiagnosisCategory.VARIABLE_ERROR.value: "变量使用方式可能不合法，例如除数为 0、下标越界或使用前未初始化",
    DiagnosisCategory.OUTPUT_MISMATCH.value: "输出内容与题目预期不一致，具体逻辑原因需结合代码进一步确认",
    DiagnosisCategory.CONDITION_ERROR.value: "条件分支的边界或覆盖范围可能与题意不一致",
    DiagnosisCategory.LOOP_BOUNDARY_ERROR.value: "循环边界可能多执行或少执行一次",
    DiagnosisCategory.UNKNOWN_ERROR.value: "现有证据不足，无法确定具体原因",
}


@dataclass(frozen=True)
class Diagnosis:
    category: str
    knowledge_point: str
    evidence: str
    possible_cause: str
    source: str
    confidence: str
    certainty: str


def _first_knowledge_point(knowledge_points: list[str]) -> str:
    return knowledge_points[0] if knowledge_points else ""


def _build(
    category: DiagnosisCategory,
    *,
    knowledge_point: str,
    evidence: str,
    confidence: Confidence,
) -> Diagnosis:
    return Diagnosis(
        category=category.value,
        knowledge_point=knowledge_point,
        evidence=evidence,
        possible_cause=_POSSIBLE_CAUSE[category.value],
        source=DiagnosisSource.RULE.value,
        confidence=confidence.value,
        certainty=_CERTAINTY_TEXT[confidence.value],
    )


def _public_failure_evidence(outcome: JudgeOutcome) -> str | None:
    for case in outcome.cases:
        if case.is_public and case.status != SubmissionStatus.ACCEPTED:
            expected = case.expected_output.strip()[:120]
            actual = case.actual_output.strip()[:120]
            return (
                f"公开用例 {case.index + 1} 未通过：预期输出「{expected}」，"
                f"实际输出「{actual}」（状态 {case.status}）"
            )
    return None


def _first_failure(outcome: JudgeOutcome):
    for case in outcome.cases:
        if case.status != SubmissionStatus.ACCEPTED:
            return case
    return None


def diagnose(
    outcome: JudgeOutcome, knowledge_points: list[str], problem_title: str
) -> Diagnosis | None:
    if outcome.status == SubmissionStatus.ACCEPTED:
        return None

    # 评测基础设施故障不是学生的学习错误，不生成诊断，也不计入错因分布。
    if outcome.status == SubmissionStatus.SYSTEM_ERROR:
        return None

    knowledge_point = _first_knowledge_point(knowledge_points)

    if outcome.status == SubmissionStatus.COMPILATION_ERROR:
        first_line = next(
            (line for line in outcome.compile_message.splitlines() if "error" in line.lower()),
            outcome.compile_message.splitlines()[0] if outcome.compile_message else "编译失败",
        )
        return _build(
            DiagnosisCategory.SYNTAX_ERROR,
            knowledge_point="语法基础",
            evidence=f"编译失败：{first_line.strip()[:300]}",
            confidence=Confidence.HIGH,
        )

    if outcome.status == SubmissionStatus.TIME_LIMIT_EXCEEDED:
        case = _first_failure(outcome)
        return _build(
            DiagnosisCategory.UNKNOWN_ERROR,
            knowledge_point=knowledge_point,
            evidence=(
                f"用例 {case.index + 1} 运行超过时间限制仍未结束"
                if case
                else "评测整体超时"
            ),
            confidence=Confidence.UNDETERMINED,
        )

    if outcome.status == SubmissionStatus.RESOURCE_LIMIT_EXCEEDED:
        return _build(
            DiagnosisCategory.UNKNOWN_ERROR,
            knowledge_point=knowledge_point,
            evidence="程序触发资源限制（输出过大或内存耗尽），无法进一步定位具体原因",
            confidence=Confidence.UNDETERMINED,
        )

    if outcome.status == SubmissionStatus.RUNTIME_ERROR:
        case = _first_failure(outcome)
        detail = (case.error_message if case else "").strip()[:200]
        category = DiagnosisCategory.UNKNOWN_ERROR
        confidence = Confidence.UNDETERMINED
        if "division by zero" in detail.lower() or "浮点异常" in detail:
            category = DiagnosisCategory.VARIABLE_ERROR
            confidence = Confidence.MEDIUM
        return _build(
            category,
            knowledge_point=knowledge_point,
            evidence=f"用例 {case.index + 1} 运行异常：{detail or '进程非正常退出'}"
            if case
            else "程序运行异常",
            confidence=confidence,
        )

    if outcome.status == SubmissionStatus.WRONG_ANSWER:
        public_evidence = _public_failure_evidence(outcome)
        if public_evidence:
            return _build(
                DiagnosisCategory.OUTPUT_MISMATCH,
                knowledge_point=knowledge_point,
                evidence=f"题目「{problem_title}」{public_evidence}",
                confidence=Confidence.MEDIUM,
            )
        return _build(
            DiagnosisCategory.UNKNOWN_ERROR,
            knowledge_point=knowledge_point,
            evidence=(
                f"公开用例全部通过，但非公开用例未通过"
                f"（{outcome.passed_cases}/{outcome.total_cases} 通过）"
            ),
            confidence=Confidence.UNDETERMINED,
        )

    return _build(
        DiagnosisCategory.UNKNOWN_ERROR,
        knowledge_point=knowledge_point,
        evidence=f"评测状态 {outcome.status}，未找到可归类的错误证据",
        confidence=Confidence.UNDETERMINED,
    )
