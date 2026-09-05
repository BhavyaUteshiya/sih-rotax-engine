"""
Health State Model.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class HealthState:
    """
    Explicit schema for the engine's health, tracking component degradation,
    fault flags, and overall health status.
    """
    timestamp: float = 0.0

    # Degradation factors (1.0 = healthy, lower = degraded)
    turbo_efficiency_degradation: float = 1.0
    compressor_efficiency_degradation: float = 1.0
    volumetric_efficiency_degradation: float = 1.0
    combustion_efficiency_degradation: float = 1.0
    friction_factor_increase: float = 1.0

    # Fault Flags
    active_faults: List[str] = field(default_factory=list)

    # Remaining Useful Life (RUL) estimates in hours (not implemented in 2A)
    engine_rul_hours: float = 1200.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes HealthState to a dictionary."""
        return {
            "timestamp": self.timestamp,
            "turbo_efficiency_degradation": round(self.turbo_efficiency_degradation, 4),
            "compressor_efficiency_degradation": round(self.compressor_efficiency_degradation, 4),
            "volumetric_efficiency_degradation": round(self.volumetric_efficiency_degradation, 4),
            "combustion_efficiency_degradation": round(self.combustion_efficiency_degradation, 4),
            "friction_factor_increase": round(self.friction_factor_increase, 4),
            "active_faults": self.active_faults.copy(),
            "engine_rul_hours": round(self.engine_rul_hours, 1),
        }
