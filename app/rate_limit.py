"""Thread-safe, single-process fixed-window limits for configured API principals."""
from __future__ import annotations

from collections import OrderedDict
from math import ceil
from threading import Lock
from time import monotonic


class PrincipalRateLimiter:
    """Bounded fixed-window counter; suitable only while the API has one replica."""

    def __init__(self, window_seconds: int = 60, max_principals: int = 1024) -> None:
        if window_seconds < 1 or max_principals < 1:
            raise ValueError("Rate limiter bounds must be positive.")
        self.window_seconds = window_seconds
        self.max_principals = max_principals
        self._entries: OrderedDict[str, tuple[float, int]] = OrderedDict()
        self._lock = Lock()

    def check(self, principal_key: str, limit: int) -> tuple[bool, int, int]:
        if not principal_key or limit < 1:
            raise ValueError("Principal key and request limit must be valid.")
        now = monotonic()
        with self._lock:
            started, count = self._entries.get(principal_key, (now, 0))
            if now - started >= self.window_seconds:
                started, count = now, 0

            if count >= limit:
                retry_after = max(1, ceil(self.window_seconds - (now - started)))
                self._entries[principal_key] = (started, count)
                self._entries.move_to_end(principal_key)
                return False, retry_after, 0

            count += 1
            self._entries[principal_key] = (started, count)
            self._entries.move_to_end(principal_key)
            while len(self._entries) > self.max_principals:
                self._entries.popitem(last=False)
            return True, 0, max(0, limit - count)
