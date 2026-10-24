"""学生学习进度与教师统计响应模型。"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.submission import SubmissionListItem


class ProblemProgress(BaseModel):
    problem_id: int
    title: str
    submissions: int
    accepted: int


class HintUsage(BaseModel):
    level_1: int = 0
    level_2: int = 0
    level_3: int = 0
    fallback_count: int = 0


class StudentProgressOut(BaseModel):
    student_id: str
    total_submissions: int
    accepted_count: int
    error_category_distribution: dict[str, int]
    per_problem: list[ProblemProgress]
    hint_usage: HintUsage
    recent_submissions: list[SubmissionListItem]


class ProblemOverview(BaseModel):
    problem_id: int
    title: str
    submissions: int
    accepted: int
    unique_students: int


class KnowledgePointError(BaseModel):
    knowledge_point: str
    count: int


class PendingTutoringItem(BaseModel):
    student_id: str
    problem_id: int
    problem_title: str
    last_submission_id: str
    last_status: str
    submission_count: int
    failure_count: int
    max_hint_level: int
    last_submitted_at: datetime


class TeacherOverviewOut(BaseModel):
    total_submissions: int
    distinct_students: int
    accepted_submissions: int
    per_problem: list[ProblemOverview]
    error_distribution: dict[str, int]
    knowledge_point_errors: list[KnowledgePointError]
    completed_problem_count: int
    hint_usage: HintUsage
    # 系统故障单独计数，不混入学生错因分布
    system_error_count: int = 0
    pending_tutoring: list[PendingTutoringItem] = []
    pending_tutoring_rule: str = (
        "同一学生同一题至少 3 次学生代码失败且最近一次仍未通过，"
        "或已解锁第 3 层提示且最近一次仍未通过；最近一次通过即移出；"
        "SYSTEM_ERROR 不计入学生失败。列表仅建议教师查看，不代表能力判断。"
    )
    generated_at: datetime
