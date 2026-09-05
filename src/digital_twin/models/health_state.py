"""
Health State Model.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class HealthLevel(str, Enum):
    """Deterministic health classification levels for Phase 2F."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class HealthState:
    """
    Explicit schema for the engine's deterministic health assessment,
    driven by quantitative residual deviation and data quality evidence.
    """
    timestamp: float = 0.0
    engine_id: str = "engine_1"

    health_level: HealthLevel = HealthLevel.UNKNOWN
    is_assessable: bool = False
    health_confidence: float = 0.0
    assessment_reason: str = "Uninitialized"
    dominant_parameter: str = "NONE"

    critical_count: int = 0
    warning_count: int = 0
    missing_count: int = 0
    invalid_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes HealthState to a JSON-compatible dictionary."""
        return {
            "timestamp": self.timestamp,
            "engine_id": self.engine_id,
            "health_level": self.health_level.value if isinstance(self.health_level, HealthLevel) else str(self.health_level),
            "is_assessable": self.is_assessable,
            "health_confidence": round(self.health_confidence, 4),
            "assessment_reason": self.assessment_reason,
            "dominant_parameter": self.dominant_parameter,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "missing_count": self.missing_count,
            "invalid_count": self.invalid_count,
        }
