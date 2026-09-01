"""
Thread-Safe Multi-Rate Ring Buffer Implementation (Phase 11).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from collections import deque
import threading
from typing import Any, Dict, List, Optional, Tuple

from src.module01.models.sensor_sample import SensorMeasurement


class RingBufferOverflowError(Exception):
    """Exception raised when ring buffer overflows under REJECT_NEW policy."""
    pass


class RingBuffer:
    """
    Thread-safe lock-protected sliding window ring buffer for per-channel multi-rate telemetry streams.
    Enforces backpressure management and dropped record accounting.
    """

    def __init__(self, capacity: int = 10000, drop_policy: str = "DROP_OLDEST"):
        self.capacity = max(1, capacity)
        self.drop_policy = drop_policy.upper()
        self._buffer: deque = deque()
        self._lock = threading.Lock()
        self._dropped_count = 0

    def push(self, item: Any) -> bool:
        """
        Pushes an item into the ring buffer. Atomically handles overflow policies.
        Returns True if item was successfully added without dropping, or False if dropped.
        """
        with self._lock:
            if len(self._buffer) >= self.capacity:
                if self.drop_policy == "DROP_OLDEST":
                    self._buffer.popleft()
                    self._dropped_count += 1
                    self._buffer.append(item)
                    return True
                elif self.drop_policy == "REJECT_NEW":
                    self._dropped_count += 1
                    return False
                else:
                    self._buffer.popleft()
                    self._dropped_count += 1
                    self._buffer.append(item)
                    return True
            else:
                self._buffer.append(item)
                return True

    def get_latest(self) -> Optional[Any]:
        """Returns the most recent item in the buffer without removing it."""
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[-1]

    def get_all(self) -> List[Any]:
        """Returns a snapshot list of all items currently in the buffer."""
        with self._lock:
            return list(self._buffer)

    def get_range(self, start_time_sec: float, end_time_sec: float) -> List[SensorMeasurement]:
        """
        Queries SensorMeasurement items within time range [start_time_sec, end_time_sec].
        Filters on normalized_source_utc or source_timestamp.
        """
        with self._lock:
            results = []
            for item in self._buffer:
                if isinstance(item, SensorMeasurement):
                    ts = item.timestamps.normalized_source_utc if item.timestamps.normalized_source_utc is not None else item.timestamps.source_timestamp
                    if ts is not None and start_time_sec <= ts <= end_time_sec:
                        results.append(item)
            return results

    def size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def dropped_count(self) -> int:
        with self._lock:
            return self._dropped_count

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
