"""题目查询接口。"""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api.deps import require_demo_token
from app.core.errors import ApiError
from app.db.session import get_db
from app.repositories import problem_repo
from app.schemas.problem import ProblemDetail, ProblemListItem, PublicCase

router = APIRouter(
    prefix="/problems",
    tags=["problems"],
    dependencies=[Depends(require_demo_token)],
)


@router.get("", response_model=list[ProblemListItem])
def list_problems(db: Session = Depends(get_db)) -> list[ProblemListItem]:
    problems = problem_repo.list_problems(db)
    return [
        ProblemListItem(
            id=item.id,
            title=item.title,
            difficulty=item.difficulty,
            knowledge_points=list(item.knowledge_points),
        )
        for item in problems
    ]


@router.get("/{problem_id}", response_model=ProblemDetail)
def get_problem(
    problem_id: int = Path(gt=0), db: Session = Depends(get_db)
) -> ProblemDetail:
    problem = problem_repo.get_problem(db, problem_id)
    if problem is None:
        raise ApiError("PROBLEM_NOT_FOUND", f"题目 {problem_id} 不存在", status_code=404)

    public_cases = [
        PublicCase(input_data=case.input_data, expected_output=case.expected_output)
        for case in problem.test_cases
        if case.is_public
    ]
    return ProblemDetail(
        id=problem.id,
        title=problem.title,
        description=problem.description,
        difficulty=problem.difficulty,
        knowledge_points=list(problem.knowledge_points),
        input_description=problem.input_description,
        output_description=problem.output_description,
        sample_input=problem.sample_input,
        sample_output=problem.sample_output,
        public_cases=public_cases,
    )
