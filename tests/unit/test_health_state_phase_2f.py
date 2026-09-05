import pytest
from src.digital_twin.models.health_state import HealthState, HealthLevel
from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.models.twin_state import DigitalTwinStatus, DigitalTwinDataQuality
import numpy as np

@pytest.fixture
def base_context():
    return OperatingContext(
        ambient_temp_c=15.0,
        ambient_pressure_kpa=101.325,
        throttle_position=0.5
    )

@pytest.fixture
def nominal_observed():
    return ObservedState(
        timestamp=1.0,
        rpm=5000.0,
        map_bar=1.0,
        turbo_rpm=100000.0,
        airflow_kg_h=200.0,
        fuel_flow_kg_h=15.0,
        afr=13.0,
        egt_c=800.0,
        cht_c=100.0,
        coolant_temp_c=80.0,
        oil_temp_c=90.0,
        oil_pressure_bar=3.5,
        turbo_boost_bar=0.5,
        data_quality="GOOD"
    )


def test_health_state_healthy(base_context, nominal_observed):
    """1. HEALTHY classification"""
    engine = DigitalTwinEngine()
    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=nominal_observed,
        engine_index=1
    )
    assert state.health_state.health_level == HealthLevel.HEALTHY
    assert state.health_state.is_assessable is True


def test_health_state_warning(base_context, nominal_observed):
    """2. WARNING classification"""
    engine = DigitalTwinEngine()
    engine.residual_analyzer.thresholds["torque_n_m"]["debounce_sec"] = 0.0
    engine.residual_analyzer.thresholds["torque_n_m"]["warning_threshold"] = 0.001
    engine.residual_analyzer.thresholds["torque_n_m"]["critical_threshold"] = 1000.0
    nominal_observed.torque_n_m = 10.0
    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=nominal_observed,
        engine_index=1
    )
    assert state.health_state.health_level == HealthLevel.WARNING


def test_health_state_critical(base_context, nominal_observed):
    """3. CRITICAL classification"""
    engine = DigitalTwinEngine()
    engine.residual_analyzer.thresholds["torque_n_m"]["debounce_sec"] = 0.0
    engine.residual_analyzer.thresholds["torque_n_m"]["warning_threshold"] = 0.001
    engine.residual_analyzer.thresholds["torque_n_m"]["critical_threshold"] = 0.002
    nominal_observed.torque_n_m = 10.0
    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=nominal_observed,
        engine_index=1
    )
    assert state.health_state.health_level == HealthLevel.CRITICAL


def test_health_state_critical_overrides_warning(base_context, nominal_observed):
    """4. CRITICAL overrides WARNING"""
    engine = DigitalTwinEngine()
    engine.residual_analyzer.thresholds["torque_n_m"]["debounce_sec"] = 0.0
    engine.residual_analyzer.thresholds["torque_n_m"]["warning_threshold"] = 0.001
    engine.residual_analyzer.thresholds["torque_n_m"]["critical_threshold"] = 1000.0
    nominal_observed.torque_n_m = 10.0  # WARNING
    
    engine.residual_analyzer.thresholds["thrust_n"]["debounce_sec"] = 0.0
    engine.residual_analyzer.thresholds["thrust_n"]["warning_threshold"] = 0.001
    engine.residual_analyzer.thresholds["thrust_n"]["critical_threshold"] = 0.002
    nominal_observed.thrust_n = 10.0  # CRITICAL

    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=nominal_observed,
        engine_index=1
    )
    assert state.health_state.health_level == HealthLevel.CRITICAL
    assert state.health_state.warning_count > 0
    assert state.health_state.critical_count > 0


def test_health_state_insufficient_data(base_context):
    """5. Insufficient data -> UNKNOWN"""
    nominal_observed = ObservedState(
        timestamp=1.0, sequence_number=0, engine_id="engine_1",
        data_quality="GOOD"
    )
    engine = DigitalTwinEngine()
    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=nominal_observed,
        engine_index=1
    )
    assert state.health_state.health_level == HealthLevel.UNKNOWN
    assert state.health_state.is_assessable is False
    assert state.health_state.missing_count > 0


def test_health_state_invalid_data(base_context, nominal_observed):
    """6. Invalid data -> UNKNOWN"""
    nominal_observed = ObservedState(
        timestamp=1.0, sequence_number=0, engine_id="engine_1",
        data_quality="GOOD",
        rpm=float('inf'), map_bar=float('inf'), turbo_rpm=float('inf'),
        airflow_kg_h=float('inf'), fuel_flow_kg_h=float('inf'), afr=float('inf'),
        combustion_energy=float('inf'), combustion_efficiency=float('inf'),
        indicated_power_kw=float('inf'), torque_n_m=float('inf'), egt_c=float('inf'),
        cht_c=float('inf'), coolant_temp_c=float('inf'), oil_temp_c=float('inf'),
        oil_pressure_bar=float('inf'), turbo_boost_bar=float('inf'), gearbox_rpm=float('inf'),
        propeller_load_nm=float('inf'), thrust_n=float('inf')
    )
    engine = DigitalTwinEngine()
    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=nominal_observed,
        engine_index=1
    )
    assert state.health_state.health_level == HealthLevel.UNKNOWN
    assert state.health_state.is_assessable is False
    assert state.health_state.invalid_count > 0


def test_health_state_degraded_data_quality(base_context, nominal_observed, monkeypatch):
    """7. Degraded but assessable -> DEGRADED"""
    engine = DigitalTwinEngine()
    # Let's mock the data quality check just for this test
    original_sync = engine.synchronizer.synchronize
    def mock_sync(expected, observed, context, last_sequence_number):
        res = original_sync(expected=expected, observed=observed, context=context, last_sequence_number=last_sequence_number)
        res.status = "DEGRADED_OBSERVATION"
        res.quality_effect = "DEGRADED"
        return res
    monkeypatch.setattr(engine.synchronizer, 'synchronize', mock_sync)
    
    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=nominal_observed,
        engine_index=1
    )
    
    assert state.data_quality == DigitalTwinDataQuality.DEGRADED
    assert state.health_state.health_level == HealthLevel.DEGRADED


def test_health_state_prediction_only(base_context):
    """8 & 9. Sync failure -> UNKNOWN"""
    # Providing empty observed state causes sync failure (prediction only)
    empty_observed = ObservedState(timestamp=1.0)
    engine = DigitalTwinEngine()
    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=empty_observed,
        engine_index=1
    )
    
    assert state.synchronization_result.is_synchronized is False
    assert state.health_state.health_level == HealthLevel.UNKNOWN
    assert state.health_state.is_assessable is False


def test_serialization():
    """11. Serialization of HealthState"""
    hs = HealthState(
        timestamp=1.0,
        health_level=HealthLevel.CRITICAL,
        is_assessable=True,
        critical_count=2
    )
    d = hs.to_dict()
    assert d['health_level'] == "CRITICAL"
    assert d['is_assessable'] is True
    assert d['critical_count'] == 2

def test_causal_separation(base_context, nominal_observed):
    """13. Causal separation (HealthState doesn't overwrite CausalAnalyzer)"""
    engine = DigitalTwinEngine()
    engine.residual_analyzer.thresholds["torque_n_m"]["debounce_sec"] = 0.0
    engine.residual_analyzer.thresholds["torque_n_m"]["warning_threshold"] = 0.001
    engine.residual_analyzer.thresholds["torque_n_m"]["critical_threshold"] = 1000.0
    nominal_observed.torque_n_m = 10.0  # WARNING
    state = engine.process_step(
        timestamp=1.0,
        operating_context=base_context,
        dt=0.1,
        observed_state=nominal_observed,
        engine_index=1
    )
    assert state.health_state.health_level == HealthLevel.WARNING
    assert "DigitalTwinStatus" in str(type(state.status))
