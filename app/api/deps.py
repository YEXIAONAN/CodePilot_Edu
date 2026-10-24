"""演示访问令牌与提交频率限制。

P0 仅用于受信任的本地演示环境，不构成正式身份认证。
"""

import hmac
import time
from collections import defaultdict, deque

from fastapi import Header

from app.core.config import settings
from app.core.errors import ApiError

_SUBMIT_WINDOW_SECONDS = 60
_SUBMIT_LIMIT = 10
_submit_history: dict[str, deque[float]] = defaultdict(deque)


async def require_demo_token(x_demo_token: str | None = Header(default=None)) -> None:
    if not settings.demo_token:
        # 配置缺失时失败关闭，避免误以为接口已受令牌保护。
        raise ApiError(
            "DEMO_TOKEN_NOT_CONFIGURED",
            "服务端未配置 DEMO_TOKEN，已拒绝访问",
            status_code=503,
        )
    if not x_demo_token or not hmac.compare_digest(x_demo_token, settings.demo_token):
        raise ApiError("UNAUTHORIZED", "缺少或错误的演示访问令牌", status_code=401)


def enforce_submit_rate_limit(student_id: str) -> None:
    now = time.monotonic()
    history = _submit_history[student_id]
    while history and now - history[0] > _SUBMIT_WINDOW_SECONDS:
        history.popleft()
    if len(history) >= _SUBMIT_LIMIT:
        raise ApiError(
            "RATE_LIMITED",
            f"提交过于频繁，每分钟最多 {_SUBMIT_LIMIT} 次",
            status_code=429,
        )
    history.append(now)
