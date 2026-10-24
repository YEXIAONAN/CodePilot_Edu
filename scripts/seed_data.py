"""写入 P0 演示题目与测试用例（幂等，不清空已有提交记录）。

预期输出均经过手算与参考实现双重核对，详见 docs/TEST_REPORT.md。
重复执行时：已存在的题目与其用例保持不变；仅补缺失的题目或用例。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.exc import OperationalError  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Problem, TestCase  # noqa: E402

PROBLEMS = [
    {
        "id": 1,
        "title": "1 到 N 求和",
        "description": "给定一个正整数 N，计算 1 + 2 + ... + N 的结果并输出。",
        "difficulty": "EASY",
        "knowledge_points": ["循环结构", "循环边界", "累加求和"],
        "input_description": "一行一个正整数 N（1 ≤ N ≤ 10000）。",
        "output_description": "输出一个整数，表示 1 到 N 的累加和。",
        "sample_input": "5\n",
        "sample_output": "15\n",
        "cases": [
            ("5\n", "15\n", True, 0),
            ("1\n", "1\n", True, 1),
            ("100\n", "5050\n", False, 2),
            ("10\n", "55\n", False, 3),
        ],
    },
    {
        "id": 2,
        "title": "成绩等级判定",
        "description": (
            "根据输入的百分制成绩输出对应等级："
            "90~100 为 A，80~89 为 B，70~79 为 C，60~69 为 D，低于 60 为 F。"
        ),
        "difficulty": "EASY",
        "knowledge_points": ["条件判断", "分支结构", "边界值处理"],
        "input_description": "一行一个整数 score（0 ≤ score ≤ 100）。",
        "output_description": "输出一个大写字母表示的等级。",
        "sample_input": "85\n",
        "sample_output": "B\n",
        "cases": [
            ("85\n", "B\n", True, 0),
            ("60\n", "D\n", True, 1),
            ("59\n", "F\n", False, 2),
            ("90\n", "A\n", False, 3),
            ("100\n", "A\n", False, 4),
        ],
    },
    {
        "id": 3,
        "title": "偶数累加",
        "description": (
            "给定正整数 N，计算 1 到 N（含 N）之间所有偶数的和并输出。"
            "若区间内没有偶数，输出 0。"
        ),
        "difficulty": "EASY",
        "knowledge_points": ["循环结构", "条件判断", "累加求和"],
        "input_description": "一行一个正整数 N（1 ≤ N ≤ 1000）。",
        "output_description": "输出一个整数，表示区间内所有偶数之和。",
        "sample_input": "5\n",
        "sample_output": "6\n",
        "cases": [
            ("5\n", "6\n", True, 0),
            ("1\n", "0\n", True, 1),
            ("10\n", "30\n", False, 2),
            ("100\n", "2550\n", False, 3),
        ],
    },
]


def _cases_for(spec: dict) -> list[TestCase]:
    return [
        TestCase(
            input_data=input_data,
            expected_output=expected,
            is_public=is_public,
            order_index=order,
        )
        for input_data, expected, is_public, order in spec["cases"]
    ]


def seed() -> None:
    db = SessionLocal()
    try:
        created_problems = 0
        created_cases = 0
        for spec in PROBLEMS:
            problem = db.get(Problem, spec["id"])
            if problem is not None and problem.test_cases:
                print(f"skip problem {spec['id']}（已存在且有用例）")
                continue
            if problem is None:
                problem = Problem(
                    id=spec["id"],
                    title=spec["title"],
                    description=spec["description"],
                    difficulty=spec["difficulty"],
                    knowledge_points=spec["knowledge_points"],
                    input_description=spec["input_description"],
                    output_description=spec["output_description"],
                    sample_input=spec["sample_input"],
                    sample_output=spec["sample_output"],
                )
                db.add(problem)
                created_problems += 1
            else:
                print(f"problem {spec['id']} 已存在但缺少用例，补齐用例")
            new_cases = _cases_for(spec)
            problem.test_cases.extend(new_cases)
            created_cases += len(new_cases)
        db.commit()
        print(
            f"seed 完成：新增题目 {created_problems} 道，新增用例 {created_cases} 个；"
            "已有提交记录未改动"
        )
    except OperationalError as exc:
        db.rollback()
        print(
            "数据库表不存在或数据库不可用，请先运行 scripts/init_db.py",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
