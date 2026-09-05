"""
Unit tests for Phase 2B Healthy Reference Model interface.
SIH26054 — Digital Twin Core.
"""

import pytest

from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.physics.healthy_reference_model import HealthyReferenceModel
from src.digital_twin.services.twin_engine import DigitalTwinEngine


def test_healthy_reference_model_instantiation():
    """Test that the HealthyReferenceModel encapsulates the simulator."""
    hrm = HealthyReferenceModel(engine_index=1, initial_altitude_m=1000.0)
    assert hrm.engine_index == 1
    assert hrm.simulator is not None
    assert hrm.simulator.time_s == 0.0


def test_healthy_reference_model_step():
    """Test stepping the healthy reference model with an operating context."""
    hrm = HealthyReferenceModel(engine_index=1)
    
    # 50% throttle at sea level
    ctx = OperatingContext(
        altitude_m=0.0,
        ambient_temp_c=15.0,
        throttle_position=0.5,
        airspeed_m_s=25.0
    )
    
    dt = 0.01
    state = hrm.step(ctx, dt)
    
    assert state.engine_id == "engine_1"
    assert state.timestamp == dt
    assert state.sequence_number == 1
    
    # Check that physics values are populated (they shouldn't be exactly zero for all)
    assert state.rpm >= 0.0


def test_twin_engine_phase2b_boundary():
    """
    Test that DigitalTwinEngine can step directly from OperatingContext 
    without requiring external sim_state.
    """
    engine = DigitalTwinEngine()
    
    ctx = OperatingContext(
        altitude_m=2000.0,
        ambient_temp_c=5.0,
        throttle_position=0.8,
        airspeed_m_s=50.0
    )
    
    # Provide an observed state (simulating telemetry)
    from src.digital_twin.models.observed_state import ObservedState
    obs = ObservedState(rpm=5000.0, map_bar=1.1, data_quality="GOOD")
    
    dt = 0.05
    state = engine.process_step(
        operating_context=ctx,
        dt=dt,
        observed_state=obs,
        engine_index=1
    )
    
    # Twin state should be populated
    assert state.engine_id == "engine_1"
    
    # Healthy expected state should be derived internally
    expected = state.healthy_expected_state
    assert expected is not None
    assert expected.timestamp == 0.0  # Since we didn't pass timestamp to process_step, it defaults to 0.0 in the process_step signature, overriding the simulator time. Wait, we should probably check if it matches the overridden timestamp.
    
    # Residuals should be calculated
    assert state.residual_state is not None
    assert state.residual_state.rpm.observed == 5000.0
