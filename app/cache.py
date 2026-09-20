from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, max_size: int = 512) -> None:
        self.max_size = max_size
        self._items: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                self._items.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl: float) -> None:
        async with self._lock:
            if len(self._items) >= self.max_size:
                oldest = min(self._items, key=lambda item: self._items[item].expires_at)
                self._items.pop(oldest, None)
            self._items[key] = CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    async def clear(self) -> None:
        async with self._lock:
            self._items.clear()

    @property
    def size(self) -> int:
        return len(self._items)
