"""题目与测试用例的数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Problem, TestCase


def list_problems(db: Session) -> list[Problem]:
    return list(db.scalars(select(Problem).order_by(Problem.id)))


def get_problem(db: Session, problem_id: int) -> Problem | None:
    return db.get(Problem, problem_id)


def list_test_cases(db: Session, problem_id: int) -> list[TestCase]:
    statement = (
        select(TestCase)
        .where(TestCase.problem_id == problem_id)
        .order_by(TestCase.order_index, TestCase.id)
    )
    return list(db.scalars(statement))


def get_cases_by_ids(db: Session, case_ids: list[int]) -> dict[int, TestCase]:
    if not case_ids:
        return {}
    statement = select(TestCase).where(TestCase.id.in_(case_ids))
    return {case.id: case for case in db.scalars(statement)}
