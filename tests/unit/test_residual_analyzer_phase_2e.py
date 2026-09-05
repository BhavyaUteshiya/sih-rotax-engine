"""
Phase 2E Regression Tests for Residual Analyzer.
Ensures correct estimated vs observed source selection and relative error calculations.
"""

import math
import pytest
from src.digital_twin.analysis.residual_analyzer import ResidualAnalyzer
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.estimated_actual_state import EstimatedActualState
from src.digital_twin.models.residual_state import ParameterResidual


def test_actual_source_non_ukf_field():
    """
    Test CRITICAL ISSUE 1.A: A non-UKF field (oil_pressure_bar) must not use
    the estimated pass-through value. It must fall back to observed.
    """
    analyzer = ResidualAnalyzer(config_path="configs/digital_twin_config.yaml")
    
    expected = HealthyExpectedState(oil_pressure_bar=4.0)
    observed = ObservedState(oil_pressure_bar=3.0)
    estimated = EstimatedActualState(oil_pressure_bar=4.0, is_prediction_only=False)
    
    res_state = analyzer.analyze(expected, observed, estimated)
    
    res = res_state.oil_pressure_bar
    assert res is not None
    assert res.actual == 3.0
    assert res.actual_source == "OBSERVED"
    assert math.isclose(res.residual, -1.0)


def test_actual_source_ukf_field():
    """
    Test CRITICAL ISSUE 1.B: A UKF field (rpm) must use the estimated value.
    """
    analyzer = ResidualAnalyzer(config_path="configs/digital_twin_config.yaml")
    
    expected = HealthyExpectedState(rpm=5000.0)
    observed = ObservedState(rpm=4950.0)
    estimated = EstimatedActualState(rpm=4900.0, is_prediction_only=False)
    
    res_state = analyzer.analyze(expected, observed, estimated)
    
    res = res_state.rpm
    assert res is not None
    assert res.actual == 4900.0
    assert res.actual_source == "ESTIMATED"
    assert math.isclose(res.residual, -100.0)


def test_actual_source_prediction_only():
    """
    Test CRITICAL ISSUE 1.C: Prediction-only estimated state must fallback to observed.
    """
    analyzer = ResidualAnalyzer(config_path="configs/digital_twin_config.yaml")
    
    expected = HealthyExpectedState(rpm=5000.0)
    observed = ObservedState(rpm=4950.0)
    estimated = EstimatedActualState(rpm=4900.0, is_prediction_only=True)
    
    res_state = analyzer.analyze(expected, observed, estimated)
    
    res = res_state.rpm
    assert res is not None
    assert res.actual == 4950.0
    assert res.actual_source == "OBSERVED"
    assert math.isclose(res.residual, -50.0)


def test_actual_source_missing():
    """
    Test CRITICAL ISSUE 1.D: No estimated/no observed -> MISSING
    """
    analyzer = ResidualAnalyzer(config_path="configs/digital_twin_config.yaml")
    
    expected = HealthyExpectedState(rpm=5000.0)
    observed = ObservedState(rpm=None)
    estimated = EstimatedActualState(rpm=None, is_prediction_only=False)
    
    res_state = analyzer.analyze(expected, observed, estimated)
    
    res = res_state.rpm
    assert res is not None
    assert res.actual is None
    assert res.actual_source == "NONE"
    assert res.status == "MISSING"


def test_relative_error_formula():
    """
    Test CRITICAL ISSUE 2: Relative error must be non-negative.
    Positive residual, negative residual, and zero-protection.
    """
    # Positive residual
    p_res = ParameterResidual.compute(
        parameter="rpm",
        expected=5000.0,
        actual=5100.0,
        denominator_floor=1e-3
    )
    assert math.isclose(p_res.residual, 100.0)
    assert math.isclose(p_res.relative_error, 100.0 / 5000.0)
    assert p_res.relative_error >= 0.0

    # Negative residual
    n_res = ParameterResidual.compute(
        parameter="rpm",
        expected=5000.0,
        actual=4900.0,
        denominator_floor=1e-3
    )
    assert math.isclose(n_res.residual, -100.0)
    assert math.isclose(n_res.relative_error, 100.0 / 5000.0)
    assert n_res.relative_error >= 0.0

    # Denominator floor (Expected near zero)
    z_res = ParameterResidual.compute(
        parameter="rpm",
        expected=0.0,
        actual=10.0,
        denominator_floor=1e-3
    )
    assert math.isclose(z_res.residual, 10.0)
    assert math.isclose(z_res.relative_error, 10.0 / 1e-3)
    assert z_res.relative_error >= 0.0

