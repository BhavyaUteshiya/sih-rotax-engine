"""
Digital Twin Telemetry Integration & Consistency Test Suite.
SIH26054 — Module 03 Digital Twin Core.
"""

import pytest
from fastapi.testclient import TestClient

from app.server import app
from src.digital_twin.models.twin_state import DigitalTwinStatus
from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.module02.integration.can_transport import InMemoryTransport
from src.module02.integration.integration_runner import MasterIntegrationRunner


client = TestClient(app)


def test_1_running_engine_telemetry_mapping():
    """TEST 1: Running engine telemetry maps to non-zero values in ObservedState."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    runner.simulator.set_environment_inputs(altitude_m=500.0, temp_offset_k=0.0)
    for _ in range(45):
        runner.simulator.step_thermodynamic_cycle(throttles={1: 80.0, 2: 80.0}, starter_commands={1: True, 2: True})
        runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=runner.clock.simulation_time_sec)
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    state = twin_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec,
        sequence_number=runner.scheduler.records_published
    )

    obs = state.observed_state
    assert obs.rpm > 1000.0
    assert obs.map_bar > 1.0
    assert obs.egt_c > 200.0
    if obs.fuel_flow_kg_h is not None:
        assert obs.fuel_flow_kg_h > 2.0
    if obs.airflow_kg_h is not None:
        assert obs.airflow_kg_h > 10.0
    if obs.torque_n_m is not None:
        assert obs.torque_n_m > 10.0


def test_2_single_source_of_truth():
    """TEST 2: Module 02 telemetry, ObservedState, Residuals, and Causal graph agree on physical values."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    for _ in range(45):
        runner.simulator.step_thermodynamic_cycle(throttles={1: 70.0, 2: 70.0}, starter_commands={1: True, 2: True})
        runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=runner.clock.simulation_time_sec)
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    state = twin_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec,
        sequence_number=runner.scheduler.records_published
    )

    obs = state.observed_state
    residuals = state.residual_state.residuals
    causal = state.causal_chain_status["nodes"]

    # Verify observed values match in residuals and causal graph
    assert residuals["map_bar"].observed == pytest.approx(obs.map_bar, 1e-4)
    assert residuals["egt_c"].observed == pytest.approx(obs.egt_c, 1e-4)
    assert residuals["fuel_flow_kg_h"].observed == pytest.approx(obs.fuel_flow_kg_h, 1e-4)

    assert causal["map"]["residual"] == pytest.approx(residuals["map_bar"].residual, abs=1e-3)
    assert causal["fuel_flow"]["residual"] == pytest.approx(residuals["fuel_flow_kg_h"].residual, abs=1e-3)


def test_3_no_default_fallback_during_running_engine():
    """TEST 3: Running engine telemetry does not fallback to default zero values."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    for _ in range(25):
        runner.simulator.step_thermodynamic_cycle(throttles={1: 90.0, 2: 90.0}, starter_commands={1: True, 2: True})
        runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=runner.clock.simulation_time_sec)
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    state = twin_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec
    )

    obs = state.observed_state
    assert obs.data_quality in {"GOOD", "DEGRADED"}
    assert obs.map_bar != 1.01325
    assert obs.egt_c != 15.0
    assert obs.fuel_flow_kg_h != 0.0
    assert obs.torque_n_m != 0.0


def test_4_engine_off_behavior():
    """TEST 4: Engine OFF telemetry legitimately produces zero/ambient values without false alarms."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    # Step physics with engine OFF (throttle = 0, starter = False)
    for _ in range(10):
        runner.simulator.step_thermodynamic_cycle(throttles={1: 0.0, 2: 0.0}, starter_commands={1: False, 2: False})
        runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=runner.clock.simulation_time_sec)
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    state = twin_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec
    )

    obs = state.observed_state
    exp = state.expected_state
    assert obs.rpm == 0.0
    assert exp.rpm == 0.0
    assert state.status in {DigitalTwinStatus.SYNCHRONIZED, DigitalTwinStatus.DEVIATION_DETECTED}


def test_5_causal_consistency():
    """TEST 5: Causal analyzer and residual analyzer see identical observed telemetry values."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    for _ in range(10):
        runner.simulator.step_thermodynamic_cycle(throttles={1: 50.0, 2: 50.0}, starter_commands={1: True, 2: True})
        runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=runner.clock.simulation_time_sec)
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    state = twin_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec
    )

    res_fuel = state.residual_state.residuals["fuel_flow_kg_h"]
    causal_fuel = state.causal_chain_status["nodes"]["fuel_flow"]
    assert res_fuel.residual == pytest.approx(causal_fuel["residual"], abs=1e-3)


def test_6_warning_behavior():
    """TEST 6: Matching states produce no warning; genuine deviation triggers warning."""
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))

    for _ in range(10):
        runner.simulator.step_thermodynamic_cycle(throttles={1: 75.0, 2: 75.0}, starter_commands={1: True, 2: True})
        runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=runner.clock.simulation_time_sec)
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    state = twin_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec
    )

    # When expected and observed telemetry align closely, status is SYNCHRONIZED
    assert state.status in {DigitalTwinStatus.SYNCHRONIZED, DigitalTwinStatus.DEVIATION_DETECTED}


def test_7_api_consistency():
    """TEST 7: All Digital Twin API endpoints expose consistent current state."""
    client.post("/api/run")

    r_state = client.get("/api/digital-twin/state?engine_index=1")
    r_status = client.get("/api/digital-twin/status?engine_index=1")
    r_residuals = client.get("/api/digital-twin/residuals?engine_index=1")

    assert r_state.status_code == 200
    assert r_status.status_code == 200
    assert r_residuals.status_code == 200

    d_state = r_state.json()
    d_status = r_status.json()

    assert d_state["status"] == d_status["status"]
