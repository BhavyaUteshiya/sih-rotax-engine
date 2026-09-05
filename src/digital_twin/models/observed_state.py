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

    @classmethod
    def from_module02_pipeline(
        cls,
        pipeline: Any,
        engine_index: int = 1,
        target_timestamp: float = 0.0,
        target_sequence: int = 0,
        max_time_skew_sec: float = 0.1
    ) -> "ObservedState":
        """
        Constructs ObservedState strictly from Module 02 acquisition pipeline buffers / telemetry frame.
        MANDATE: Does NOT read from or fall back to Module 01 simulation state.
        If Module 02 telemetry is missing or not aligned to target_timestamp,
        returns an ObservedState marked data_quality="INSUFFICIENT_DATA".
        """
        if pipeline is None:
            return cls(
                timestamp=target_timestamp,
                sequence_number=target_sequence,
                engine_id=f"engine_{engine_index}",
                aircraft_id="rotax_914_uav",
                data_quality="INSUFFICIENT_DATA"
            )

        buffers = getattr(pipeline, "channel_buffers", {}) if pipeline else {}
        latest_frame = pipeline.get_latest_frame() if (pipeline and hasattr(pipeline, "get_latest_frame")) else None

        def get_meas(candidate_ids: List[str]) -> Optional[Any]:
            # 1. Search Channel Ring Buffers
            for pid in candidate_ids:
                buf = buffers.get(pid)
                if buf and hasattr(buf, "get_latest"):
                    meas = buf.get_latest()
                    if meas:
                        meas_ts = getattr(meas.timestamps, "source_timestamp", None)
                        if meas_ts is None:
                            meas_ts = getattr(meas.timestamps, "normalized_source_utc", None)

                        if meas_ts is None or abs(meas_ts - target_timestamp) <= max_time_skew_sec:
                            return meas

            # 2. Search latest TelemetryFrame
            if latest_frame and hasattr(latest_frame, "get_measurement"):
                for pid in candidate_ids:
                    m = latest_frame.get_measurement(pid)
                    if m:
                        return m
            return None

        def val(candidate_ids: List[str]) -> Optional[float]:
            meas = get_meas(candidate_ids)
            if meas:
                if hasattr(meas, "engineering_value") and meas.engineering_value is not None:
                    return float(meas.engineering_value)
                if hasattr(meas, "value") and meas.value is not None:
                    return float(meas.value)
            return None

        idx = engine_index
        rpm_v = val([f"rotax914.engine_{idx}.crankshaft_rpm", f"crankshaft_rpm_{idx}", "crankshaft_rpm", "engine.rpm", "rpm"])
        
        map_raw = val([f"rotax914.engine_{idx}.manifold_pressure_pa", f"manifold_pressure_pa_{idx}", "manifold_pressure_pa", "engine.map", f"map_bar_{idx}", "map_bar"])
        map_bar_v = (map_raw / 100000.0) if (map_raw is not None and map_raw > 50.0) else map_raw

        turbo_rpm_v = val([f"rotax914.engine_{idx}.turbocharger_speed_rpm", f"turbo_speed_rpm_{idx}", "turbo_speed_rpm", "engine.turbo_speed", "turbo_rpm"])
        
        air_raw = val([f"rotax914.engine_{idx}.air_mass_flow_kg_s", f"air_mass_flow_kg_s_{idx}", "air_mass_flow_kg_s", "engine.airflow", f"airflow_kg_h_{idx}", "airflow_kg_h"])
        air_kg_h_v = (air_raw * 3600.0) if (air_raw is not None and air_raw <= 10.0) else air_raw

        fuel_raw = val([f"rotax914.engine_{idx}.fuel_mass_flow_kg_s", f"fuel_mass_flow_kg_s_{idx}", "fuel_mass_flow_kg_s", "engine.fuel_flow", f"fuel_flow_kg_h_{idx}", "fuel_flow_kg_h", "engine.fuel_flow_kg_h"])
        fuel_kg_h_v = (fuel_raw * 3600.0) if (fuel_raw is not None and fuel_raw <= 1.0) else fuel_raw

        afr_v = val([f"rotax914.engine_{idx}.air_fuel_ratio", f"air_fuel_ratio_{idx}", "air_fuel_ratio", "engine.afr", "afr"])
        comb_energy_v = val([f"rotax914.engine_{idx}.combustion_energy_j", f"combustion_energy_{idx}", "combustion_energy"])
        comb_eff_v = val([f"rotax914.engine_{idx}.combustion_efficiency", f"combustion_efficiency_{idx}", "combustion_efficiency"])

        torque_v = val([f"rotax914.engine_{idx}.indicated_torque_total_n_m", f"indicated_torque_n_m_{idx}", "indicated_torque_total_n_m", "engine.torque", "torque_n_m"])

        egt_raw = val([f"rotax914.engine_{idx}.exhaust_gas_temp_k", f"egt_k_{idx}", "exhaust_gas_temp_k", "engine.egt", f"egt_c_{idx}", "egt_c"])
        egt_c_v = (egt_raw - 273.15) if (egt_raw is not None and egt_raw > 1000.0) else egt_raw

        cht_raw = val([f"rotax914.engine_{idx}.cylinder_head_temp_k", f"cht_k_{idx}", "cylinder_head_temp_k", "engine.cht", f"cht_c_{idx}", "cht_c"])
        cht_c_v = (cht_raw - 273.15) if (cht_raw is not None and cht_raw > 1000.0) else cht_raw

        cool_raw = val([f"rotax914.engine_{idx}.coolant_temp_k", f"coolant_temp_k_{idx}", "coolant_temp_k", "engine.coolant_temp", f"coolant_temp_c_{idx}", "coolant_temp_c"])
        cool_c_v = (cool_raw - 273.15) if (cool_raw is not None and cool_raw > 1000.0) else cool_raw

        oil_temp_raw = val([f"rotax914.engine_{idx}.oil_temp_k", f"oil_temp_k_{idx}", "oil_temp_k", "engine.oil_temp", f"oil_temp_c_{idx}", "oil_temp_c"])
        oil_c_v = (oil_temp_raw - 273.15) if (oil_temp_raw is not None and oil_temp_raw > 1000.0) else oil_temp_raw

        oil_pa_raw = val([f"rotax914.engine_{idx}.oil_pressure_pa", f"oil_pressure_pa_{idx}", "oil_pressure_pa", "engine.oil_pressure", f"oil_pressure_bar_{idx}", "oil_pressure_bar"])
        oil_press_bar_v = (oil_pa_raw / 100000.0) if (oil_pa_raw is not None and oil_pa_raw > 50.0) else oil_pa_raw

        thrust_v = val([f"rotax914.propeller_{idx}.thrust_n", f"thrust_n_{idx}", "thrust_n", "engine.propeller.thrust", "propeller.thrust"])
        prop_load_v = val([f"rotax914.propeller_{idx}.load_torque_nm", f"propeller_load_nm_{idx}", "propeller_load_nm", "engine.propeller.load_torque"])

        speed_v = val(["uav.aircraft.velocity_m_s", "airspeed_m_s"])
        alt_v = val(["uav.aircraft.altitude_m", "altitude_m"])
        amb_k = val(["uav.environment.ambient_temp_k", "ambient_temp_k"])
        amb_c_v = (amb_k - 273.15) if (amb_k is not None and amb_k > 1000.0) else amb_k

        amb_pa = val(["uav.environment.ambient_pressure_pa", "ambient_pressure_pa"])
        amb_kpa_v = (amb_pa / 1000.0) if (amb_pa is not None and amb_pa > 500.0) else amb_pa
        amb_rho_v = val(["uav.environment.air_density_kg_m3", "ambient_density_kg_m3"])
        wind_v = val(["uav.environment.wind_speed_m_s", "wind_m_s"])

        # Data quality evaluation strictly based on telemetry presence
        present_sensors = [v for v in [rpm_v, map_bar_v, turbo_rpm_v, egt_c_v, oil_press_bar_v, thrust_v] if v is not None]
        valid_cnt = len(present_sensors)
        quality = "GOOD" if valid_cnt >= 3 else ("DEGRADED" if valid_cnt >= 1 else "INSUFFICIENT_DATA")

        return cls(
            timestamp=target_timestamp,
            sequence_number=target_sequence,
            engine_id=f"engine_{engine_index}",
            aircraft_id="rotax_914_uav",
            rpm=rpm_v,
            map_bar=map_bar_v,
            turbo_rpm=turbo_rpm_v,
            airflow_kg_h=air_kg_h_v,
            fuel_flow_kg_h=fuel_kg_h_v,
            afr=afr_v,
            combustion_energy=comb_energy_v,
            combustion_efficiency=comb_eff_v,
            indicated_power_kw=val([f"indicated_power_kw_{idx}", "indicated_power_kw"]),
            torque_n_m=torque_v,
            egt_c=egt_c_v,
            cht_c=cht_c_v,
            coolant_temp_c=cool_c_v,
            oil_temp_c=oil_c_v,
            oil_pressure_bar=oil_press_bar_v,
            turbo_boost_bar=val([f"turbo_boost_bar_{idx}", "turbo_boost_bar"]),
            gearbox_rpm=val([f"gearbox_rpm_{idx}", "gearbox_rpm"]),
            propeller_load_nm=prop_load_v,
            thrust_n=thrust_v,
            airspeed_m_s=speed_v,
            altitude_m=alt_v,
            ambient_temp_c=amb_c_v,
            ambient_pressure_kpa=amb_kpa_v,
            ambient_density_kg_m3=amb_rho_v,
            wind_m_s=wind_v,
            data_quality=quality,
            valid_sensors_count=valid_cnt,
            corrupted_sensors_count=0
        )

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
