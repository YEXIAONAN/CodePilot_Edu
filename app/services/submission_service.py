"""提交流程编排：校验题目 → 调用评测 → 规则诊断 → 持久化。"""

import logging
from dataclasses import asdict

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import SubmissionStatus
from app.models import EvaluationDetail, Submission
from app.repositories import problem_repo, submission_repo
from app.schemas.submission import (
    CaseResultOut,
    DiagnosisOut,
    SubmissionCreate,
    SubmissionResultOut,
)
from app.services import diagnosis_service, judge_service

logger = logging.getLogger(__name__)


class ProblemNotFoundError(LookupError):
    pass


class NoTestCaseError(RuntimeError):
    pass


def _build_details(submission_id: str, outcome: judge_service.JudgeOutcome) -> list[EvaluationDetail]:
    details = []
    for case in outcome.cases:
        details.append(
            EvaluationDetail(
                submission_id=submission_id,
                test_case_id=case.test_case_id,
                status=case.status,
                execution_time_ms=case.time_ms,
                error_message=case.error_message[:1024],
                # 非公开用例不保存输出，避免评测数据经任何途径泄露
                actual_output=case.actual_output if case.is_public else "",
                expected_output=case.expected_output if case.is_public else "",
            )
        )
    return details


def _build_case_results(outcome: judge_service.JudgeOutcome) -> list[CaseResultOut]:
    results = []
    for case in outcome.cases:
        results.append(
            CaseResultOut(
                case_index=case.index + 1,
                is_public=case.is_public,
                status=case.status,
                execution_time_ms=case.time_ms,
                expected_output=case.expected_output[: settings.judge_max_output_bytes]
                if case.is_public
                else None,
                actual_output=case.actual_output[: settings.judge_max_output_bytes]
                if case.is_public
                else None,
                error_message=case.error_message[:500] or None,
            )
        )
    return results


async def submit_code(db: Session, payload: SubmissionCreate) -> SubmissionResultOut:
    problem = problem_repo.get_problem(db, payload.problem_id)
    if problem is None:
        raise ProblemNotFoundError(f"题目 {payload.problem_id} 不存在")

    problem_id = problem.id
    problem_title = problem.title
    knowledge_points = list(problem.knowledge_points)

    test_cases = problem_repo.list_test_cases(db, problem_id)
    if not test_cases:
        raise NoTestCaseError("题目缺少测试用例")

    selected = test_cases[: settings.judge_max_cases]
    specs = [
        judge_service.CaseSpec(
            index=index,
            test_case_id=case.id,
            input_data=case.input_data,
            expected_output=case.expected_output,
            is_public=case.is_public,
        )
        for index, case in enumerate(selected)
    ]

    # 评测可能等待 Docker 数十秒。先结束本次读事务，避免在等待期间持有
    # MySQL 连接、快照或行锁；持久化时再开启新的短事务。
    db.rollback()

    try:
        outcome = await judge_service.evaluate(payload.source_code, specs)
    except judge_service.JudgeSystemError as exc:
        logger.error("judge_system_error problem_id=%d reason=%s", problem_id, exc)
        outcome = judge_service.JudgeOutcome(
            status=SubmissionStatus.SYSTEM_ERROR.value,
            passed_cases=0,
            total_cases=len(specs),
            execution_time_ms=0,
            compile_message=f"评测系统内部错误：{exc}"[:4096],
        )

    diagnosis = diagnosis_service.diagnose(outcome, knowledge_points, problem_title)
    error_category = diagnosis.category if diagnosis else "NONE"

    submission = Submission(
        student_id=payload.student_id,
        problem_id=problem_id,
        source_code=payload.source_code,
        language=payload.language,
        status=outcome.status,
        error_category=error_category,
        passed_cases=outcome.passed_cases,
        total_cases=outcome.total_cases,
        execution_time_ms=outcome.execution_time_ms,
        diagnosis_knowledge_point=diagnosis.knowledge_point if diagnosis else "",
        diagnosis_evidence=diagnosis.evidence if diagnosis else "",
        diagnosis_source=diagnosis.source if diagnosis else "RULE",
        diagnosis_confidence=diagnosis.confidence if diagnosis else "UNDETERMINED",
        diagnosis_json=asdict(diagnosis) if diagnosis else None,
        error_message=outcome.compile_message[:4096],
    )

    try:
        submission_repo.add(db, submission)
        submission_repo.add_details(db, _build_details(submission.id, outcome))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("submission_persist_failed problem_id=%d", problem_id)
        raise

    logger.info(
        "submission_evaluated submission_id=%s status=%s passed=%d/%d elapsed_ms=%d",
        submission.id,
        outcome.status,
        outcome.passed_cases,
        outcome.total_cases,
        outcome.execution_time_ms,
    )

    return SubmissionResultOut(
        submission_id=submission.id,
        problem_id=problem_id,
        status=outcome.status,
        passed_cases=outcome.passed_cases,
        total_cases=outcome.total_cases,
        execution_time_ms=outcome.execution_time_ms,
        diagnosis=DiagnosisOut(**asdict(diagnosis)) if diagnosis else None,
        message=outcome.compile_message,
        cases=_build_case_results(outcome),
    )


class SubmissionNotFoundError(LookupError):
    pass


def get_submission_result(db: Session, submission_id: str) -> SubmissionResultOut:
    submission = submission_repo.get(db, submission_id)
    if submission is None:
        raise SubmissionNotFoundError(submission_id)

    cases = problem_repo.get_cases_by_ids(
        db, [detail.test_case_id for detail in submission.details]
    )
    case_results = []
    ordered = sorted(
        submission.details,
        key=lambda detail: (
            cases[detail.test_case_id].order_index if detail.test_case_id in cases else 0,
            detail.id,
        ),
    )
    for index, detail in enumerate(ordered):
        test_case = cases.get(detail.test_case_id)
        is_public = bool(test_case and test_case.is_public)
        case_results.append(
            CaseResultOut(
                case_index=index + 1,
                is_public=is_public,
                status=detail.status,
                execution_time_ms=detail.execution_time_ms,
                expected_output=detail.expected_output if is_public else None,
                actual_output=detail.actual_output if is_public else None,
                error_message=detail.error_message[:500] or None,
            )
        )

    diagnosis = None
    if submission.error_category != "NONE":
        payload = submission.diagnosis_json or {}
        diagnosis = DiagnosisOut(
            category=submission.error_category,
            knowledge_point=submission.diagnosis_knowledge_point,
            evidence=submission.diagnosis_evidence,
            source=submission.diagnosis_source,
            confidence=submission.diagnosis_confidence,
            possible_cause=str(payload.get("possible_cause", "")),
            certainty=str(payload.get("certainty", "")),
        )

    return SubmissionResultOut(
        submission_id=submission.id,
        problem_id=submission.problem_id,
        status=submission.status,
        passed_cases=submission.passed_cases,
        total_cases=submission.total_cases,
        execution_time_ms=submission.execution_time_ms,
        diagnosis=diagnosis,
        message=submission.error_message,
        cases=case_results,
    )
