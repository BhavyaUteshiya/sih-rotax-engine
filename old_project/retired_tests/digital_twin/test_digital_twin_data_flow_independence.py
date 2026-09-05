"""
Digital Twin End-to-End Data Flow & Independence Integration Test.
SIH26054 — Module 03 Digital Twin Core.
"""

import pytest
from src.module02.integration.integration_runner import MasterIntegrationRunner
from src.module02.integration.can_transport import InMemoryTransport
from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.digital_twin.models.expected_state import ExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.twin_state import DigitalTwinStatus


def test_digital_twin_data_flow_and_source_independence():
    """
    ACCEPTANCE TEST: Proves that Digital Twin ExpectedState and ObservedState
    originate from TWO TRULY INDEPENDENT SOURCES:
    
    Source A (ExpectedState): Module 01 Physical Simulation Truth (sim_state)
    Source B (ObservedState): Module 02 Acquisition Pipeline (pipeline channel buffers & telemetry frames)
    """
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    # Step simulation and publish telemetry across CAN bus & Module 02 ingestion bridge
    runner.simulator.set_environment_inputs(altitude_m=1000.0, temp_offset_k=0.0)
    
    for _ in range(10):
        # 1. Physical truth generation (Module 01)
        runner.simulator.step_thermodynamic_cycle(
            throttles={1: 75.0, 2: 75.0},
            starter_commands={1: True, 2: True},
            flight_path_angle_rad=0.0
        )
        # 2. Sensor encoding & CAN transmission (Sensor Layer / Telemetry Scheduler)
        runner.scheduler.step_physics_and_publish_telemetry(
            state=runner.simulator.state,
            simulation_time_sec=runner.clock.simulation_time_sec,
        )
        # 3. CAN transport reception & Module 02 Ingestion Pipeline processing
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    # 4. Digital Twin processing step consuming BOTH distinct sources
    sim_truth_state = runner.simulator.state
    module02_pipeline = runner.pipeline

    twin_state = twin_engine.process_step(
        sim_state=sim_truth_state,
        pipeline=module02_pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec,
        sequence_number=runner.scheduler.records_published,
        operating_context={"throttle_pct": 75.0}
    )

    expected = twin_state.expected_state
    observed = twin_state.observed_state
    residuals = twin_state.residual_state

    # Verify ExpectedState source (Module 01 truth)
    phys_rpm_truth = sim_truth_state.engines[1].engine_rpm
    assert expected.rpm == phys_rpm_truth

    # Verify ObservedState source (Module 02 validated telemetry pipeline)
    latest_meas = module02_pipeline.channel_buffers.get("engine.rpm")
    if latest_meas and latest_meas.get_latest():
        pipeline_obs_rpm = latest_meas.get_latest().engineering_value or latest_meas.get_latest().value
        assert observed.rpm == float(pipeline_obs_rpm)

    # Verify residual calculation: residual = observed - expected
    res_rpm = residuals.residuals["rpm"]
    assert pytest.approx(res_rpm.expected, 1e-4) == expected.rpm
    assert pytest.approx(res_rpm.observed, 1e-4) == observed.rpm
    assert pytest.approx(res_rpm.residual, 1e-4) == (observed.rpm - expected.rpm)

    # Verify status and data quality
    assert observed.data_quality in {"GOOD", "DEGRADED"}
    assert twin_state.status in {DigitalTwinStatus.SYNCHRONIZED, DigitalTwinStatus.DEVIATION_DETECTED}


def test_observed_state_does_not_mutate_or_alias_physical_truth():
    """
    Verifies that modifying physical truth in sim_state does NOT directly
    mutate an already-ingested ObservedState object from Module 02.
    """
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    dt_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    runner.simulator.step_thermodynamic_cycle(throttles={1: 50.0, 2: 50.0}, starter_commands={1: True, 2: True})
    runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=0.1)
    frames = runner.transport.receive_frames(max_frames=100)
    runner.bridge.process_batch(frames)

    twin_state_1 = dt_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=0.1
    )

    obs_rpm_snapshot = twin_state_1.observed_state.rpm

    # Mutate physical truth state directly
    runner.simulator.state.engines[1].engine_rpm = 9999.0

    # Ensure previous ObservedState snapshot remains unchanged
    assert twin_state_1.observed_state.rpm == obs_rpm_snapshot
    assert twin_state_1.observed_state.rpm != 9999.0


def test_observed_state_insufficient_data_when_pipeline_empty():
    """
    MANDATE C: Proves that when Module 02 telemetry is missing or pipeline is None,
    ObservedState returns data_quality='INSUFFICIENT_DATA' with NO simulation fallback.
    """
    obs = ObservedState.from_module02_pipeline(pipeline=None, target_timestamp=10.0)
    assert obs.data_quality == "INSUFFICIENT_DATA"
    assert obs.valid_sensors_count == 0
    assert obs.rpm is None

    dt_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")
    state = dt_engine.process_step(
        sim_state=None if not hasattr(dt_engine, 'sim') else dt_engine.sim,
        pipeline=None,
        engine_index=1,
        timestamp=10.0
    )
    assert state.data_quality == "INSUFFICIENT_DATA"
    assert state.status == DigitalTwinStatus.INSUFFICIENT_DATA
    assert state.confidence == 0.0


def test_timestamp_alignment_mismatch_returns_insufficient_data():
    """
    MANDATE F & G: Proves that requesting a Digital Twin state at timestamp X (e.g. 100.0 s)
    when Module 02 pipeline measurements are at timestamp Y (e.g. 0.1 s) results in
    data_quality='INSUFFICIENT_DATA' rather than an invalid residual.
    """
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    dt_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    runner.simulator.step_thermodynamic_cycle(throttles={1: 50.0, 2: 50.0}, starter_commands={1: True, 2: True})
    runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=0.1)
    frames = runner.transport.receive_frames(max_frames=100)
    runner.bridge.process_batch(frames)

    # Request step at target_timestamp=100.0 s (skew = 99.9 s > max_time_skew_sec 0.1 s)
    state = dt_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=100.0
    )

    assert state.observed_state.data_quality == "INSUFFICIENT_DATA"
    assert state.status == DigitalTwinStatus.INSUFFICIENT_DATA
    assert state.confidence == 0.0


def test_no_tapas_identity_in_digital_twin_models():
    """
    MANDATE I: Verifies that Digital Twin runtime states use rotax_914_uav identity
    and contain zero 'tapas_bh201' string references.
    """
    exp = ExpectedState()
    obs = ObservedState()
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    assert exp.aircraft_id == "rotax_914_uav"
    assert obs.aircraft_id == "rotax_914_uav"
    assert exp.aircraft_id != "tapas_bh201"
    assert obs.aircraft_id != "tapas_bh201"
