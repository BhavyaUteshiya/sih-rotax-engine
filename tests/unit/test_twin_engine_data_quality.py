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
        data_quality="INSUFFICIENT_DATA"
    )
    state = engine.process_step(context, 1.0, observed_insufficient)
    assert state.data_quality == DigitalTwinDataQuality.INSUFFICIENT_DATA
    assert state.status == DigitalTwinStatus.INSUFFICIENT_DATA
    assert state.confidence == 0.0

    # 2. Test INVALID
    observed_invalid = ObservedState(
        engine_id="engine_1",
        data_quality="INVALID"
    )
    state = engine.process_step(context, 1.0, observed_invalid)
    assert state.data_quality == DigitalTwinDataQuality.INVALID
    assert state.status == DigitalTwinStatus.DATA_QUALITY_DEGRADED
    assert state.confidence == 0.5

    # 3. Test DEGRADED
    observed_degraded = ObservedState(
        engine_id="engine_1",
        data_quality="DEGRADED"
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
    assert state.data_quality == DigitalTwinDataQuality.GOOD
    assert state.status == DigitalTwinStatus.SYNCHRONIZED
    assert state.confidence == 1.0
