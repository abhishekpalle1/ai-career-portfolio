"""In-memory cost controls: per-session and per-IP daily limits, and a bounded TTL answer cache.

State is per process, which matches the single-instance Cloud Run deployment (max instances 1).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from app.models.chat import ChatResponse


@dataclass(frozen=True)
class LimitDecision:
    allowed: bool
    reason: str | None = None
    retry_after_seconds: int = 0


class RateLimiter:
    """Fixed daily window per client IP plus a lifetime-of-window cap per session ID."""

    def __init__(
        self,
        *,
        max_per_session: int,
        max_per_ip_per_day: int,
        max_tracked_keys: int = 10_000,
        clock: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self._max_per_session = max_per_session
        self._max_per_ip = max_per_ip_per_day
        self._max_keys = max_tracked_keys
        self._clock = clock or (lambda: dt.datetime.now(dt.UTC))
        self._lock = threading.Lock()
        self._day: dt.date | None = None
        self._ip_counts: dict[str, int] = {}
        self._session_counts: dict[str, int] = {}

    def check_and_record(self, client_ip: str, session_id: str | None) -> LimitDecision:
        now = self._clock()
        retry_after = int(
            (
                dt.datetime.combine(now.date() + dt.timedelta(days=1), dt.time(), dt.UTC) - now
            ).total_seconds()
        )
        with self._lock:
            if self._day != now.date():
                self._day = now.date()
                self._ip_counts.clear()
                self._session_counts.clear()
            if self._ip_counts.get(client_ip, 0) >= self._max_per_ip:
                return LimitDecision(False, "ip_daily_limit", retry_after)
            if session_id and self._session_counts.get(session_id, 0) >= self._max_per_session:
                return LimitDecision(False, "session_limit", retry_after)
            if len(self._ip_counts) >= self._max_keys and client_ip not in self._ip_counts:
                return LimitDecision(False, "tracking_capacity", retry_after)
            self._ip_counts[client_ip] = self._ip_counts.get(client_ip, 0) + 1
            if session_id and (
                session_id in self._session_counts or len(self._session_counts) < self._max_keys
            ):
                self._session_counts[session_id] = self._session_counts.get(session_id, 0) + 1
            return LimitDecision(True)

    def reset(self) -> None:
        with self._lock:
            self._day = None
            self._ip_counts.clear()
            self._session_counts.clear()


class AnswerCache:
    """Bounded LRU cache with TTL. Only grounded, validated answers are stored."""

    def __init__(
        self, *, ttl_seconds: int, max_entries: int, clock: Callable[[], float] | None = None
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, tuple[float, ChatResponse]] = OrderedDict()

    @staticmethod
    def make_key(question: str, *, versions: tuple[str, ...]) -> str:
        normalized = re.sub(r"[\s?.!]+$", "", re.sub(r"\s+", " ", question).strip().casefold())
        return hashlib.sha256("\x1f".join((normalized, *versions)).encode("utf-8")).hexdigest()

    def get(self, key: str) -> ChatResponse | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            stored_at, response = entry
            if self._clock() - stored_at > self._ttl:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return response

    def put(self, key: str, response: ChatResponse) -> None:
        if self._max <= 0 or self._ttl <= 0:
            return
        with self._lock:
            self._entries[key] = (self._clock(), response)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max:
                self._entries.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
