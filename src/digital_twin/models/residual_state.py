"""
Residual State Model — Residuals (Observed - Expected) and Relative Deviation Metrics.
SIH26054 — Module 03 Digital Twin Core.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ParameterResidual:
    """
    Represents calculated residual error for a single physical parameter:
    residual = observed - expected
    relative_error = (observed - expected) / expected (or 0.0 if expected is 0)
    """
    parameter: str
    expected: Optional[float] = None
    observed: Optional[float] = None
    residual: float = 0.0
    relative_error: float = 0.0
    quality: str = "VALID"  # VALID, MISSING, INVALID_NAN, INVALID_INF
    warning_triggered: bool = False
    threshold: Optional[float] = None
    tolerance_type: str = "ABSOLUTE"
    unit: str = ""
    timestamp: float = 0.0

    @classmethod
    def compute(
        cls,
        parameter: str,
        expected: Optional[float],
        observed: Optional[float],
        threshold: Optional[float] = None,
        tolerance_type: str = "ABSOLUTE",
        unit: str = "",
        timestamp: float = 0.0
    ) -> "ParameterResidual":
        """Safely computes ParameterResidual handling None, zero, NaN, Inf, and invalid units."""
        if expected is None or observed is None:
            return cls(
                parameter=parameter,
                expected=expected,
                observed=observed,
                residual=0.0,
                relative_error=0.0,
                quality="MISSING",
                warning_triggered=False,
                threshold=threshold,
                tolerance_type=tolerance_type,
                unit=unit,
                timestamp=timestamp
            )

        if math.isnan(expected) or math.isnan(observed):
            return cls(
                parameter=parameter,
                expected=expected if not math.isnan(expected) else None,
                observed=observed if not math.isnan(observed) else None,
                residual=0.0,
                relative_error=0.0,
                quality="INVALID_NAN",
                warning_triggered=False,
                threshold=threshold,
                tolerance_type=tolerance_type,
                unit=unit,
                timestamp=timestamp
            )

        if math.isinf(expected) or math.isinf(observed):
            return cls(
                parameter=parameter,
                expected=expected if not math.isinf(expected) else None,
                observed=observed if not math.isinf(observed) else None,
                residual=0.0,
                relative_error=0.0,
                quality="INVALID_INF",
                warning_triggered=False,
                threshold=threshold,
                tolerance_type=tolerance_type,
                unit=unit,
                timestamp=timestamp
            )

        exp_val = float(expected)
        obs_val = float(observed)
        res = obs_val - exp_val

        if abs(exp_val) > 1e-9:
            rel_err = res / abs(exp_val)
        else:
            rel_err = 0.0

        warning = False
        if threshold is not None:
            if tolerance_type.upper() == "RELATIVE":
                if abs(rel_err) > threshold:
                    warning = True
            else:
                if abs(res) > threshold:
                    warning = True

        return cls(
            parameter=parameter,
            expected=exp_val,
            observed=obs_val,
            residual=res,
            relative_error=rel_err,
            quality="VALID",
            warning_triggered=warning,
            threshold=threshold,
            tolerance_type=tolerance_type,
            unit=unit,
            timestamp=timestamp
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes ParameterResidual to dictionary."""
        return {
            "parameter": self.parameter,
            "expected": round(self.expected, 4) if self.expected is not None else None,
            "observed": round(self.observed, 4) if self.observed is not None else None,
            "residual": round(self.residual, 4),
            "relative_error": round(self.relative_error, 4),
            "quality": self.quality,
            "warning_triggered": self.warning_triggered,
            "threshold": self.threshold,
            "unit": self.unit,
            "timestamp": self.timestamp
        }


@dataclass
class ResidualState:
    """
    Explicit schema for all evaluated engine/aircraft parameter residuals.
    """
    timestamp: float = 0.0
    sequence_number: int = 0
    engine_id: str = "engine_1"
    
    # Explicit 18 Category C Parameters
    rpm: Optional[ParameterResidual] = None
    map_bar: Optional[ParameterResidual] = None
    turbo_rpm: Optional[ParameterResidual] = None
    airflow_kg_h: Optional[ParameterResidual] = None
    fuel_flow_kg_h: Optional[ParameterResidual] = None
    afr: Optional[ParameterResidual] = None
    combustion_energy: Optional[ParameterResidual] = None
    combustion_efficiency: Optional[ParameterResidual] = None
    indicated_power_kw: Optional[ParameterResidual] = None
    torque_n_m: Optional[ParameterResidual] = None
    egt_c: Optional[ParameterResidual] = None
    cht_c: Optional[ParameterResidual] = None
    coolant_temp_c: Optional[ParameterResidual] = None
    oil_temp_c: Optional[ParameterResidual] = None
    oil_pressure_bar: Optional[ParameterResidual] = None
    turbo_boost_bar: Optional[ParameterResidual] = None
    gearbox_rpm: Optional[ParameterResidual] = None
    propeller_load_nm: Optional[ParameterResidual] = None
    thrust_n: Optional[ParameterResidual] = None

    @property
    def warnings_count(self) -> int:
        """Returns the number of residuals that triggered a warning."""
        count = 0
        for attr_name in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                          "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                          "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                          "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
            res = getattr(self, attr_name)
            if res is not None and getattr(res, "warning_triggered", False):
                count += 1
        return count

    def to_dict(self) -> Dict[str, Any]:
        """Serializes ResidualState to dictionary."""
        residuals_dict = {}
        for attr_name in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                          "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                          "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                          "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
            res = getattr(self, attr_name)
            if res is not None:
                residuals_dict[attr_name] = res.to_dict()

        return {
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "engine_id": self.engine_id,
            "residuals": residuals_dict,
            "warnings_count": self.warnings_count
        }
