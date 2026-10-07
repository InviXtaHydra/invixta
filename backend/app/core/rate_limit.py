"""A small in-memory rate limiter (sliding window).

- Login: at most LOGIN_ATTEMPTS_PER_MINUTE *failed* logins per email address, which makes guessing
  a password very slow without bothering users who type it right.
- Chat: at most CHAT_MESSAGES_PER_MINUTE messages per user, because every message costs LLM tokens.

The counters live in this process's memory. That's enough for a single backend container; with
several replicas you'd keep them in a shared store such as Redis.
"""

import threading
import time
from collections import defaultdict, deque
from functools import lru_cache

from app.core.config import get_settings
from app.core.exceptions import TooManyRequestsError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Raise TooManyRequestsError if `key` already used up its limit in the current window."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, round(hits[0] + self.window - now))
                raise TooManyRequestsError(f"Too many attempts. Try again in {retry_after} seconds.", retry_after=retry_after)

    def record(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def hit(self, key: str) -> None:
        """check() and record() in one go: count this request, refuse it when over the limit."""
        self.check(key)
        self.record(key)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


@lru_cache
def login_limiter() -> RateLimiter:
    return RateLimiter(get_settings().login_attempts_per_minute)


@lru_cache
def chat_limiter() -> RateLimiter:
    return RateLimiter(get_settings().chat_messages_per_minute)
