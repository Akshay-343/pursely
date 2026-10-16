"""Small in-memory sliding-window limiter (per process). Enough to blunt guessing on a single-instance deployment."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window_s: int):
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str):
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            raise HTTPException(429, "Too many attempts. Please wait a few minutes and try again.")
        q.append(now)

    def reset(self):
        self.hits.clear()


def client_ip(request: Request) -> str:
    # Behind Caddy/nginx the real address is in X-Forwarded-For; the proxy is the only thing that can set it in our deployment.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


auth_limiter = RateLimiter(limit=20, window_s=300)
