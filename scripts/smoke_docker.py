"""评测环境自检：Docker、镜像、隔离限制、状态判定与资源清理。

用法（先启动 Docker Desktop 并构建镜像）：
    python scripts/smoke_docker.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.services import judge_service  # noqa: E402

CODES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "codes"

CASES = [
    judge_service.CaseSpec(0, 1, "5\n", "15\n", True),
]


def _case(input_data: str, expected: str, is_public: bool = True) -> judge_service.CaseSpec:
    return judge_service.CaseSpec(0, 1, input_data, expected, is_public)


def _source(name: str) -> str:
    return (CODES_DIR / name).read_text(encoding="utf-8")


async def _run() -> int:
    failures = 0

    available, image_ready = judge_service._check_docker(force=True)  # noqa: SLF001
    print(f"[1] Docker 守护进程: {'OK' if available else 'FAIL'}")
    print(f"[2] 评测镜像 {settings.judge_image}: {'OK' if image_ready else 'FAIL'}")
    if not (available and image_ready):
        print("评测环境未就绪，其余检查跳过。")
        return 1

    checks = [
        ("正确程序 → ACCEPTED", "ACCEPTED", _source("problem1_accepted.c"), [CASES[0]]),
        ("语法错误 → COMPILATION_ERROR", "COMPILATION_ERROR", _source("problem1_compile_error.c"), [CASES[0]]),
        ("循环边界错误 → WRONG_ANSWER", "WRONG_ANSWER", _source("problem1_wrong_boundary.c"), [CASES[0]]),
        ("死循环 → TIME_LIMIT_EXCEEDED", "TIME_LIMIT_EXCEEDED", _source("problem1_timeout.c"), [_case("5\n", "15\n")]),
        ("空指针写入 → RUNTIME_ERROR", "RUNTIME_ERROR", _source("problem1_runtime_error.c"), [_case("5\n", "15\n")]),
        ("巨量输出 → RESOURCE_LIMIT_EXCEEDED", "RESOURCE_LIMIT_EXCEEDED", _source("problem1_huge_output.c"), [_case("5\n", "15\n")]),
    ]

    for index, (label, expected, source, cases) in enumerate(checks, start=3):
        try:
            outcome = await judge_service.evaluate(source, cases)
            ok = outcome.status == expected
            if not ok and label.startswith("空指针写入"):
                ok = outcome.status in {"RUNTIME_ERROR", "RESOURCE_LIMIT_EXCEEDED"}
            print(f"[{index}] {label}: {outcome.status} {'OK' if ok else 'FAIL'}")
            failures += 0 if ok else 1
        except Exception as exc:  # noqa: BLE001
            print(f"[{index}] {label}: 异常 {type(exc).__name__}: {exc}")
            failures += 1

    import subprocess

    listing = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "name=judge-"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    residue = listing.stdout.strip()
    print(f"[9] 容器残留检查: {'OK' if not residue else 'FAIL ' + residue}")
    failures += 0 if not residue else 1

    print(f"\n结果：{'全部通过' if failures == 0 else f'{failures} 项失败'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
