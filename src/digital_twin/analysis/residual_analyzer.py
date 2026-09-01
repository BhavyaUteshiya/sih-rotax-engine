"""
Residual Analyzer — Calculates Residuals (Observed - Expected) and Evaluates Configured Thresholds.
SIH26054 — Module 03 Digital Twin Core.
"""

import os
from typing import Any, Dict, Optional
import yaml

from src.digital_twin.models.expected_state import ExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.residual_state import ParameterResidual, ResidualState


class ResidualAnalyzer:
    """
    Evaluates parameter-by-parameter residuals between ObservedState and ExpectedState.
    Thresholds are strictly configuration-driven loaded from configs/digital_twin_config.yaml.
    Evaluates EXACTLY the 18 authoritative Category C internal parameters:
    rpm, map_bar, turbo_rpm, airflow_kg_h, fuel_flow_kg_h, afr, combustion_energy,
    indicated_power_kw, torque_n_m, egt_c, cht_c, coolant_temp_c, oil_temp_c,
    oil_pressure_bar, turbo_boost_bar, gearbox_rpm, propeller_load_nm, thrust_n.
    """

    def __init__(self, config_path: str = "configs/digital_twin_config.yaml") -> None:
        self.config_path = config_path
        self.thresholds = self._load_thresholds(config_path)
        
        # Debounce filter state
        # engine_id -> { parameter_name -> timestamp_of_first_violation }
        self.violation_start_times: Dict[str, Dict[str, float]] = {}
        self.debounce_time_sec: float = 2.0  # Require 2 continuous seconds to flag as a warning

    def _load_thresholds(self, filepath: str) -> Dict[str, float]:
        """Loads residual threshold values from YAML configuration file."""
        defaults = {
            "rpm": 100.0,
            "map_bar": 0.05,
            "turbo_rpm": 5000.0,
            "airflow_kg_h": 15.0,
            "fuel_flow_kg_h": 1.2,
            "afr": 0.8,
            "combustion_energy": 1000.0,
            "indicated_power_kw": 5.0,
            "torque_n_m": 15.0,
            "egt_c": 25.0,
            "cht_c": 15.0,
            "coolant_temp_c": 15.0,
            "oil_temp_c": 10.0,
            "oil_pressure_bar": 0.5,
            "turbo_boost_bar": 0.05,
            "gearbox_rpm": 50.0,
            "propeller_load_nm": 10.0,
            "thrust_n": 50.0,
        }

        if not os.path.exists(filepath):
            return defaults

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            
            thresh_dict = cfg.get("digital_twin", {}).get("residual_thresholds", {})
            result = {}
            for k, default_val in defaults.items():
                if k in thresh_dict and isinstance(thresh_dict[k], dict):
                    result[k] = float(thresh_dict[k].get("value", default_val))
                elif k in thresh_dict and isinstance(thresh_dict[k], (int, float)):
                    result[k] = float(thresh_dict[k])
                else:
                    result[k] = default_val
            return result
        except Exception:
            return defaults

    def analyze(self, expected: ExpectedState, observed: ObservedState) -> ResidualState:
        """
        Computes ParameterResidual objects for all 18 authoritative internal parameters and aggregates into ResidualState.
        Applies a debounce filter to suppress instantaneous transient warnings.
        """
        res_state = ResidualState(
            timestamp=observed.timestamp,
            sequence_number=observed.sequence_number,
            engine_id=observed.engine_id
        )
        
        engine_id = observed.engine_id
        if engine_id not in self.violation_start_times:
            self.violation_start_times[engine_id] = {}

        mappings = [
            ("rpm", expected.rpm, observed.rpm, self.thresholds.get("rpm", 100.0), "RPM"),
            ("map_bar", expected.map_bar, observed.map_bar, self.thresholds.get("map_bar", 0.05), "bar"),
            ("turbo_rpm", expected.turbo_rpm, observed.turbo_rpm, self.thresholds.get("turbo_rpm", 5000.0), "RPM"),
            ("airflow_kg_h", expected.airflow_kg_h, observed.airflow_kg_h, self.thresholds.get("airflow_kg_h", 15.0), "kg/h"),
            ("fuel_flow_kg_h", expected.fuel_flow_kg_h, observed.fuel_flow_kg_h, self.thresholds.get("fuel_flow_kg_h", 1.2), "kg/h"),
            ("afr", expected.afr, observed.afr, self.thresholds.get("afr", 0.8), "ratio"),
            ("combustion_energy", expected.combustion_energy, observed.combustion_energy, self.thresholds.get("combustion_energy", 1000.0), "J"),
            ("indicated_power_kw", expected.indicated_power_kw, observed.indicated_power_kw, self.thresholds.get("indicated_power_kw", 5.0), "kW"),
            ("torque_n_m", expected.torque_n_m, observed.torque_n_m, self.thresholds.get("torque_n_m", 15.0), "N*m"),
            ("egt_c", expected.egt_c, observed.egt_c, self.thresholds.get("egt_c", 25.0), "°C"),
            ("cht_c", expected.cht_c, observed.cht_c, self.thresholds.get("cht_c", 15.0), "°C"),
            ("coolant_temp_c", expected.coolant_temp_c, observed.coolant_temp_c, self.thresholds.get("coolant_temp_c", 15.0), "°C"),
            ("oil_temp_c", expected.oil_temp_c, observed.oil_temp_c, self.thresholds.get("oil_temp_c", 10.0), "°C"),
            ("oil_pressure_bar", expected.oil_pressure_bar, observed.oil_pressure_bar, self.thresholds.get("oil_pressure_bar", 0.5), "bar"),
            ("turbo_boost_bar", expected.turbo_boost_bar, observed.turbo_boost_bar, self.thresholds.get("turbo_boost_bar", 0.05), "bar"),
            ("gearbox_rpm", expected.gearbox_rpm, observed.gearbox_rpm, self.thresholds.get("gearbox_rpm", 50.0), "RPM"),
            ("propeller_load_nm", expected.propeller_load_nm, observed.propeller_load_nm, self.thresholds.get("propeller_load_nm", 10.0), "N*m"),
            ("thrust_n", expected.thrust_n, observed.thrust_n, self.thresholds.get("thrust_n", 50.0), "N"),
        ]

        for name, exp_val, obs_val, thresh, unit in mappings:
            res = ParameterResidual.compute(
                parameter=name,
                expected=exp_val,
                observed=obs_val,
                threshold=thresh,
                unit=unit,
                timestamp=observed.timestamp
            )
            
            # Apply debounce logic for transient handling
            if res.warning_triggered:
                if name not in self.violation_start_times[engine_id]:
                    # Record the exact simulation time the violation began
                    self.violation_start_times[engine_id][name] = observed.timestamp
                
                # Check if the violation has persisted long enough
                duration = observed.timestamp - self.violation_start_times[engine_id][name]
                if duration < self.debounce_time_sec:
                    # Suppress the instantaneous warning for legitimate transients
                    res.warning_triggered = False
            else:
                # If within threshold, clear any tracked violation start time
                if name in self.violation_start_times[engine_id]:
                    del self.violation_start_times[engine_id][name]
                    
            res_state.add_residual(res)

        return res_state
