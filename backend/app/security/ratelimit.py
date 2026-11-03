import time
from collections import defaultdict, deque
from fastapi import Depends, Request
from ..core.config import get_settings
from ..core.errors import AppError

_hits = defaultdict(deque)


def reset():
    _hits.clear()


def limiter(bucket: str, per_min_attr: str):
    def dep(request: Request):
        s = get_settings()
        if not s.rate_limit_enabled:
            return
        limit = getattr(s, per_min_attr)
        ident = request.cookies.get("access_token", "")[-24:] or (request.client.host if request.client else "anon")
        q, now = _hits[(bucket, ident)], time.monotonic()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            raise AppError(429, "rate_limited", "Too many requests. Please slow down.")
        q.append(now)
    return Depends(dep)
