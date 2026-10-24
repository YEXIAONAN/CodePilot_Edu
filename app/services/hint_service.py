"""分层提示服务：保证层级递进、结果稳定、AI 故障可降级。"""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.enums import DiagnosisCategory, HintSource, SubmissionStatus
from app.models import HintRecord
from app.repositories import hint_repo, problem_repo, submission_repo
from app.schemas.hint import HintOut
from app.services import ai_service

logger = logging.getLogger(__name__)


class HintNotFoundError(LookupError):
    pass


class HintNotAvailableError(RuntimeError):
    pass


class HintLevelError(ValueError):
    def __init__(self, message: str, next_level: int | None = None) -> None:
        super().__init__(message)
        self.next_level = next_level


@dataclass(frozen=True)
class _SubmissionSnapshot:
    """在结束数据库事务前复制出的纯数据，供 AI 调用期间使用。"""

    id: str
    problem_id: int
    status: str
    source_code: str
    error_category: str
    diagnosis_knowledge_point: str
    diagnosis_evidence: str


_RULE_HINTS: dict[str, list[str]] = {
    DiagnosisCategory.SYNTAX_ERROR.value: [
        "这道题目前卡在编译阶段。请先关注 C 语言的语法规则，而不是程序逻辑。",
        "编译器报告的第一处错误通常就是根因：检查报错行及其上一行，重点看语句结尾的分号、括号是否成对、变量是否先声明后使用。",
        "从第一条错误开始逐条修复，每改一处就重新编译一次，不要同时改动多处。语法通过后再回到题目逻辑验证输出。",
    ],
    DiagnosisCategory.VARIABLE_ERROR.value: [
        "重点检查变量的使用方式：初始化、取值范围以及运算是否合法。",
        "找到参与除法或数组下标的变量，确认除数不为 0、下标没有越过数组范围，并检查变量是否在使用前完成初始化。",
        "沿程序执行顺序列出相关变量在每一步的值，确认它在被使用时不处于未定义或越界状态。调试时可先打印中间值验证。",
    ],
    DiagnosisCategory.OUTPUT_MISMATCH.value: [
        "评测已确认输出与预期不符。先明确题目要求的输出格式与计算目标，再定位是哪一类逻辑导致的偏差。",
        "对照失败用例的输入，检查循环变量的初值与终止条件、累加器是否在循环前正确初始化，以及是否存在多算或少算一次的情况。",
        "用题目中最小的输入手动推演：写下每轮循环开始时各变量的值，比较最终结果。如果只差一个值，通常问题在边界条件（< 与 <=）；如果整体偏差，检查累加或条件判断是否覆盖了全部情况。请自己完成推演，不要直接抄标准答案。",
    ],
    DiagnosisCategory.CONDITION_ERROR.value: [
        "重点检查条件判断结构：分支条件是否覆盖了题目要求的全部情况。",
        "检查 if/else 分支的边界值（例如临界分数、等于号与不等号），确认每个区间都落到正确的分支，且没有遗漏的情况。",
        "把题目中的每种情况列成表格，逐个代入条件表达式，判断实际会走哪个分支，再与预期对照。注意区间端点应归入哪一侧。",
    ],
    DiagnosisCategory.LOOP_BOUNDARY_ERROR.value: [
        "重点检查循环边界：循环变量的初值、循环条件和每轮更新方式。",
        "对照题目输入范围，检查循环条件中的边界值，以及循环体是否多执行或少执行了一次。",
        "用最小输入手动模拟循环过程，记录每轮变量的值，确认循环次数与题目要求一致。",
    ],
    DiagnosisCategory.UNKNOWN_ERROR.value: [
        "当前证据只能确认程序未通过评测，还不足以判断具体错因。先从题目要求和程序整体结构入手排查。",
        "建议按顺序核对：输入读取方式是否与题目一致、循环与条件是否符合题意、输出格式是否完全匹配（空格与换行也会影响判定）。",
        "缩小范围的方法：先用题目给的示例输入手动运行程序，确认输出；再把中间变量打印出来，与手算结果逐步比对，定位第一次出现分歧的位置。",
    ],
}


def _loop_focused_hints() -> list[str]:
    return [
        "这道题的核心是循环结构。请重点检查循环变量、循环条件和每轮的更新方式。",
        "对照题目输入范围，检查循环条件里的边界值（例如 N=1 时循环体执行几次），并确认累加变量在循环开始前已正确初始化。",
        "用题目中最小的输入手动推演一遍：记录每轮循环开始时各变量的值，比较最终结果与预期。如果只差一次，问题通常在 < 与 <= 的边界；如果累计值不对，检查是否漏加或多加了某个值。",
    ]


def _condition_focused_hints() -> list[str]:
    return _RULE_HINTS[DiagnosisCategory.CONDITION_ERROR.value]


def _pick_rule_hints(category: str, knowledge_point: str) -> list[str]:
    if any("循环" in point for point in (knowledge_point,)) and category == DiagnosisCategory.OUTPUT_MISMATCH.value:
        return _loop_focused_hints()
    if "条件" in knowledge_point and category == DiagnosisCategory.OUTPUT_MISMATCH.value:
        return _condition_focused_hints()
    return _RULE_HINTS.get(category, _RULE_HINTS[DiagnosisCategory.UNKNOWN_ERROR.value])


def _to_out(record: HintRecord, knowledge_point: str) -> HintOut:
    return HintOut(
        submission_id=record.submission_id,
        level=record.hint_level,
        source=record.source,
        knowledge_point=knowledge_point,
        hint=record.hint_content,
        is_fallback=record.is_fallback,
    )


async def request_hint(db: Session, submission_id: str, level: int) -> HintOut:
    submission = submission_repo.get(db, submission_id)
    if submission is None:
        raise HintNotFoundError(submission_id)
    if submission.status == SubmissionStatus.ACCEPTED:
        raise HintNotAvailableError("该提交已通过评测，无需纠错提示")
    if submission.status == SubmissionStatus.SYSTEM_ERROR:
        raise HintNotAvailableError("该提交为系统故障，未生成学习诊断，请重新提交")

    snapshot = _SubmissionSnapshot(
        id=submission.id,
        problem_id=submission.problem_id,
        status=submission.status,
        source_code=submission.source_code,
        error_category=submission.error_category,
        diagnosis_knowledge_point=submission.diagnosis_knowledge_point,
        diagnosis_evidence=submission.diagnosis_evidence,
    )

    existing = hint_repo.list_for_submission(db, submission_id)
    existing_by_level = {record.hint_level: record for record in existing}
    # 只有“已解锁”的层级才算已获取。AI 预生成的第 2/3 层先以未解锁状态入库，
    # 防止客户端在拿到第 1 层后直接读取第 3 层。
    max_unlocked = max(
        (record.hint_level for record in existing if record.is_unlocked), default=0
    )

    if level <= max_unlocked:
        record = existing_by_level.get(level)
        if record is not None:
            return _to_out(record, snapshot.diagnosis_knowledge_point)

    if level != max_unlocked + 1:
        raise HintLevelError(
            f"提示必须按层级依次获取，下一次可请求第 {max_unlocked + 1} 层",
            next_level=max_unlocked + 1 if max_unlocked < 3 else None,
        )

    problem = problem_repo.get_problem(db, snapshot.problem_id)
    problem_title = problem.title if problem is not None else ""
    problem_description = problem.description if problem is not None else ""
    knowledge_points = list(problem.knowledge_points) if problem is not None else []

    # AI 调用与后续写入之间不持有数据库事务/行锁。
    db.rollback()

    # 首次请求：允许 AI 一次生成三层，但第 2/3 层先存为未解锁。
    if level == 1 and not existing and problem is not None:
        ai_hints = await ai_service.generate_three_levels(
            problem_title=problem_title,
            problem_description=problem_description,
            knowledge_points=knowledge_points,
            source_code=snapshot.source_code,
            status=snapshot.status,
            evidence=snapshot.diagnosis_evidence,
        )
        if ai_hints:
            hint_repo.upsert_levels(
                db,
                submission_id,
                [
                    {
                        "hint_level": index + 1,
                        "hint_content": content,
                        "source": HintSource.AI.value,
                        "is_fallback": False,
                        "is_unlocked": index == 0,
                    }
                    for index, content in enumerate(ai_hints)
                ],
            )
            db.commit()
            record = hint_repo.get_level(db, submission_id, level)
            if record is not None:
                return _to_out(record, snapshot.diagnosis_knowledge_point)

    # 已有预生成记录但尚未解锁：按顺序解锁并复用原内容，不重复调用模型。
    if level in existing_by_level:
        hint_repo.unlock_level(db, submission_id, level)
        db.commit()
        record = hint_repo.get_level(db, submission_id, level)
        if record is not None:
            return _to_out(record, snapshot.diagnosis_knowledge_point)

    # AI 未配置 / 调用失败 / 输出不合法：降级为规则提示，并如实标记来源。
    rule_hints = _pick_rule_hints(
        snapshot.error_category, snapshot.diagnosis_knowledge_point
    )
    hint_repo.upsert_levels(
        db,
        submission_id,
        [
            {
                "hint_level": level,
                "hint_content": rule_hints[level - 1],
                "source": HintSource.RULE.value,
                "is_fallback": True,
                "is_unlocked": True,
            }
        ],
    )
    db.commit()
    record = hint_repo.get_level(db, submission_id, level)
    if record is None:
        raise RuntimeError("提示记录写入后未能回读")
    logger.info("hint_fallback submission_id=%s level=%d", submission_id, level)
    return _to_out(record, snapshot.diagnosis_knowledge_point)
