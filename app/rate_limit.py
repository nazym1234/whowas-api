from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(
        self,
        limit: int = 30,
        window_seconds: int = 60,
        max_clients: int = 10_000,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            if key not in self._requests and len(self._requests) >= self.max_clients:
                self._requests.pop(next(iter(self._requests)))
            history = self._requests[key]
            while history and history[0] <= cutoff:
                history.popleft()
            if len(history) >= self.limit:
                return False
            history.append(now)
            return True
