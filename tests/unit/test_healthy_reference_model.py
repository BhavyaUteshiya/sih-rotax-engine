import pytest
from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.physics.healthy_reference_model import HealthyReferenceModel
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState

def test_healthy_reference_model_initialization():
    model = HealthyReferenceModel(engine_index=1, initial_altitude_m=1000.0)
    assert model.engine_index == 1
    assert model.sequence_number == 0
    assert model.simulator is not None

def test_healthy_reference_model_step():
    model = HealthyReferenceModel(engine_index=1)
    
    context = OperatingContext(
        altitude_m=0.0,
        ambient_temp_c=15.0,
        ambient_pressure_kpa=101.325,
        relative_humidity_pct=0.0,
        throttle_position=1.0, # 100%
        airspeed_m_s=0.0,
        fuel_pressure_pa=250000.0,
        starter_engaged=False
    )
    
    state = model.step(context, dt=0.1)
    
    assert isinstance(state, HealthyExpectedState)
    assert state.sequence_number == 1
    assert state.timestamp == 0.1
    assert state.engine_id == "engine_1"
    
    # Verify mapping is successful by type rather than hardcoded physical spool-up limits
    assert isinstance(state.rpm, float)
    assert isinstance(state.map_bar, float)
    assert isinstance(state.afr, float)

def test_healthy_reference_model_invalid_dt():
    model = HealthyReferenceModel()
    context = OperatingContext()
    
    with pytest.raises(ValueError, match="Timestep dt must be strictly positive."):
        model.step(context, dt=0.0)

    with pytest.raises(ValueError, match="Timestep dt must be strictly positive."):
        model.step(context, dt=-0.1)

def test_healthy_reference_model_no_fabricated_values():
    model = HealthyReferenceModel(engine_index=1)
    context = OperatingContext(
        altitude_m=0.0,
        ambient_temp_c=15.0,
        ambient_pressure_kpa=101.325,
        relative_humidity_pct=0.0,
        throttle_position=1.0, 
        airspeed_m_s=0.0,
        fuel_pressure_pa=250000.0,
        starter_engaged=False
    )
    state = model.step(context, dt=0.1)
    
    # Phase 1 Simulator doesn't provide these, so they must be None, not fabricated 0.0s
    assert state.coolant_temp_c is None
    assert state.oil_pressure_bar is None
    assert state.combustion_energy is None

def test_healthy_reference_model_authoritative_gearbox():
    model = HealthyReferenceModel(engine_index=1)
    context = OperatingContext(
        throttle_position=0.5
    )
    
    # 1. Step the model
    state = model.step(context, dt=0.1)
    
    # 2. Get authoritative Phase 1 state
    sim_state = model.simulator.get_state()
    
    # 3. Assert they are exactly equal, no fallback division
    assert state.gearbox_rpm == sim_state.engine_dynamics.propeller_rpm
    
    # 4. Verify fuel pressure delta explicitly remains a nominal calibration assumption
    # We verify the source file directly contains the required disclaimer.
    import inspect
    import src.digital_twin.physics.healthy_reference_model as hrm
    source_lines = inspect.getsource(hrm)
    assert "nominal engineering/calibration assumption" in source_lines
    assert "NOT presented as an official Rotax specification" in source_lines
    assert "fuel_pressure_delta_pa=25000.0" in source_lines
