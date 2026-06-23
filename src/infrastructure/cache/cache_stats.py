"""Cache statistics tracker — hit/miss metrics for QA cache layer."""

import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class _EntryStats:
    hits: int = 0
    misses: int = 0
    last_access: float = 0.0


class CacheStats:
    """Thread-safe cache statistics tracker."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: Dict[str, _EntryStats] = {}
        self._total_hits: int = 0
        self._total_misses: int = 0
        self._start_time: float = time.time()

    def record_hit(self, key: str) -> None:
        with self._lock:
            self._total_hits += 1
            entry = self._entries.setdefault(key, _EntryStats())
            entry.hits += 1
            entry.last_access = time.time()

    def record_miss(self, key: str) -> None:
        with self._lock:
            self._total_misses += 1
            entry = self._entries.setdefault(key, _EntryStats())
            entry.misses += 1
            entry.last_access = time.time()

    @property
    def total_hits(self) -> int:
        with self._lock:
            return self._total_hits

    @property
    def total_misses(self) -> int:
        with self._lock:
            return self._total_misses

    @property
    def total_requests(self) -> int:
        return self.total_hits + self.total_misses

    @property
    def hit_rate(self) -> float:
        total = self.total_requests
        return (self.total_hits / total * 100.0) if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self._start_time
            total = self._total_hits + self._total_misses
            return {
                "total_hits": self._total_hits,
                "total_misses": self._total_misses,
                "total_requests": total,
                "hit_rate": round((self._total_hits / total * 100.0) if total > 0 else 0.0, 2),
                "unique_keys": len(self._entries),
                "uptime_seconds": round(uptime, 2),
            }

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()
            self._total_hits = 0
            self._total_misses = 0
            self._start_time = time.time()
