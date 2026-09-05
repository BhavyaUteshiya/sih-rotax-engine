"""
Digital Twin State Master Container Model.
SIH26054 — Module 03 Digital Twin Core.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.digital_twin.models.expected_state import ExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.residual_state import ResidualState
from src.digital_twin.models.twin_internal_state import TwinInternalState


class DigitalTwinStatus(str, Enum):
    """Lifecycle status enumerations for the Phase 1 Digital Twin."""
    OFFLINE = "OFFLINE"
    WAITING_FOR_DATA = "WAITING_FOR_DATA"
    SYNCHRONIZED = "SYNCHRONIZED"
    DATA_QUALITY_DEGRADED = "DATA_QUALITY_DEGRADED"
    DEVIATION_DETECTED = "DEVIATION_DETECTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class DigitalTwinState:
    """
    Master container combining Observed State, Expected State, Residuals,
    Operating Context, Data Quality, Causal Analysis, and Warnings.
    """
    timestamp: float = 0.0
    simulation_time: float = 0.0
    engine_id: str = "engine_1"
    aircraft_id: str = "rotax_914_uav"

    observed_state: ObservedState = field(default_factory=ObservedState)
    expected_state: ExpectedState = field(default_factory=ExpectedState)
    residual_state: ResidualState = field(default_factory=ResidualState)
    healthy_internal_state: TwinInternalState = field(default_factory=TwinInternalState)
    estimated_actual_state: TwinInternalState = field(default_factory=TwinInternalState)

    operating_context: Dict[str, Any] = field(default_factory=dict)

    data_quality: str = "GOOD"
    confidence: float = 1.0
    status: DigitalTwinStatus = DigitalTwinStatus.SYNCHRONIZED
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    causal_chain_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes complete DigitalTwinState to a JSON-compatible dictionary."""
        return {
            "timestamp": self.timestamp,
            "simulation_time": round(self.simulation_time, 2),
            "engine_id": self.engine_id,
            "aircraft_id": self.aircraft_id,
            "status": self.status.value if isinstance(self.status, DigitalTwinStatus) else str(self.status),
            "data_quality": self.data_quality,
            "confidence": round(self.confidence, 4),
            "operating_context": self.operating_context,
            "healthy_internal_state": self.healthy_internal_state.to_dict(),
            "estimated_actual_state": self.estimated_actual_state.to_dict(),
            "observed_state": self.observed_state.to_dict(),
            "expected_state": self.expected_state.to_dict(),
            "residual_state": self.residual_state.to_dict(),
            "warnings": self.warnings,
            "causal_chain_status": self.causal_chain_status,
        }
