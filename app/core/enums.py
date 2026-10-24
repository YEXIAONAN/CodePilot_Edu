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
    # 扩展状态：Docker 不可用时明确报错，禁止回退宿主执行
    JUDGE_UNAVAILABLE = "JUDGE_UNAVAILABLE"


class DiagnosisCategory(StrEnum):
    SYNTAX_ERROR = "SYNTAX_ERROR"
    LOOP_BOUNDARY_ERROR = "LOOP_BOUNDARY_ERROR"
    CONDITION_ERROR = "CONDITION_ERROR"
    VARIABLE_ERROR = "VARIABLE_ERROR"
    OUTPUT_MISMATCH = "OUTPUT_MISMATCH"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class DiagnosisSource(StrEnum):
    RULE = "RULE"
    AI = "AI"
    HUMAN = "HUMAN"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNDETERMINED = "UNDETERMINED"


class HintSource(StrEnum):
    RULE = "RULE"
    AI = "AI"
