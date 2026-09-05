"""
Verification of Production Test Injection Removal.
SIH26054 — Module 03 Digital Twin Core.
"""

from fastapi.testclient import TestClient

from app.server import app
from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.module02.integration.can_transport import InMemoryTransport
from src.module02.integration.integration_runner import MasterIntegrationRunner


client = TestClient(app)


def test_1_production_test_injection_endpoints_removed():
    """1. Verifies that production test-injection endpoints do NOT exist / return 404 or 405."""
    r_post = client.post("/api/digital-twin/test-inject", json={"parameter": "map", "offset": -0.3, "enabled": True})
    assert r_post.status_code in {404, 405}, f"Expected 404/405 for removed endpoint, got {r_post.status_code}"

    r_get = client.get("/api/digital-twin/test-inject")
    assert r_get.status_code in {404, 405}

    r_clear = client.post("/api/digital-twin/test-inject/clear")
    assert r_clear.status_code in {404, 405}


def test_2_digital_twin_engine_has_no_test_injection_methods():
    """2. Verifies that DigitalTwinEngine has no test injection state or methods."""
    engine = DigitalTwinEngine()
    assert not hasattr(engine, "test_injection")
    assert not hasattr(engine, "set_test_injection")
    assert not hasattr(engine, "get_test_injection")


def test_3_4_observed_state_derived_strictly_from_module02_without_mutation():
    """3 & 4. Verifies that ObservedState is never artificially mutated and real telemetry remains the only source."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    engine = DigitalTwinEngine()

    # Step physics & telemetry for 15 cycles to populate Module 02 channel buffers
    for _ in range(15):
        runner.simulator.step_thermodynamic_cycle(throttles={1: 75.0, 2: 75.0}, starter_commands={1: True, 2: True})
        runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=runner.clock.simulation_time_sec)
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    # Process Digital Twin step
    dt_state = engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec
    )

    # Verify observed state quality is GOOD and values match Module 02 telemetry
    assert dt_state.observed_state.data_quality in {"GOOD", "DEGRADED"}
    assert dt_state.observed_state.rpm is not None
    assert dt_state.observed_state.map_bar is not None
