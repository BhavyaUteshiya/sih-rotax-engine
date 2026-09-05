"""
Estimated Actual State Model — The Digital Twin's best estimate of the actual physical state.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, List


@dataclass
class EstimatedActualState:
    """
    Represents the twin's best estimate of the actual engine state.
    This is independently estimated and incorporates degradation, faults, and estimators,
    distinguishing it strictly from the HealthyExpectedState.
    
    NOTE: Only the 8 UKF state vector parameters are actively estimated:
    [rpm, map_bar, turbo_rpm, airflow_kg_h, fuel_flow_kg_h, afr, cht_c, oil_temp_c].
    The remaining 11 parameters are NOT estimated by the UKF; they are simply 
    pass-through values from the HealthyExpectedState (and remain healthy-reference values).
    """
    timestamp: float = 0.0
    sequence_number: int = 0
    engine_id: str = "engine_1"
    aircraft_id: str = "rotax_914_uav"

    # Estimated Engine Parameters (19 Category C Internal Parameters)
    rpm: float = 0.0
    map_bar: float = 1.01325
    turbo_rpm: float = 0.0
    airflow_kg_h: float = 0.0
    fuel_flow_kg_h: float = 0.0
    afr: float = 14.7
    combustion_energy: Optional[float] = None
    combustion_efficiency: float = 0.0
    indicated_power_kw: float = 0.0
    torque_n_m: float = 0.0
    egt_c: float = 15.0
    cht_c: float = 15.0
    coolant_temp_c: float = 15.0
    oil_temp_c: float = 15.0
    oil_pressure_bar: float = 0.0
    turbo_boost_bar: float = 0.0
    gearbox_rpm: float = 0.0
    propeller_load_nm: float = 0.0
    thrust_n: float = 0.0

    estimation_confidence: float = 1.0
    is_prediction_only: bool = False
    covariance: Optional[List[List[float]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes EstimatedActualState to a dictionary."""
        return {
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "engine_id": self.engine_id,
            "aircraft_id": self.aircraft_id,
            "rpm": round(self.rpm, 2),
            "map_bar": round(self.map_bar, 4),
            "turbo_rpm": round(self.turbo_rpm, 1),
            "airflow_kg_h": round(self.airflow_kg_h, 3),
            "fuel_flow_kg_h": round(self.fuel_flow_kg_h, 3),
            "afr": round(self.afr, 2),
            "combustion_energy": round(self.combustion_energy, 2) if self.combustion_energy is not None else None,
            "combustion_efficiency": round(self.combustion_efficiency, 4),
            "indicated_power_kw": round(self.indicated_power_kw, 2),
            "torque_n_m": round(self.torque_n_m, 2),
            "egt_c": round(self.egt_c, 2),
            "cht_c": round(self.cht_c, 2),
            "coolant_temp_c": round(self.coolant_temp_c, 2),
            "oil_temp_c": round(self.oil_temp_c, 2),
            "oil_pressure_bar": round(self.oil_pressure_bar, 4),
            "turbo_boost_bar": round(self.turbo_boost_bar, 4),
            "gearbox_rpm": round(self.gearbox_rpm, 2),
            "propeller_load_nm": round(self.propeller_load_nm, 2),
            "thrust_n": round(self.thrust_n, 2),
            "estimation_confidence": self.estimation_confidence,
            "is_prediction_only": self.is_prediction_only,
            "covariance": self.covariance,
        }
