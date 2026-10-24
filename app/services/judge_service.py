"""评测编排服务。

职责：组装作业 → 调用受限容器 → 解析结果 → 汇总状态。
安全红线：
- 学生代码只在 Docker 受限容器中编译执行，Docker 不可用时明确报错，绝不回退宿主执行。
- 宿主侧命令以参数列表传入，不使用 shell 字符串拼接。
- 无论成功失败，都强制清理本次容器。
"""

import asyncio
import json
import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.enums import SubmissionStatus

logger = logging.getLogger(__name__)

# 失败状态优先级：越靠前越能解释失败原因
_STATUS_PRIORITY = [
    SubmissionStatus.SYSTEM_ERROR,
    SubmissionStatus.RESOURCE_LIMIT_EXCEEDED,
    SubmissionStatus.TIME_LIMIT_EXCEEDED,
    SubmissionStatus.RUNTIME_ERROR,
    SubmissionStatus.WRONG_ANSWER,
]


class JudgeUnavailableError(RuntimeError):
    """评测环境不可用（Docker 未启动或镜像缺失）。"""


class JudgeSystemError(RuntimeError):
    """评测过程发生内部异常。"""


@dataclass
class CaseSpec:
    index: int
    test_case_id: int
    input_data: str
    expected_output: str
    is_public: bool


@dataclass
class CaseOutcome:
    index: int
    test_case_id: int
    is_public: bool
    status: str
    time_ms: int
    actual_output: str = ""
    expected_output: str = ""
    error_message: str = ""
    truncated: bool = False


@dataclass
class JudgeOutcome:
    status: str
    passed_cases: int
    total_cases: int
    execution_time_ms: int
    compile_message: str = ""
    cases: list[CaseOutcome] = field(default_factory=list)


_semaphore: asyncio.Semaphore | None = None
_docker_state = {"checked_at": 0.0, "available": False, "image": False}
_DOCKER_CACHE_SECONDS = 10.0


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.judge_max_concurrency)
    return _semaphore


def _check_docker(force: bool = False) -> tuple[bool, bool]:
    """返回 (守护进程可用, 镜像存在)。结果缓存 10 秒，避免每次提交都做探活。"""
    now = time.monotonic()
    if not force and now - _docker_state["checked_at"] < _DOCKER_CACHE_SECONDS:
        return bool(_docker_state["available"]), bool(_docker_state["image"])

    available = False
    image_ready = False
    try:
        info = subprocess.run(
            [settings.judge_docker_bin, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        available = info.returncode == 0
        if available:
            inspect = subprocess.run(
                [settings.judge_docker_bin, "image", "inspect", settings.judge_image],
                capture_output=True,
                text=True,
                timeout=5,
            )
            image_ready = inspect.returncode == 0
    except (OSError, subprocess.SubprocessError):
        available = False
        image_ready = False

    _docker_state.update(
        {"checked_at": now, "available": available, "image": image_ready}
    )
    return available, image_ready


def docker_status() -> bool:
    available, image_ready = _check_docker()
    return available and image_ready


def cleanup_stale_containers() -> None:
    """启动时清理上次异常退出遗留的评测容器。"""
    try:
        listing = subprocess.run(
            [settings.judge_docker_bin, "ps", "-aq", "--filter", "name=judge-"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if listing.returncode != 0:
            return
        container_ids = listing.stdout.split()
        if not container_ids:
            return
        subprocess.run(
            [settings.judge_docker_bin, "rm", "-f", *container_ids],
            capture_output=True,
            timeout=15,
        )
        logger.warning("stale_containers_removed count=%d", len(container_ids))
    except (OSError, subprocess.SubprocessError):
        logger.warning("stale_container_cleanup_failed")


def _remove_container(name: str) -> None:
    try:
        subprocess.run(
            [settings.judge_docker_bin, "rm", "-f", name],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        logger.warning("container_cleanup_failed name=%s", name)


def build_container_args(name: str) -> list[str]:
    """构建容器启动参数。所有限制均为固定安全边界，不接受调用方覆盖。"""
    return [
        settings.judge_docker_bin,
        "run",
        "--rm",
        "-i",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "256m",
        "--cpus",
        "0.5",
        "--user",
        "65534:65534",
        "--tmpfs",
        "/work:rw,nosuid,nodev,exec,size=32m,mode=1777",
        "--ulimit",
        "cpu=10",
        "--log-driver",
        "none",
        settings.judge_image,
    ]


def _run_container(source_code: str, cases: list[CaseSpec]) -> dict:
    name = f"judge-{uuid.uuid4().hex[:12]}"
    payload = json.dumps(
        {
            "source_code": source_code,
            "cases": [
                {
                    "input": case.input_data,
                    "expected": case.expected_output,
                    "time_limit_ms": settings.judge_case_timeout_ms,
                }
                for case in cases
            ],
        },
        ensure_ascii=False,
    )
    args = build_container_args(name)
    try:
        proc = subprocess.run(
            args,
            input=payload.encode("utf-8"),
            capture_output=True,
            timeout=settings.judge_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        _remove_container(name)
        raise JudgeSystemError("评测整体执行超时，容器已强制清理") from exc
    except OSError as exc:
        raise JudgeUnavailableError(f"无法调用 Docker：{exc}") from exc
    finally:
        _remove_container(name)

    stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
    if proc.returncode == 137:
        return {"container_killed": True, "stderr": stderr}
    if proc.returncode != 0:
        raise JudgeSystemError(
            f"评测容器异常退出，退出码 {proc.returncode}：{stderr}"
        )

    try:
        return json.loads(proc.stdout.decode("utf-8", errors="replace"))
    except ValueError as exc:
        raise JudgeSystemError("评测容器返回内容无法解析") from exc


def _aggregate_status(cases: list[CaseOutcome]) -> str:
    if not cases:
        return SubmissionStatus.SYSTEM_ERROR.value
    if all(case.status == SubmissionStatus.ACCEPTED for case in cases):
        return SubmissionStatus.ACCEPTED.value
    failed = {case.status for case in cases if case.status != SubmissionStatus.ACCEPTED}
    for candidate in _STATUS_PRIORITY:
        if candidate.value in failed:
            return candidate.value
    return SubmissionStatus.WRONG_ANSWER.value


async def evaluate(source_code: str, cases: list[CaseSpec]) -> JudgeOutcome:
    if not cases:
        raise JudgeSystemError("题目没有可执行的测试用例")

    # 探活会调用 docker CLI，放到线程池，避免阻塞事件循环。
    available, image_ready = await asyncio.to_thread(_check_docker)
    if not available:
        raise JudgeUnavailableError("评测服务不可用：Docker 守护进程未运行")
    if not image_ready:
        raise JudgeUnavailableError(
            f"评测服务不可用：未找到评测镜像 {settings.judge_image}"
        )

    started = time.perf_counter()
    async with _get_semaphore():
        raw = await asyncio.to_thread(_run_container, source_code, cases)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    if raw.get("container_killed"):
        logger.warning("judge_container_killed total_cases=%d", len(cases))
        return JudgeOutcome(
            status=SubmissionStatus.RESOURCE_LIMIT_EXCEEDED.value,
            passed_cases=0,
            total_cases=len(cases),
            execution_time_ms=elapsed_ms,
            compile_message="评测容器被资源限制终止",
        )

    compile_info = raw.get("compile") or {}
    if not compile_info.get("ok"):
        message = str(compile_info.get("message") or "编译失败")[:4096]
        return JudgeOutcome(
            status=SubmissionStatus.COMPILATION_ERROR.value,
            passed_cases=0,
            total_cases=len(cases),
            execution_time_ms=elapsed_ms,
            compile_message=message,
        )

    raw_cases = raw.get("cases") or []
    by_index = {int(item.get("index", -1)): item for item in raw_cases}
    outcomes: list[CaseOutcome] = []
    for case in cases:
        item = by_index.get(case.index, {})
        outcomes.append(
            CaseOutcome(
                index=case.index,
                test_case_id=case.test_case_id,
                is_public=case.is_public,
                status=str(item.get("status") or SubmissionStatus.SYSTEM_ERROR),
                time_ms=int(item.get("time_ms") or 0),
                actual_output=str(item.get("output") or "")[: settings.judge_max_output_bytes],
                expected_output=case.expected_output,
                error_message=str(item.get("error") or "")[:1024],
                truncated=bool(item.get("truncated")),
            )
        )

    passed = sum(1 for case in outcomes if case.status == SubmissionStatus.ACCEPTED)
    return JudgeOutcome(
        status=_aggregate_status(outcomes),
        passed_cases=passed,
        total_cases=len(cases),
        execution_time_ms=elapsed_ms,
        cases=outcomes,
    )

