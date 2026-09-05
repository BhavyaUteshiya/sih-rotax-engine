"""
Unit tests for Phase 2A Digital Twin Data Contracts.
SIH26054 — Digital Twin Core.
"""

import pytest

from src.digital_twin.models import (
    OperatingContext,
    HealthState,
    ObservedState,
    HealthyExpectedState,
    EstimatedActualState,
    ResidualState,
    ParameterResidual,
    DigitalTwinState,
    DigitalTwinStatus,
    DigitalTwinDataQuality
)


def test_default_state_validity():
    """Test that all states can be instantiated with safe defaults."""
    op_ctx = OperatingContext()
    health = HealthState()
    obs = ObservedState()
    exp = HealthyExpectedState()
    est = EstimatedActualState()
    res = ResidualState()
    dt = DigitalTwinState()

    assert op_ctx.altitude_m == 0.0
    assert health.turbo_efficiency_degradation == 1.0
    assert obs.rpm is None  # Observations default to missing
    assert exp.rpm is None  # Healthy expectations default to missing until explicitly set
    assert est.rpm == 0.0   # Estimations default to 0.0
    assert res.rpm is None
    assert dt.status == DigitalTwinStatus.WAITING_FOR_DATA


def test_complete_state_construction_and_isolation():
    """Test full construction and ensure states are isolated (independent objects)."""
    op_ctx = OperatingContext(altitude_m=1000.0, throttle_position=0.8)
    health = HealthState(active_faults=["SENSOR_DEGRADED"])
    
    obs = ObservedState(rpm=5500.0, map_bar=1.1, data_quality="GOOD")
    exp = HealthyExpectedState(rpm=5520.0, map_bar=1.12)
    est = EstimatedActualState(rpm=5510.0, map_bar=1.11, estimation_confidence=0.95)
    
    res = ResidualState(
        rpm=ParameterResidual.compute("rpm", exp.rpm, obs.rpm, warning_threshold=50.0, critical_threshold=100.0, denominator_floor=1.0),
        map_bar=ParameterResidual.compute("map_bar", exp.map_bar, obs.map_bar, warning_threshold=0.05, critical_threshold=0.1, denominator_floor=0.1)
    )

    dt = DigitalTwinState(
        timestamp=1.5,
        engine_id="eng_test_1",
        aircraft_id="uav_alpha",
        operating_context=op_ctx,
        observed_state=obs,
        healthy_expected_state=exp,
        estimated_actual_state=est,
        residual_state=res,
        health_state=health,
        data_quality=DigitalTwinDataQuality.DEGRADED,
        confidence=0.9
    )

    assert dt.timestamp == 1.5
    assert dt.engine_id == "eng_test_1"
    
    # Verify independent separation
    assert dt.observed_state.rpm == 5500.0
    assert dt.healthy_expected_state.rpm == 5520.0
    assert dt.estimated_actual_state.rpm == 5510.0
    
    assert dt.observed_state is not dt.healthy_expected_state
    assert dt.estimated_actual_state is not dt.healthy_expected_state

    # Verify residuals
    assert res.rpm.residual == (5500.0 - 5520.0) # -20.0
    assert res.rpm.status == "GOOD"
    assert res.map_bar.residual == pytest.approx(1.1 - 1.12)
    
    # Confidence and Data Quality bounds
    assert dt.data_quality == DigitalTwinDataQuality.DEGRADED
    assert dt.confidence == 0.9


def test_serialization_round_trip():
    """Test serialization to dict does not lose keys."""
    dt = DigitalTwinState(
        operating_context=OperatingContext(airspeed_m_s=30.0),
        health_state=HealthState(turbo_efficiency_degradation=0.98),
        observed_state=ObservedState(rpm=5000.0),
        healthy_expected_state=HealthyExpectedState(rpm=5000.0),
        estimated_actual_state=EstimatedActualState(rpm=5000.0),
        residual_state=ResidualState(
            rpm=ParameterResidual.compute("rpm", 5000.0, 5000.0)
        )
    )

    dt_dict = dt.to_dict()
    
    assert dt_dict["timestamp"] == 0.0
    assert dt_dict["engine_id"] == "engine_1"
    assert "operating_context" in dt_dict
    assert "health_state" in dt_dict
    assert "observed_state" in dt_dict
    assert "healthy_expected_state" in dt_dict
    assert "estimated_actual_state" in dt_dict
    assert "residual_state" in dt_dict
    
    assert dt_dict["operating_context"]["airspeed_m_s"] == 30.0
    assert dt_dict["health_state"]["turbo_efficiency_degradation"] == 0.98
    assert dt_dict["observed_state"]["rpm"] == 5000.0
    assert dt_dict["healthy_expected_state"]["rpm"] == 5000.0
    assert dt_dict["estimated_actual_state"]["rpm"] == 5000.0
    
    assert "rpm" in dt_dict["residual_state"]["residuals"]
    assert dt_dict["residual_state"]["residuals"]["rpm"]["residual"] == 0.0
    assert dt_dict["residual_state"]["warnings_count"] == 0


def test_residual_invalid_computation():
    """Test ParameterResidual handles missing/nan data appropriately."""
    missing = ParameterResidual.compute("rpm", 5000.0, None, 50.0, 100.0, 1.0)
    assert missing.status == "MISSING"
    assert missing.residual == 0.0

    missing_exp = ParameterResidual.compute("rpm", None, 5000.0, 50.0, 100.0, 1.0)
    assert missing_exp.status == "MISSING"

    invalid = ParameterResidual.compute("rpm", 5000.0, float('nan'), 50.0, 100.0, 1.0)
    assert invalid.status == "INVALID_NAN"
    
    invalid_inf = ParameterResidual.compute("rpm", float('inf'), 5000.0, 50.0, 100.0, 1.0)
    assert invalid_inf.status == "INVALID_INF"


def test_engine_identity_isolation():
    """Test that engine identities are properly assigned and isolated."""
    dt1 = DigitalTwinState(engine_id="L_engine")
    dt2 = DigitalTwinState(engine_id="R_engine")

    assert dt1.engine_id == "L_engine"
    assert dt2.engine_id == "R_engine"
    assert dt1.engine_id != dt2.engine_id
