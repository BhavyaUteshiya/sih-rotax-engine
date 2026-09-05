"""
Digital Twin State Master Container Model.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.models.health_state import HealthState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.estimated_actual_state import EstimatedActualState
from src.digital_twin.models.residual_state import ResidualState
from src.digital_twin.models.synchronization_result import SynchronizationResult


class DigitalTwinDataQuality(str, Enum):
    """Data quality enumeration for Phase 2A."""
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID = "INVALID"


class DigitalTwinStatus(str, Enum):
    """Lifecycle status enumerations for the Phase 2 Digital Twin."""
    OFFLINE = "OFFLINE"
    WAITING_FOR_DATA = "WAITING_FOR_DATA"
    SYNC_FAILED = "SYNC_FAILED"
    SYNCHRONIZED = "SYNCHRONIZED"
    DATA_QUALITY_DEGRADED = "DATA_QUALITY_DEGRADED"
    DEVIATION_DETECTED = "DEVIATION_DETECTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class DigitalTwinState:
    """
    Master container (Phase 2A Contract) combining all explicit sub-states.
    Strictly isolates observed, healthy expected, and estimated actual states.
    """
    timestamp: float = 0.0
    engine_id: str = "engine_1"
    aircraft_id: str = "rotax_914_uav"

    operating_context: OperatingContext = field(default_factory=OperatingContext)
    observed_state: ObservedState = field(default_factory=ObservedState)
    healthy_expected_state: HealthyExpectedState = field(default_factory=HealthyExpectedState)
    estimated_actual_state: EstimatedActualState = field(default_factory=EstimatedActualState)
    residual_state: ResidualState = field(default_factory=ResidualState)
    health_state: HealthState = field(default_factory=HealthState)
    synchronization_result: Optional[SynchronizationResult] = None

    data_quality: DigitalTwinDataQuality = DigitalTwinDataQuality.GOOD
    confidence: float = 1.0
    status: DigitalTwinStatus = DigitalTwinStatus.WAITING_FOR_DATA
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes complete DigitalTwinState to a JSON-compatible dictionary."""
        return {
            "timestamp": self.timestamp,
            "engine_id": self.engine_id,
            "aircraft_id": self.aircraft_id,
            "status": self.status.value if isinstance(self.status, DigitalTwinStatus) else str(self.status),
            "data_quality": self.data_quality.value if isinstance(self.data_quality, DigitalTwinDataQuality) else str(self.data_quality),
            "confidence": round(self.confidence, 4),
            "operating_context": self.operating_context.to_dict(),
            "health_state": self.health_state.to_dict(),
            "synchronization_result": self.synchronization_result.to_dict() if self.synchronization_result else None,
            "observed_state": self.observed_state.to_dict(),
            "healthy_expected_state": self.healthy_expected_state.to_dict(),
            "estimated_actual_state": self.estimated_actual_state.to_dict(),
            "residual_state": self.residual_state.to_dict(),
            "warnings": self.warnings,
        }
