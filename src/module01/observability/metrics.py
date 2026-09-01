"""
Structured Observability & Ingestion Metrics Module (Phase 17).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import threading
from typing import Any, Dict


class MetricsTracker:
    """
    Thread-safe in-process metrics tracker for Module 01 pipeline observability.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "records_received_total": 0,
            "records_decoded_total": 0,
            "records_physically_valid_total": 0,
            "records_physically_invalid_total": 0,
            "timestamp_sync_failures_total": 0,
            "unresolved_clock_total": 0,
            "out_of_order_total": 0,
            "duplicate_total": 0,
            "conflicting_payload_total": 0,
            "dropped_records_total": 0,
            "storage_failures_total": 0,
            "storage_recovery_total": 0,
        }
        self._gauges: Dict[str, float] = {
            "buffer_utilization": 0.0,
            "pipeline_latency_ms": 0.0,
        }

    def increment(self, metric_name: str, amount: int = 1) -> None:
        with self._lock:
            if metric_name in self._counters:
                self._counters[metric_name] += amount

    def set_gauge(self, metric_name: str, value: float) -> None:
        with self._lock:
            self._gauges[metric_name] = value

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            res = dict(self._counters)
            res.update(self._gauges)
            return res

    def reset(self) -> None:
        with self._lock:
            for k in self._counters:
                self._counters[k] = 0
            for k in self._gauges:
                self._gauges[k] = 0.0
