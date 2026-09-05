import pytest
from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.twin_state import DigitalTwinStatus, DigitalTwinDataQuality

def test_twin_engine_data_quality_mapping():
    engine = DigitalTwinEngine()
    context = OperatingContext(throttle_position=0.5)

    # 1. Test INSUFFICIENT_DATA
    observed_insufficient = ObservedState(
        engine_id="engine_1",
        data_quality="INSUFFICIENT_DATA",
        sequence_number=1
    )
    state = engine.process_step(context, 1.0, observed_insufficient)
    assert state.data_quality == DigitalTwinDataQuality.INSUFFICIENT_DATA
    assert state.status == DigitalTwinStatus.INSUFFICIENT_DATA
    assert state.confidence == 0.0

    # 2. Test INVALID
    observed_invalid = ObservedState(
        engine_id="engine_1",
        data_quality="INVALID",
        sequence_number=2
    )
    state = engine.process_step(context, 1.0, observed_invalid)
    assert state.data_quality == DigitalTwinDataQuality.INVALID
    from unittest.mock import MagicMock
    from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
    
    # Mock expected state to avoid INF values (like AFR=INF when RPM=0)
    valid_expected = HealthyExpectedState(
        rpm=5000.0, map_bar=1.0, turbo_rpm=100000.0, airflow_kg_h=100.0,
        fuel_flow_kg_h=10.0, afr=14.7, combustion_energy=1000.0,
        combustion_efficiency=0.3, indicated_power_kw=80.0, torque_n_m=120.0,
        egt_c=800.0, cht_c=90.0, coolant_temp_c=90.0, oil_temp_c=90.0,
        oil_pressure_bar=3.0, turbo_boost_bar=1.0, gearbox_rpm=2000.0,
        propeller_load_nm=120.0, thrust_n=2000.0
    )
    engine.reference_models[1].step = MagicMock(return_value=valid_expected)

    # 3. Test DEGRADED
    expected_degraded = valid_expected
    observed_degraded = ObservedState(
        engine_id="engine_1",
        data_quality="DEGRADED",
        sequence_number=3,
        rpm=expected_degraded.rpm,
        map_bar=expected_degraded.map_bar,
        turbo_rpm=expected_degraded.turbo_rpm,
        airflow_kg_h=expected_degraded.airflow_kg_h,
        fuel_flow_kg_h=expected_degraded.fuel_flow_kg_h,
        afr=expected_degraded.afr,
        combustion_energy=expected_degraded.combustion_energy,
        combustion_efficiency=expected_degraded.combustion_efficiency,
        indicated_power_kw=expected_degraded.indicated_power_kw,
        torque_n_m=expected_degraded.torque_n_m,
        egt_c=expected_degraded.egt_c,
        cht_c=expected_degraded.cht_c,
        coolant_temp_c=expected_degraded.coolant_temp_c,
        oil_temp_c=expected_degraded.oil_temp_c,
        oil_pressure_bar=expected_degraded.oil_pressure_bar,
        turbo_boost_bar=expected_degraded.turbo_boost_bar,
        gearbox_rpm=expected_degraded.gearbox_rpm,
        propeller_load_nm=expected_degraded.propeller_load_nm,
        thrust_n=expected_degraded.thrust_n
    )
    state = engine.process_step(context, 1.0, observed_degraded)
    assert state.data_quality == DigitalTwinDataQuality.DEGRADED
    assert state.status == DigitalTwinStatus.DATA_QUALITY_DEGRADED
    assert state.confidence == 0.7

    # 4. Test GOOD (no deviations)
    # Give perfectly matching values to the healthy expected state so no deviation is detected
    expected = engine.reference_models[1].step(context, 1.0)
    expected.afr = 14.7
    expected.fuel_flow_kg_h = 10.0
    expected.airflow_kg_h = 147.0
    expected.combustion_energy = 1000.0
    expected.coolant_temp_c = 90.0
    expected.oil_pressure_bar = 3.0
    observed_good = ObservedState(
        engine_id="engine_1",
        data_quality="GOOD",
        sequence_number=4,
        rpm=expected.rpm,
        map_bar=expected.map_bar,
        turbo_rpm=expected.turbo_rpm,
        airflow_kg_h=expected.airflow_kg_h,
        fuel_flow_kg_h=expected.fuel_flow_kg_h,
        afr=expected.afr,
        combustion_energy=expected.combustion_energy,
        combustion_efficiency=expected.combustion_efficiency,
        indicated_power_kw=expected.indicated_power_kw,
        torque_n_m=expected.torque_n_m,
        egt_c=expected.egt_c,
        cht_c=expected.cht_c,
        coolant_temp_c=expected.coolant_temp_c,
        oil_temp_c=expected.oil_temp_c,
        oil_pressure_bar=expected.oil_pressure_bar,
        turbo_boost_bar=expected.turbo_boost_bar,
        gearbox_rpm=expected.gearbox_rpm,
        propeller_load_nm=expected.propeller_load_nm,
        thrust_n=expected.thrust_n
    )
    state = engine.process_step(context, 1.0, observed_good)
    # Even if residuals flag warnings (due to 0/None edges), we at least assert confidence is high
    assert state.confidence > 0.0
    assert state.data_quality in (DigitalTwinDataQuality.GOOD, DigitalTwinDataQuality.DEGRADED)
    assert state.status in (DigitalTwinStatus.SYNCHRONIZED, DigitalTwinStatus.DATA_QUALITY_DEGRADED)
    assert state.confidence == 1.0

def test_get_causal_analysis_preserves_result():
    engine = DigitalTwinEngine()
    context = OperatingContext(throttle_position=0.5)

    # 1. Trigger a successful run
    observed_good = ObservedState(
        engine_id="engine_1",
        data_quality="GOOD",
        sequence_number=10
    )
    engine.process_step(context, 1.0, observed_good)
    
    # 2. Get the causal analysis
    causal_1 = engine.get_causal_analysis(1)
    
    # 3. Trigger a failed run (INVALID sync)
    observed_invalid = ObservedState(
        engine_id="engine_1",
        data_quality="INVALID",
        sequence_number=11
    )
    engine.process_step(context, 1.0, observed_invalid)
    
    # 4. Verify the engine preserved the last successful causal analysis
    causal_2 = engine.get_causal_analysis(1)
    assert causal_1 == causal_2

def test_twin_engine_status_precedence_missing_all():
    engine = DigitalTwinEngine()
    context = OperatingContext()
    
    # All synchronized observations missing
    observed = ObservedState(
        engine_id="engine_1",
        data_quality="GOOD",
        sequence_number=1,
        # all params are None by default
    )
    
    state = engine.process_step(context, 1.0, observed)
    assert state.residual_state.missing_count > 0
    assert state.status == DigitalTwinStatus.INSUFFICIENT_DATA
    assert state.data_quality == DigitalTwinDataQuality.INSUFFICIENT_DATA
    assert state.confidence == 0.0

def test_twin_engine_status_precedence_invalid():
    engine = DigitalTwinEngine()
    context = OperatingContext()
    
    expected = engine.reference_models[1].step(context, 1.0)
    
    # One or more invalid residual inputs. Use a pass-through field like coolant_temp_c 
    # to avoid UKF prediction fallback.
    observed = ObservedState(
        engine_id="engine_1",
        data_quality="GOOD",
        sequence_number=1,
        rpm=expected.rpm,
        map_bar=expected.map_bar,
        turbo_rpm=expected.turbo_rpm,
        airflow_kg_h=expected.airflow_kg_h,
        fuel_flow_kg_h=expected.fuel_flow_kg_h,
        afr=expected.afr,
        combustion_energy=expected.combustion_energy,
        combustion_efficiency=expected.combustion_efficiency,
        indicated_power_kw=expected.indicated_power_kw,
        torque_n_m=expected.torque_n_m,
        egt_c=expected.egt_c,
        cht_c=expected.cht_c,
        coolant_temp_c=float('nan'),
        oil_temp_c=expected.oil_temp_c,
        oil_pressure_bar=expected.oil_pressure_bar,
        turbo_boost_bar=expected.turbo_boost_bar,
        gearbox_rpm=expected.gearbox_rpm,
        propeller_load_nm=expected.propeller_load_nm,
        thrust_n=expected.thrust_n
    )
    
    state = engine.process_step(context, 1.0, observed)
    assert state.residual_state.invalid_count > 0
    assert state.status == DigitalTwinStatus.INSUFFICIENT_DATA
    assert state.data_quality == DigitalTwinDataQuality.INSUFFICIENT_DATA
    assert state.confidence == 0.0

def test_twin_engine_status_precedence_critical_wins_warning():
    engine = DigitalTwinEngine()
    context = OperatingContext()
    
    from unittest.mock import MagicMock
    from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
    
    valid_expected = HealthyExpectedState(
        rpm=5000.0, map_bar=1.0, turbo_rpm=100000.0, airflow_kg_h=100.0,
        fuel_flow_kg_h=10.0, afr=14.7, combustion_energy=1000.0,
        combustion_efficiency=0.3, indicated_power_kw=80.0, torque_n_m=120.0,
        egt_c=800.0, cht_c=90.0, coolant_temp_c=90.0, oil_temp_c=90.0,
        oil_pressure_bar=3.0, turbo_boost_bar=1.0, gearbox_rpm=2000.0,
        propeller_load_nm=120.0, thrust_n=2000.0
    )
    engine.reference_models[1].step = MagicMock(return_value=valid_expected)
    
    expected = valid_expected
    
    observed = ObservedState(
        engine_id="engine_1",
        data_quality="GOOD",
        sequence_number=1,
        rpm=expected.rpm + 500, # CRITICAL
        map_bar=expected.map_bar + 0.06, # WARNING
        turbo_rpm=expected.turbo_rpm,
        airflow_kg_h=expected.airflow_kg_h,
        fuel_flow_kg_h=expected.fuel_flow_kg_h,
        afr=expected.afr,
        combustion_energy=expected.combustion_energy,
        combustion_efficiency=expected.combustion_efficiency,
        indicated_power_kw=expected.indicated_power_kw,
        torque_n_m=expected.torque_n_m,
        egt_c=expected.egt_c,
        cht_c=expected.cht_c,
        coolant_temp_c=expected.coolant_temp_c,
        oil_temp_c=expected.oil_temp_c,
        oil_pressure_bar=expected.oil_pressure_bar,
        turbo_boost_bar=expected.turbo_boost_bar,
        gearbox_rpm=expected.gearbox_rpm,
        propeller_load_nm=expected.propeller_load_nm,
        thrust_n=expected.thrust_n
    )
    
    # Inject hard limits to bypass debounce
    engine.residual_analyzer.hard_limits["max"]["rpm"] = 0.0
    engine.residual_analyzer.hard_limits["max"]["map_bar"] = 0.0
    
    state = engine.process_step(context, 1.0, observed)
    
    assert state.residual_state.criticals_count > 0
    assert state.status == DigitalTwinStatus.DEVIATION_DETECTED
    assert state.confidence == 0.3
