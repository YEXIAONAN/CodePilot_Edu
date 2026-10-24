"""安全边界单元测试：容器启动参数必须包含全部隔离限制。"""

from app.core.config import settings
from app.services.judge_service import build_container_args


def test_container_args_enforce_isolation() -> None:
    args = build_container_args("judge-test")
    joined = " ".join(args)

    assert "--network" in args and args[args.index("--network") + 1] == "none"
    assert "--read-only" in args
    assert args[args.index("--cap-drop") + 1] == "ALL"
    assert args[args.index("--security-opt") + 1] == "no-new-privileges"
    assert args[args.index("--user") + 1] == "65534:65534"
    assert "--pids-limit" in args
    assert "--memory" in args and args[args.index("--memory") + 1] == "256m"
    assert "--cpus" in args
    assert args[-1] == settings.judge_image

    tmpfs = args[args.index("--tmpfs") + 1]
    assert tmpfs.startswith("/work:rw")
    assert "size=32m" in tmpfs


def test_arguments_are_list_not_shell_string() -> None:
    args = build_container_args("judge-test")
    assert isinstance(args, list)
    assert all(isinstance(item, str) for item in args)
    # 参数列表不应包含 shell 元字符拼接
    assert not any("&&" in item or "|" in item for item in args)
