"""枚举常量：评测状态、错因类别、诊断来源与置信度。"""

from enum import StrEnum


class SubmissionStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    WRONG_ANSWER = "WRONG_ANSWER"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    # Docker 不可用不产生提交记录，只以 503 JUDGE_UNAVAILABLE 错误码返回，
    # 因此这里不设 JUDGE_UNAVAILABLE 状态。


class DiagnosisCategory(StrEnum):
    SYNTAX_ERROR = "SYNTAX_ERROR"
    LOOP_BOUNDARY_ERROR = "LOOP_BOUNDARY_ERROR"
    CONDITION_ERROR = "CONDITION_ERROR"
    VARIABLE_ERROR = "VARIABLE_ERROR"
    OUTPUT_MISMATCH = "OUTPUT_MISMATCH"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class DiagnosisSource(StrEnum):
    # TEACHER 只允许真实教师复核时人工写入，P0 没有该入口，故不预留枚举值
    RULE = "RULE"
    AI = "AI"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNDETERMINED = "UNDETERMINED"


class HintSource(StrEnum):
    RULE = "RULE"
    AI = "AI"
