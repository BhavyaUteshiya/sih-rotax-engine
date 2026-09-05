"""
Residual State Model — Residuals (Observed - Expected) and Relative Deviation Metrics.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ParameterResidual:
    """
    Represents calculated residual error for a single physical parameter:
    residual = actual - expected
    relative_error = (actual - expected) / expected (or 0.0 if expected is 0)
    """
    parameter: str
    expected: Optional[float] = None
    actual: Optional[float] = None
    actual_source: str = "NONE"  # "ESTIMATED", "OBSERVED", or "NONE"
    residual: float = 0.0
    relative_error: float = 0.0
    status: str = "GOOD"  # GOOD, WARNING, CRITICAL, MISSING, INVALID_NAN, INVALID_INF
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    tolerance_type: str = "ABSOLUTE"
    denominator_floor: float = 1e-3
    unit: str = ""
    timestamp: float = 0.0

    @classmethod
    def compute(
        cls,
        parameter: str,
        expected: Optional[float],
        actual: Optional[float],
        actual_source: str = "NONE",
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        tolerance_type: str = "ABSOLUTE",
        denominator_floor: float = 1e-3,
        unit: str = "",
        timestamp: float = 0.0
    ) -> "ParameterResidual":
        """Safely computes ParameterResidual handling None, zero, NaN, Inf, and invalid units."""
        if expected is None or actual is None:
            return cls(
                parameter=parameter,
                expected=expected,
                actual=actual,
                actual_source=actual_source if actual is not None else "NONE",
                residual=0.0,
                relative_error=0.0,
                status="MISSING",
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                tolerance_type=tolerance_type,
                denominator_floor=denominator_floor,
                unit=unit,
                timestamp=timestamp
            )

        if math.isnan(expected) or math.isnan(actual):
            return cls(
                parameter=parameter,
                expected=expected if not math.isnan(expected) else None,
                actual=actual if not math.isnan(actual) else None,
                actual_source=actual_source if not math.isnan(actual) else "NONE",
                residual=0.0,
                relative_error=0.0,
                status="INVALID_NAN",
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                tolerance_type=tolerance_type,
                denominator_floor=denominator_floor,
                unit=unit,
                timestamp=timestamp
            )

        if math.isinf(expected) or math.isinf(actual):
            return cls(
                parameter=parameter,
                expected=expected if not math.isinf(expected) else None,
                actual=actual if not math.isinf(actual) else None,
                actual_source=actual_source if not math.isinf(actual) else "NONE",
                residual=0.0,
                relative_error=0.0,
                status="INVALID_INF",
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                tolerance_type=tolerance_type,
                denominator_floor=denominator_floor,
                unit=unit,
                timestamp=timestamp
            )

        exp_val = float(expected)
        act_val = float(actual)
        res = act_val - exp_val

        denom = abs(exp_val)
        if denom < denominator_floor:
            denom = denominator_floor

        rel_err = res / denom

        status = "GOOD"
        
        # Evaluate against thresholds
        val_to_check = abs(rel_err) if tolerance_type.upper() == "RELATIVE" else abs(res)

        if critical_threshold is not None and val_to_check > critical_threshold:
            status = "CRITICAL"
        elif warning_threshold is not None and val_to_check > warning_threshold:
            status = "WARNING"

        return cls(
            parameter=parameter,
            expected=exp_val,
            actual=act_val,
            actual_source=actual_source,
            residual=res,
            relative_error=rel_err,
            status=status,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            tolerance_type=tolerance_type,
            denominator_floor=denominator_floor,
            unit=unit,
            timestamp=timestamp
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes ParameterResidual to dictionary."""
        return {
            "parameter": self.parameter,
            "expected": round(self.expected, 4) if self.expected is not None else None,
            "actual": round(self.actual, 4) if self.actual is not None else None,
            "actual_source": self.actual_source,
            "residual": round(self.residual, 4),
            "relative_error": round(self.relative_error, 4),
            "status": self.status,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "denominator_floor": self.denominator_floor,
            "tolerance_type": self.tolerance_type,
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
    
    # Explicit 19 Category C Parameters
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
        """Returns the number of residuals that triggered a WARNING."""
        count = 0
        for attr_name in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                          "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                          "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                          "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
            res = getattr(self, attr_name)
            if res is not None and res.status == "WARNING":
                count += 1
        return count

    @property
    def criticals_count(self) -> int:
        """Returns the number of residuals that triggered a CRITICAL."""
        count = 0
        for attr_name in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                          "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                          "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                          "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
            res = getattr(self, attr_name)
            if res is not None and res.status == "CRITICAL":
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
            "warnings_count": self.warnings_count,
            "criticals_count": self.criticals_count
        }
