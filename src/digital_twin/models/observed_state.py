"""
Observed State Model — Validated & SI-Normalized Telemetry Ingested strictly from Module 02.
SIH26054 — Module 03 Digital Twin Core.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ObservedState:
    """
    Encapsulates validated, normalized telemetry observations coming strictly from Module 02.
    MANDATE: Does NOT read directly from Module 01 simulation truth state and contains ZERO fallbacks to Module 01.
    Supports complete 18 internal Category C parameters. Missing telemetry channels remain None.
    Disambiguates combustion_energy from combustion_efficiency.
    """
    timestamp: float = 0.0
    sequence_number: int = 0
    engine_id: str = "engine_1"
    aircraft_id: str = "rotax_914_uav"

    # Engine Operating Parameters (18 Category C Parameters)
    rpm: Optional[float] = None
    map_bar: Optional[float] = None
    turbo_rpm: Optional[float] = None
    airflow_kg_h: Optional[float] = None
    fuel_flow_kg_h: Optional[float] = None
    afr: Optional[float] = None
    combustion_energy: Optional[float] = None
    combustion_efficiency: Optional[float] = None
    indicated_power_kw: Optional[float] = None
    torque_n_m: Optional[float] = None
    egt_c: Optional[float] = None
    cht_c: Optional[float] = None
    coolant_temp_c: Optional[float] = None
    oil_temp_c: Optional[float] = None
    oil_pressure_bar: Optional[float] = None
    turbo_boost_bar: Optional[float] = None
    gearbox_rpm: Optional[float] = None
    propeller_load_nm: Optional[float] = None
    thrust_n: Optional[float] = None

    # Environmental & Aircraft Parameters
    airspeed_m_s: Optional[float] = None
    altitude_m: Optional[float] = None
    ambient_temp_c: Optional[float] = None
    ambient_pressure_kpa: Optional[float] = None
    ambient_density_kg_m3: Optional[float] = None
    wind_m_s: Optional[float] = None

    # Data Integrity & Quality Metadata
    data_quality: str = "INSUFFICIENT_DATA"  # GOOD, DEGRADED, INSUFFICIENT_DATA, INVALID
    valid_sensors_count: int = 0
    corrupted_sensors_count: int = 0



    def to_dict(self) -> Dict[str, Any]:
        """Serializes ObservedState to a dictionary."""
        return {
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "engine_id": self.engine_id,
            "aircraft_id": self.aircraft_id,
            "rpm": round(self.rpm, 2) if self.rpm is not None else None,
            "map_bar": round(self.map_bar, 4) if self.map_bar is not None else None,
            "turbo_rpm": round(self.turbo_rpm, 1) if self.turbo_rpm is not None else None,
            "airflow_kg_h": round(self.airflow_kg_h, 3) if self.airflow_kg_h is not None else None,
            "fuel_flow_kg_h": round(self.fuel_flow_kg_h, 3) if self.fuel_flow_kg_h is not None else None,
            "afr": round(self.afr, 2) if self.afr is not None else None,
            "combustion_energy": round(self.combustion_energy, 2) if self.combustion_energy is not None else None,
            "combustion_efficiency": round(self.combustion_efficiency, 4) if self.combustion_efficiency is not None else None,
            "indicated_power_kw": round(self.indicated_power_kw, 2) if self.indicated_power_kw is not None else None,
            "torque_n_m": round(self.torque_n_m, 2) if self.torque_n_m is not None else None,
            "egt_c": round(self.egt_c, 2) if self.egt_c is not None else None,
            "cht_c": round(self.cht_c, 2) if self.cht_c is not None else None,
            "coolant_temp_c": round(self.coolant_temp_c, 2) if self.coolant_temp_c is not None else None,
            "oil_temp_c": round(self.oil_temp_c, 2) if self.oil_temp_c is not None else None,
            "oil_pressure_bar": round(self.oil_pressure_bar, 4) if self.oil_pressure_bar is not None else None,
            "turbo_boost_bar": round(self.turbo_boost_bar, 4) if self.turbo_boost_bar is not None else None,
            "gearbox_rpm": round(self.gearbox_rpm, 2) if self.gearbox_rpm is not None else None,
            "propeller_load_nm": round(self.propeller_load_nm, 2) if self.propeller_load_nm is not None else None,
            "thrust_n": round(self.thrust_n, 2) if self.thrust_n is not None else None,
            "airspeed_m_s": round(self.airspeed_m_s, 2) if self.airspeed_m_s is not None else None,
            "altitude_m": round(self.altitude_m, 1) if self.altitude_m is not None else None,
            "ambient_temp_c": round(self.ambient_temp_c, 2) if self.ambient_temp_c is not None else None,
            "ambient_pressure_kpa": round(self.ambient_pressure_kpa, 2) if self.ambient_pressure_kpa is not None else None,
            "ambient_density_kg_m3": round(self.ambient_density_kg_m3, 4) if self.ambient_density_kg_m3 is not None else None,
            "wind_m_s": round(self.wind_m_s, 2) if self.wind_m_s is not None else None,
            "data_quality": self.data_quality,
            "valid_sensors_count": self.valid_sensors_count,
            "corrupted_sensors_count": self.corrupted_sensors_count,
        }
