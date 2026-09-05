"""
Phase 2C: Synchronization Result Contract
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SynchronizationStatus(str, Enum):
    """Explicit statuses describing the outcome of Observation/Expected temporal and contextual alignment."""
    SYNC_SUCCESS = "SYNC_SUCCESS"
    STALE_OBSERVATION = "STALE_OBSERVATION"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    MISSING_OBSERVATION = "MISSING_OBSERVATION"
    TIMESTAMP_MISMATCH = "TIMESTAMP_MISMATCH"
    ENGINE_MISMATCH = "ENGINE_MISMATCH"
    INVALID_OBSERVATION = "INVALID_OBSERVATION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DEGRADED_OBSERVATION = "DEGRADED_OBSERVATION"


@dataclass
class SynchronizationResult:
    """
    Authoritative contract containing the result of aligning the physical telemetry (Observed) 
    with the physics model baseline (Expected).
    """
    is_synchronized: bool
    status: SynchronizationStatus
    observed_timestamp: float
    expected_timestamp: float
    sequence_delta: int
    engine_id: str
    quality_effect: str
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes SynchronizationResult to a JSON-compatible dictionary."""
        return {
            "is_synchronized": self.is_synchronized,
            "status": self.status.value if isinstance(self.status, SynchronizationStatus) else str(self.status),
            "observed_timestamp": self.observed_timestamp,
            "expected_timestamp": self.expected_timestamp,
            "sequence_delta": self.sequence_delta,
            "engine_id": self.engine_id,
            "quality_effect": self.quality_effect,
            "reason": self.reason
        }
