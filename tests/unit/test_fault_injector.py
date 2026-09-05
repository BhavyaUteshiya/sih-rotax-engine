import pytest
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.faults.fault_scenario import FaultScenario
from src.digital_twin.faults.fault_injector import FaultInjector

@pytest.fixture
def base_expected():
    """Creates a base healthy expected state for testing."""
    state = HealthyExpectedState(
        timestamp=10.0,
        sequence_number=1,
        engine_id="engine_test",
        aircraft_id="uav_test"
    )
    # Populate dummy values
    state.rpm = 5000.0
    state.map_bar = 1.0
    state.airflow_kg_h = 100.0
    state.indicated_power_kw = 50.0
    state.torque_n_m = 90.0
    state.cht_c = 90.0
    state.oil_temp_c = 85.0
    state.oil_pressure_bar = 4.0
    state.thrust_n = 500.0
    return state

@pytest.fixture
def injector():
    return FaultInjector()

def test_healthy_no_fault(injector, base_expected):
    """Test 1: Healthy/no fault -> outputs unchanged."""
    scenarios = []
    obs = injector.inject(base_expected, scenarios, timestamp=10.0)
    
    assert obs.cht_c == base_expected.cht_c
    assert obs.oil_pressure_bar == base_expected.oil_pressure_bar
    assert obs.torque_n_m == base_expected.torque_n_m
    assert obs.valid_sensors_count == 9  # 9 parameters populated in fixture

def test_cooling_degradation_enabled(injector, base_expected):
    """Test 2: Cooling degradation -> intended direction."""
    scenario = FaultScenario(fault_type="COOLING_DEGRADATION", severity=1.0)
    obs = injector.inject(base_expected, [scenario], timestamp=10.0)
    
    assert obs.cht_c == base_expected.cht_c + 50.0
    assert obs.oil_temp_c == base_expected.oil_temp_c + 20.0

def test_lubrication_degradation_enabled(injector, base_expected):
    """Test 3: Lubrication degradation -> intended direction."""
    scenario = FaultScenario(fault_type="LUBRICATION_DEGRADATION", severity=1.0)
    obs = injector.inject(base_expected, [scenario], timestamp=10.0)
    
    assert obs.oil_pressure_bar == base_expected.oil_pressure_bar - 2.0
    assert obs.oil_temp_c == base_expected.oil_temp_c + 15.0

def test_airflow_restriction_enabled(injector, base_expected):
    """Test 4: Airflow restriction -> intended direction."""
    scenario = FaultScenario(fault_type="AIRFLOW_RESTRICTION", severity=1.0)
    obs = injector.inject(base_expected, [scenario], timestamp=10.0)
    
    assert obs.airflow_kg_h == base_expected.airflow_kg_h * 0.5
    assert obs.map_bar == base_expected.map_bar * 0.6
    assert obs.indicated_power_kw == base_expected.indicated_power_kw * 0.6

def test_torque_degradation_enabled(injector, base_expected):
    """Test 5: Torque degradation -> intended direction."""
    scenario = FaultScenario(fault_type="TORQUE_DEGRADATION", severity=1.0)
    obs = injector.inject(base_expected, [scenario], timestamp=10.0)
    
    assert obs.torque_n_m == base_expected.torque_n_m * 0.7
    assert obs.thrust_n == base_expected.thrust_n * 0.7

def test_severity_scaling(injector, base_expected):
    """Test 6: Severity scaling outputs proportional changes."""
    scenario_half = FaultScenario(fault_type="COOLING_DEGRADATION", severity=0.5)
    obs = injector.inject(base_expected, [scenario_half], timestamp=10.0)
    
    # Half of the 50.0 max increase
    assert obs.cht_c == base_expected.cht_c + 25.0

def test_gradual_degradation(injector, base_expected):
    """Test 7: Gradual degradation linearly increases effect over ramp_duration."""
    scenario = FaultScenario(
        fault_type="LUBRICATION_DEGRADATION", 
        severity=1.0, 
        start_time=10.0, 
        ramp_duration=10.0
    )
    
    # At t=10.0 (start), effect should be 0
    obs_start = injector.inject(base_expected, [scenario], timestamp=10.0)
    assert obs_start.oil_pressure_bar == base_expected.oil_pressure_bar
    
    # At t=15.0 (halfway), effect should be 0.5 * severity
    obs_mid = injector.inject(base_expected, [scenario], timestamp=15.0)
    assert obs_mid.oil_pressure_bar == base_expected.oil_pressure_bar - 1.0
    
    # At t=25.0 (after end), effect should be capped at 1.0 * severity
    obs_end = injector.inject(base_expected, [scenario], timestamp=25.0)
    assert obs_end.oil_pressure_bar == base_expected.oil_pressure_bar - 2.0

def test_instant_fault_activation(injector, base_expected):
    """Test 8: Instant fault activation applies immediately."""
    scenario = FaultScenario(
        fault_type="TORQUE_DEGRADATION", 
        severity=1.0, 
        start_time=15.0, 
        ramp_duration=0.0
    )
    
    # At t=10.0 (before start), no effect
    obs_before = injector.inject(base_expected, [scenario], timestamp=10.0)
    assert obs_before.torque_n_m == base_expected.torque_n_m
    
    # At t=15.0 (at start), full effect applied instantly
    obs_after = injector.inject(base_expected, [scenario], timestamp=15.0)
    assert obs_after.torque_n_m == base_expected.torque_n_m * 0.7

def test_disabled_fault_unchanged(injector, base_expected):
    """Test 9: Disabled fault scenario leaves output unchanged."""
    scenario = FaultScenario(fault_type="COOLING_DEGRADATION", severity=1.0, enabled=False)
    obs = injector.inject(base_expected, [scenario], timestamp=10.0)
    
    assert obs.cht_c == base_expected.cht_c

def test_multiple_simultaneous_faults(injector, base_expected):
    """Test 10: Multiple simultaneous faults stack securely."""
    s1 = FaultScenario(fault_type="COOLING_DEGRADATION", severity=1.0)
    s2 = FaultScenario(fault_type="LUBRICATION_DEGRADATION", severity=1.0)
    
    obs = injector.inject(base_expected, [s1, s2], timestamp=10.0)
    
    # CHT goes up by 50.0
    assert obs.cht_c == base_expected.cht_c + 50.0
    
    # Oil Pressure drops by 2.0
    assert obs.oil_pressure_bar == base_expected.oil_pressure_bar - 2.0
    
    # Oil temp increases from both: +20.0 (cooling) and +15.0 (lube)
    assert obs.oil_temp_c == base_expected.oil_temp_c + 35.0

def test_invalid_severity_clipping(injector, base_expected):
    """Test 13: Invalid severity values are safely clipped between 0.0 and 1.0."""
    scenario_high = FaultScenario(fault_type="COOLING_DEGRADATION", severity=5.0)
    obs_high = injector.inject(base_expected, [scenario_high], timestamp=10.0)
    # Effect should be capped at 1.0 (50.0 total)
    assert obs_high.cht_c == base_expected.cht_c + 50.0
    
    scenario_neg = FaultScenario(fault_type="COOLING_DEGRADATION", severity=-1.0)
    obs_neg = injector.inject(base_expected, [scenario_neg], timestamp=10.0)
    # Effect should be capped at 0.0
    assert obs_neg.cht_c == base_expected.cht_c

def test_lubrication_pressure_clipping(injector, base_expected):
    """Test 14: Ensure oil pressure is naturally bounded at 0.0."""
    # Force baseline oil pressure lower
    base_expected.oil_pressure_bar = 1.0
    scenario = FaultScenario(fault_type="LUBRICATION_DEGRADATION", severity=1.0) # Reduces by 2.0
    
    obs = injector.inject(base_expected, [scenario], timestamp=10.0)
    # Should not fall below 0.0
    assert obs.oil_pressure_bar == 0.0
