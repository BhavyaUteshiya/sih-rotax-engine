"""
Residual Analyzer — Calculates Residuals (Actual - Expected) and Evaluates Configured Thresholds.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

import os
import math
from typing import Any, Dict, Optional

import yaml

from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.estimated_actual_state import EstimatedActualState
from src.digital_twin.models.residual_state import ParameterResidual, ResidualState


class ResidualAnalyzer:
    """
    Evaluates parameter-by-parameter residuals between Actual (Estimated or Observed) and HealthyExpectedState.
    Thresholds are strictly configuration-driven loaded from configs/digital_twin_config.yaml.
    Evaluates EXACTLY the 19 authoritative Category C internal parameters:
    rpm, map_bar, turbo_rpm, airflow_kg_h, fuel_flow_kg_h, afr, combustion_energy,
    combustion_efficiency, indicated_power_kw, torque_n_m, egt_c, cht_c, coolant_temp_c,
    oil_temp_c, oil_pressure_bar, turbo_boost_bar, gearbox_rpm, propeller_load_nm, thrust_n.
    """

    def __init__(self, config_path: str = "configs/digital_twin_config.yaml", engine_config_path: Optional[str] = None) -> None:
        self.config_path = config_path
        self.thresholds = self._load_thresholds(config_path)
        
        # Debounce filter state
        # engine_id -> { parameter_name -> timestamp_of_first_violation }
        self.violation_start_times: Dict[str, Dict[str, float]] = {}
        self.debounce_time_sec: float = 2.0  # Require 2 continuous seconds to flag as a warning/critical

        # Hard limits from physical engine config to bypass debounce
        self.hard_limits = self._load_hard_limits(engine_config_path)

    def _load_thresholds(self, filepath: str) -> Dict[str, Dict[str, Any]]:
        """Loads residual threshold configurations from YAML. Uses emergency fallbacks if YAML is missing."""
        emergency_fallback_defaults = {
            "rpm": {"warning_threshold": 100.0, "critical_threshold": 200.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "map_bar": {"warning_threshold": 0.05, "critical_threshold": 0.1, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "turbo_rpm": {"warning_threshold": 5000.0, "critical_threshold": 10000.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "airflow_kg_h": {"warning_threshold": 15.0, "critical_threshold": 30.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "fuel_flow_kg_h": {"warning_threshold": 1.2, "critical_threshold": 2.4, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "afr": {"warning_threshold": 0.8, "critical_threshold": 1.6, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "combustion_energy": {"warning_threshold": 1000.0, "critical_threshold": 2000.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "combustion_efficiency": {"warning_threshold": 0.1, "critical_threshold": 0.2, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "indicated_power_kw": {"warning_threshold": 5.0, "critical_threshold": 10.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "torque_n_m": {"warning_threshold": 15.0, "critical_threshold": 30.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "egt_c": {"warning_threshold": 25.0, "critical_threshold": 50.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "cht_c": {"warning_threshold": 15.0, "critical_threshold": 30.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "coolant_temp_c": {"warning_threshold": 15.0, "critical_threshold": 30.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "oil_temp_c": {"warning_threshold": 10.0, "critical_threshold": 20.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "oil_pressure_bar": {"warning_threshold": 0.5, "critical_threshold": 1.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "turbo_boost_bar": {"warning_threshold": 0.05, "critical_threshold": 0.1, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "gearbox_rpm": {"warning_threshold": 50.0, "critical_threshold": 100.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "propeller_load_nm": {"warning_threshold": 10.0, "critical_threshold": 20.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
            "thrust_n": {"warning_threshold": 50.0, "critical_threshold": 100.0, "tolerance_type": "ABSOLUTE", "debounce_sec": 2.0, "denominator_floor": 1e-3},
        }

        if not os.path.exists(filepath):
            return emergency_fallback_defaults

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            
            thresh_dict = cfg.get("digital_twin", {}).get("residual_thresholds", {})
            result = {}
            for k, default_vals in emergency_fallback_defaults.items():
                if k in thresh_dict and isinstance(thresh_dict[k], dict):
                    result[k] = {
                        "warning_threshold": float(thresh_dict[k].get("warning_threshold", default_vals["warning_threshold"])),
                        "critical_threshold": float(thresh_dict[k].get("critical_threshold", default_vals["critical_threshold"])),
                        "tolerance_type": str(thresh_dict[k].get("tolerance_type", default_vals["tolerance_type"])),
                        "debounce_sec": float(thresh_dict[k].get("debounce_sec", default_vals["debounce_sec"])),
                        "denominator_floor": float(thresh_dict[k].get("denominator_floor", default_vals["denominator_floor"]))
                    }
                else:
                    result[k] = default_vals
            return result
        except Exception:
            return emergency_fallback_defaults

    def _load_hard_limits(self, filepath: str) -> Dict[str, Dict[str, float]]:
        """Loads physical operating safety limits from engine configuration to bypass debounce. Returns dict of max_limits and min_limits."""
        max_limits = {}
        min_limits = {}
        limits = {"max": max_limits, "min": min_limits}
        if not filepath or not os.path.exists(filepath):
            return limits
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                
            # Extract applicable hard limits. E.g. max_takeoff_rpm
            pp = cfg.get("power_and_performance", {})
            if "rated_rpm" in pp:
                max_limits["rpm"] = float(pp["rated_rpm"].get("value", 5800.0))
                
            turbo = cfg.get("turbocharger", {})
            if "max_manifold_absolute_pressure_pa" in turbo:
                max_limits["map_bar"] = float(turbo["max_manifold_absolute_pressure_pa"].get("value", 132000.0)) / 100000.0
            if "max_turbo_speed_rpm" in turbo:
                max_limits["turbo_rpm"] = float(turbo["max_turbo_speed_rpm"].get("value", 140000.0))
                
            thermal = cfg.get("thermal", {})
            if "max_safe_cht_k" in thermal:
                max_limits["cht_c"] = float(thermal["max_safe_cht_k"].get("value", 408.15)) - 273.15
            if "max_safe_egt_k" in thermal:
                max_limits["egt_c"] = float(thermal["max_safe_egt_k"].get("value", 1223.15)) - 273.15
            if "max_safe_oil_temp_k" in thermal:
                max_limits["oil_temp_c"] = float(thermal["max_safe_oil_temp_k"].get("value", 403.15)) - 273.15
            if "max_safe_coolant_temp_k" in thermal:
                max_limits["coolant_temp_c"] = float(thermal["max_safe_coolant_temp_k"].get("value", 393.15)) - 273.15
                
            lube = cfg.get("lubrication", {})
            if "max_oil_pressure_pa" in lube:
                max_limits["oil_pressure_bar"] = float(lube["max_oil_pressure_pa"].get("value", 700000.0)) / 100000.0
            if "min_oil_pressure_pa" in lube:
                min_limits["oil_pressure_bar"] = float(lube["min_oil_pressure_pa"].get("value", 80000.0)) / 100000.0
                
            return limits
        except Exception:
            return limits

    def analyze(self, expected: HealthyExpectedState, observed: ObservedState, estimated: Optional[EstimatedActualState] = None) -> ResidualState:
        """
        Computes ParameterResidual objects for all 19 authoritative internal parameters and aggregates into ResidualState.
        Uses EstimatedActualState if available and valid (not NaN), otherwise falls back to ObservedState.
        Applies a parameter-specific debounce filter to suppress instantaneous transient warnings.
        """
        engine_id = observed.engine_id
        if engine_id not in self.violation_start_times:
            self.violation_start_times[engine_id] = {}

        computed_residuals = {}

        def get_actual(name: str) -> tuple[Optional[float], str]:
            ukf_keys = {
                "rpm", "map_bar", "turbo_rpm", "airflow_kg_h", 
                "fuel_flow_kg_h", "afr", "cht_c", "oil_temp_c"
            }
            if estimated is not None and not estimated.is_prediction_only and name in ukf_keys:
                val = getattr(estimated, name, None)
                if val is not None and not math.isnan(val):
                    return val, "ESTIMATED"
            
            val = getattr(observed, name, None)
            if val is not None and not math.isnan(val):
                return val, "OBSERVED"
            
            return None, "NONE"

        mappings = [
            ("rpm", "RPM"),
            ("map_bar", "bar"),
            ("turbo_rpm", "RPM"),
            ("airflow_kg_h", "kg/h"),
            ("fuel_flow_kg_h", "kg/h"),
            ("afr", "ratio"),
            ("combustion_energy", "J"),
            ("combustion_efficiency", "ratio"),
            ("indicated_power_kw", "kW"),
            ("torque_n_m", "N*m"),
            ("egt_c", "°C"),
            ("cht_c", "°C"),
            ("coolant_temp_c", "°C"),
            ("oil_temp_c", "°C"),
            ("oil_pressure_bar", "bar"),
            ("turbo_boost_bar", "bar"),
            ("gearbox_rpm", "RPM"),
            ("propeller_load_nm", "N*m"),
            ("thrust_n", "N"),
        ]

        for name, unit in mappings:
            exp_val = getattr(expected, name, None)
            act_val, act_source = get_actual(name)
            
            cfg = self.thresholds.get(name, {
                "warning_threshold": 0.0,
                "critical_threshold": 0.0,
                "tolerance_type": "ABSOLUTE",
                "debounce_sec": 2.0,
                "denominator_floor": 1e-3
            })
            
            res = ParameterResidual.compute(
                parameter=name,
                expected=exp_val,
                actual=act_val,
                actual_source=act_source,
                warning_threshold=cfg["warning_threshold"],
                critical_threshold=cfg["critical_threshold"],
                tolerance_type=cfg["tolerance_type"],
                denominator_floor=cfg["denominator_floor"],
                unit=unit,
                timestamp=observed.timestamp
            )
            
            # Apply debounce logic for transient handling
            if res.status in ("WARNING", "CRITICAL"):
                bypass_debounce = False
                
                # Severe/hard-limit bypass check
                if act_val is not None:
                    if name in self.hard_limits.get("max", {}) and act_val >= self.hard_limits["max"][name]:
                        bypass_debounce = True
                    if name in self.hard_limits.get("min", {}) and act_val <= self.hard_limits["min"][name]:
                        bypass_debounce = True
                
                if bypass_debounce or cfg["debounce_sec"] <= 0.0:
                    if name in self.violation_start_times[engine_id]:
                        del self.violation_start_times[engine_id][name]
                else:
                    if name not in self.violation_start_times[engine_id]:
                        self.violation_start_times[engine_id][name] = observed.timestamp
                    
                    duration = observed.timestamp - self.violation_start_times[engine_id][name]
                    if duration < cfg["debounce_sec"]:
                        res.status = "GOOD"
            else:
                if name in self.violation_start_times[engine_id]:
                    del self.violation_start_times[engine_id][name]
                    
            computed_residuals[name] = res

        res_state = ResidualState(
            timestamp=observed.timestamp,
            sequence_number=observed.sequence_number,
            engine_id=observed.engine_id,
            **computed_residuals
        )
        return res_state
