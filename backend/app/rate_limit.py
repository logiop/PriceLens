from __future__ import annotations

import os
import time
from collections import deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

ENABLED = os.environ.get("PRICELENS_RATE_LIMIT_ENABLED", "1").lower() not in ("0", "false", "no")
DEFAULT_LIMIT = int(os.environ.get("PRICELENS_RATE_LIMIT_PER_MINUTE", "300"))
AUTH_LIMIT = int(os.environ.get("PRICELENS_AUTH_RATE_LIMIT_PER_MINUTE", "10"))
WINDOW_SECONDS = 60


class SlidingWindowLimiter:
    """Tiny in-process sliding-window limiter (per key)."""

    def __init__(self, window: int = WINDOW_SECONDS) -> None:
        self.window = window
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, limit: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window
        bucket = self._hits.setdefault(key, deque())
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry = int(self.window - (now - bucket[0])) + 1
            return False, max(retry, 1)
        bucket.append(now)
        return True, 0


_limiter = SlidingWindowLimiter()

# Paths that must never be rate limited (health checks, static assets).
_EXEMPT_PREFIXES = ("/api/health", "/assets", "/favicon")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not ENABLED or not request.url.path.startswith("/api"):
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        scope = "auth" if request.url.path.startswith("/api/auth") else "api"
        limit = AUTH_LIMIT if scope == "auth" else DEFAULT_LIMIT
        allowed, retry_after = _limiter.allow(f"{scope}:{client}", limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Troppe richieste, riprova più tardi"},
                headers={"Retry-After": str(retry_after)},
            )
        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(limit))
        return response
