"""容器内评测执行器。

输入：stdin 上的 JSON 作业
    {"source_code": "...", "cases": [{"input": "...", "expected": "...", "time_limit_ms": 2000}]}
输出：stdout 上的 JSON 结果
    {"compile": {"ok": bool, "message": "..."}, "cases": [{"index": 0, "status": "...", ...}]}

安全约束由 docker 启动参数提供（无网络、只读根文件系统、非 root、资源上限）；
本脚本额外用 rlimit 限制单个学生进程的输出文件大小、CPU 时间与 core dump。
"""

import json
import os
import resource
import subprocess
import sys
import time

WORK_DIR = "/work"
SOURCE_PATH = os.path.join(WORK_DIR, "main.c")
BINARY_PATH = os.path.join(WORK_DIR, "main")
OUTPUT_FILE_LIMIT = 1024 * 1024  # 学生程序 stdout 落盘上限，超过即判定资源超限
MAX_OUTPUT_BYTES = 4096  # 回传给后端的输出最大字节数
COMPILE_TIMEOUT_S = 10
COMPILE_MESSAGE_LIMIT = 4096


def _apply_child_limits(cpu_seconds: int):
    def _apply() -> None:
        resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_FILE_LIMIT, OUTPUT_FILE_LIMIT))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))

    return _apply


def normalize_output(text: str) -> str:
    """逐行去掉行尾空白，并忽略文末多余空行。"""
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def sanitize_compile_message(message: str) -> str:
    cleaned = message.replace(WORK_DIR + "/", "").replace(WORK_DIR, "")
    return cleaned[:COMPILE_MESSAGE_LIMIT]


def read_limited(path: str) -> tuple[str, bool]:
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_OUTPUT_BYTES + 1)
    except OSError:
        return "", False
    truncated = len(data) > MAX_OUTPUT_BYTES
    return data[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), truncated


def main() -> int:
    raw = sys.stdin.read()
    try:
        spec = json.loads(raw)
        source_code = spec["source_code"]
        cases = spec["cases"]
    except (ValueError, KeyError, TypeError):
        print(json.dumps({"compile": {"ok": False, "message": "invalid job spec"}, "cases": []}))
        return 0

    os.makedirs(WORK_DIR, exist_ok=True)
    with open(SOURCE_PATH, "w", encoding="utf-8") as handle:
        handle.write(source_code)

    try:
        compile_proc = subprocess.run(
            [
                "gcc",
                "-O1",
                "-std=c11",
                "-fmax-errors=10",
                "-o",
                BINARY_PATH,
                SOURCE_PATH,
                "-lm",
            ],
            capture_output=True,
            text=True,
            timeout=COMPILE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        print(json.dumps({"compile": {"ok": False, "message": "compilation timeout"}, "cases": []}))
        return 0

    if compile_proc.returncode != 0:
        message = sanitize_compile_message(compile_proc.stderr or "compilation failed")
        print(json.dumps({"compile": {"ok": False, "message": message}, "cases": []}))
        return 0

    results = []
    for index, case in enumerate(cases):
        time_limit_ms = int(case.get("time_limit_ms") or 2000)
        stdout_path = os.path.join(WORK_DIR, f"out_{index}.txt")
        stderr_path = os.path.join(WORK_DIR, f"err_{index}.txt")
        started = time.perf_counter()
        timed_out = False
        exit_code = 0
        cpu_seconds = max(1, time_limit_ms // 1000 + 1)

        try:
            with open(stdout_path, "wb") as out_file, open(stderr_path, "wb") as err_file:
                proc = subprocess.run(
                    [BINARY_PATH],
                    input=(case.get("input") or "").encode("utf-8"),
                    stdout=out_file,
                    stderr=err_file,
                    timeout=time_limit_ms / 1000,
                    preexec_fn=_apply_child_limits(cpu_seconds),
                    cwd=WORK_DIR,
                )
                exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
        except OSError as exc:
            results.append(
                {
                    "index": index,
                    "status": "SYSTEM_ERROR",
                    "time_ms": 0,
                    "output": "",
                    "truncated": False,
                    "error": f"runner error: {exc}",
                }
            )
            continue

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        actual, truncated = read_limited(stdout_path)
        output_size = os.path.getsize(stdout_path) if os.path.exists(stdout_path) else 0
        error_output, _ = read_limited(stderr_path)

        if timed_out:
            status = "TIME_LIMIT_EXCEEDED"
        elif output_size >= OUTPUT_FILE_LIMIT:
            status = "RESOURCE_LIMIT_EXCEEDED"
        elif exit_code != 0:
            status = "RUNTIME_ERROR"
            if exit_code < 0:
                error_output = f"进程被信号 {-exit_code} 终止。{error_output}".strip()
        elif normalize_output(actual) == normalize_output(case.get("expected") or ""):
            status = "ACCEPTED"
        else:
            status = "WRONG_ANSWER"

        results.append(
            {
                "index": index,
                "status": status,
                "time_ms": elapsed_ms,
                "output": actual,
                "truncated": truncated,
                "error": error_output,
            }
        )

    print(json.dumps({"compile": {"ok": True, "message": ""}, "cases": results}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
