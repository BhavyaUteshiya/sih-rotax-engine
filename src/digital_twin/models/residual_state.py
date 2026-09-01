"""
Residual State Model — Residuals (Observed - Expected) and Relative Deviation Metrics.
SIH26054 — Module 03 Digital Twin Core.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    unit: str = ""
    timestamp: float = 0.0

    @classmethod
    def compute(
        cls,
        parameter: str,
        expected: Optional[float],
        observed: Optional[float],
        threshold: Optional[float] = None,
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
        if threshold is not None and abs(res) > threshold:
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
    Container storing ParameterResidual entries across all evaluated engine/aircraft parameters.
    """
    timestamp: float = 0.0
    sequence_number: int = 0
    engine_id: str = "engine_1"
    residuals: Dict[str, ParameterResidual] = field(default_factory=dict)
    warnings_count: int = 0

    def add_residual(self, res: ParameterResidual) -> None:
        """Adds or updates a ParameterResidual entry."""
        self.residuals[res.parameter] = res
        if res.warning_triggered:
            self.warnings_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Serializes ResidualState to dictionary."""
        return {
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "engine_id": self.engine_id,
            "residuals": {k: v.to_dict() for k, v in self.residuals.items()},
            "warnings_count": sum(1 for v in self.residuals.values() if v.warning_triggered)
        }
