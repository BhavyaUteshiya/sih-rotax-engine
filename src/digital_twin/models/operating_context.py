"""
Operating Context Model.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class OperatingContext:
    """
    Explicit schema for the operational context and external environment 
    in which the engine is running.
    """
    # Environmental conditions
    altitude_m: float = 0.0
    ambient_temp_c: float = 15.0
    ambient_pressure_kpa: float = 101.325
    ambient_density_kg_m3: float = 1.225
    relative_humidity_pct: float = 0.0
    wind_m_s: float = 0.0

    # Flight Dynamics
    airspeed_m_s: float = 0.0

    # Control Inputs
    throttle_position: float = 0.0
    fuel_pressure_pa: float = 250000.0
    starter_engaged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes OperatingContext to a dictionary."""
        return {
            "altitude_m": round(self.altitude_m, 1),
            "ambient_temp_c": round(self.ambient_temp_c, 2),
            "ambient_pressure_kpa": round(self.ambient_pressure_kpa, 2),
            "ambient_density_kg_m3": round(self.ambient_density_kg_m3, 4),
            "relative_humidity_pct": round(self.relative_humidity_pct, 1),
            "wind_m_s": round(self.wind_m_s, 2),
            "airspeed_m_s": round(self.airspeed_m_s, 2),
            "throttle_position": round(self.throttle_position, 4),
            "fuel_pressure_pa": round(self.fuel_pressure_pa, 0),
            "starter_engaged": self.starter_engaged,
        }
