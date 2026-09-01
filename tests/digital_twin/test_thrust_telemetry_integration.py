"""
Thrust Telemetry Integration & Single Source of Truth Regression Test.
SIH26054 — Module 03 Digital Twin Core.
"""

import pytest

from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.module02.integration.can_transport import InMemoryTransport
from src.module02.integration.integration_runner import MasterIntegrationRunner


def test_thrust_telemetry_single_source_of_truth():
    """
    REGRESSION TEST: Verifies that physical propeller thrust produced by Rotax 914
    flows cleanly into Telemetry -> Module 02 -> ObservedState -> ResidualAnalyzer -> CausalAnalyzer.
    
    Proves single source of truth across all consumers.
    """
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    twin_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    # Step simulation until thrust evolves
    runner.simulator.set_environment_inputs(altitude_m=500.0, temp_offset_k=0.0)
    for _ in range(30):
        runner.simulator.step_thermodynamic_cycle(
            throttles={1: 85.0, 2: 85.0},
            starter_commands={1: True, 2: True},
            flight_path_angle_rad=0.0
        )
        runner.scheduler.step_physics_and_publish_telemetry(
            state=runner.simulator.state,
            simulation_time_sec=runner.clock.simulation_time_sec
        )
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    # 1. Verify physical simulator thrust is non-zero
    sim_thrust = runner.simulator.state.propulsion.propellers[1].thrust_n
    assert sim_thrust > 100.0, f"Physical simulation thrust must be > 100 N, got {sim_thrust} N"

    # 2. Verify Module 02 telemetry buffer contains non-zero decoded thrust
    buf = runner.pipeline.channel_buffers.get("engine.propeller.thrust")
    assert buf is not None and buf.get_latest() is not None
    module02_thrust = buf.get_latest().engineering_value
    assert module02_thrust > 100.0
    assert module02_thrust == pytest.approx(sim_thrust, abs=1.0)  # within CAN 0.1 N quantization

    # 3. Process Digital Twin step
    st = twin_engine.process_step(
        sim_state=runner.simulator.state,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=runner.clock.simulation_time_sec,
        sequence_number=runner.scheduler.records_published
    )

    # 4. Verify ObservedState thrust matches Module 02 telemetry
    assert st.observed_state.thrust_n > 100.0
    assert st.observed_state.thrust_n == pytest.approx(module02_thrust, abs=1e-4)

    # 5. Verify ExpectedState thrust matches physical simulation thrust
    assert st.expected_state.thrust_n == pytest.approx(sim_thrust, abs=1e-4)

    # 6. Verify Thrust Residual is near zero (no false warning)
    thrust_residual = st.residual_state.residuals["thrust_n"]
    assert abs(thrust_residual.residual) < 5.0
    assert thrust_residual.warning_triggered is False

    # 7. Verify CausalAnalyzer receives same non-zero residual
    causal_thrust = st.causal_chain_status["nodes"]["thrust"]
    assert causal_thrust["residual"] == pytest.approx(thrust_residual.residual, abs=1e-3)
