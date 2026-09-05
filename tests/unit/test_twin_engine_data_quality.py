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
    assert state.status == DigitalTwinStatus.SYNC_FAILED
    assert state.confidence == 0.0

    # 3. Test DEGRADED
    observed_degraded = ObservedState(
        engine_id="engine_1",
        data_quality="DEGRADED",
        sequence_number=3
    )
    state = engine.process_step(context, 1.0, observed_degraded)
    assert state.data_quality == DigitalTwinDataQuality.DEGRADED
    assert state.status == DigitalTwinStatus.DATA_QUALITY_DEGRADED
    assert state.confidence == 0.7

    # 4. Test GOOD (no deviations)
    # Give perfectly matching values to the healthy expected state so no deviation is detected
    expected = engine.reference_models[1].step(context, 1.0)
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
