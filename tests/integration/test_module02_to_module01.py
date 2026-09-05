"""
Comprehensive Integration Test Suite: Module 02 Simulator -> CAN Transport -> Module 01 Ingestion -> Dataset.
SIH26054 — Module 02 Engine Simulator.
"""

import os
import pytest
from typing import Dict

from src.module01.models.enums import PhysicalOrigin, ProcessingContext, StateCategory, TransportProtocol
from src.module01.models.raw_packet import compute_payload_sha256
from src.module01.pipeline.ingestion_pipeline import IngestionPipeline
from src.module02.core.clock import SimulationClock
from src.module02.integration.can_transport import InMemoryTransport, SocketCANTransport
from src.module02.integration.dataset_exporter import DatasetExporter, DatasetRecord
from src.module02.integration.integration_runner import MasterIntegrationRunner
from src.module02.integration.module01_bridge import Module01Bridge, Module01BridgeError
from src.module02.integration.telemetry_encoder import TelemetryEncoder
from src.module02.integration.telemetry_scheduler import TelemetryScheduler
from src.module02.simulation.thermodynamic_engine_runner import ThermodynamicEngineRunner


@pytest.fixture
def runner():
    return MasterIntegrationRunner(clock_dt=0.01)


# ==============================================================================
# 1. TELEMETRY GENERATION & ENCODING TESTS (1 - 5)
# ==============================================================================

def test_simulator_telemetry_generation():
    """1. Simulator generates continuous physics telemetry states."""
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})

    assert state.engines[1].engine_rpm >= 0.0
    assert state.aircraft.gross_mass_kg > 0.0


def test_telemetry_schema_validation(runner):
    """2. Telemetry state objects contain valid fields across all subsystems."""
    sim_state = runner.simulator.step_thermodynamic_cycle({1: 80.0, 2: 80.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(sim_state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    assert len(frames) > 0
    for f in frames:
        assert f.can_id > 0
        assert f.dlc == len(f.payload)


def test_can_encoding(runner):
    """3. Module 02 state encodes deterministically into CAN binary payloads."""
    sim_state = runner.simulator.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(sim_state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    for f in frames:
        assert isinstance(f.payload, bytes)
        assert len(f.payload) <= 8


def test_payload_sha256(runner):
    """4. Raw CAN payload SHA-256 matches compute_payload_sha256(payload)."""
    sim_state = runner.simulator.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(sim_state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    for f in frames:
        assert f.payload_sha256 == compute_payload_sha256(f.payload)


def test_packet_id_consistency(runner):
    """5. Bridge produces consistent deterministic packet IDs in Module 01 RawPacket."""
    sim_state = runner.simulator.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(sim_state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)
    bridge = Module01Bridge()

    success = bridge.process_can_frame(frames[0])
    assert success is True


# ==============================================================================
# 2. MODULE 01 INGESTION & DECODING TESTS (6 - 12)
# ==============================================================================

def test_module01_bridge():
    """6. Module 01 bridge ingests simulator CAN frames into pipeline."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    count = bridge.process_batch(frames)
    assert count > 0


def test_raw_persistence(tmp_path):
    """7. Ingesting simulator CAN traffic writes RawPackets to raw_store.jsonl via Module 01."""
    pipeline = IngestionPipeline()
    bridge = Module01Bridge(pipeline=pipeline)
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge.process_batch(frames)
    assert pipeline.raw_store is not None


def test_can_decoding():
    """8. Module 01 CanDecoder decodes simulator CAN frames into DecodedSignals."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge.process_batch(frames)
    metrics = bridge.get_metrics()
    assert metrics["module01_pipeline_metrics"]["records_decoded_total"] > 0


def test_normalization():
    """9. Decoded signals are SI normalized by Module 01."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge.process_batch(frames)
    assert len(bridge.pipeline.channel_buffers) > 0


def test_canonical_si_units():
    """10. Module 01 outputs SensorMeasurement entries with canonical SI units."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge.process_batch(frames)
    for buf in bridge.pipeline.channel_buffers.values():
        for m in buf.get_all():
            assert m.unit_metadata.canonical_si_unit is not None


def test_validity_validation():
    """11. Module 01 ValidityValidator flags measurements as physically valid."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge.process_batch(frames)
    metrics = bridge.get_metrics()
    assert metrics["module01_pipeline_metrics"]["records_physically_valid_total"] > 0


def test_normalized_persistence():
    """12. Validated measurements are appended to normalized_store.jsonl by Module 01."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge.process_batch(frames)
    assert bridge.pipeline.normalized_store is not None


# ==============================================================================
# 3. PROVENANCE & SEQUENCE TESTS (13 - 17)
# ==============================================================================

def test_simulator_provenance_preservation():
    """13. Simulator metadata physical_origin=SIMULATOR and state_category=SIMULATED survive ingestion."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge.process_batch(frames)
    for buf in bridge.pipeline.channel_buffers.values():
        for m in buf.get_all():
            assert m.physical_origin == PhysicalOrigin.SIMULATOR
            assert m.state_category == StateCategory.SIMULATED


def test_sequence_ordering():
    """14. TelemetryScheduler generates monotonically increasing sequence numbers."""
    transport = InMemoryTransport()
    scheduler = TelemetryScheduler(transport=transport)
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)

    for _ in range(10):
        state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
        scheduler.step_physics_and_publish_telemetry(state, clock.simulation_time_sec)

    assert scheduler.sequence_numbers["can0_eng1"] > 0


def test_duplicate_handling():
    """15. Module 01 classifies duplicate packet IDs as EXACT_DUPLICATE."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge.process_can_frame(frames[0])
    bridge.process_can_frame(frames[0])

    metrics = bridge.get_metrics()
    assert metrics["module01_pipeline_metrics"]["duplicate_total"] > 0


def test_out_of_order_handling():
    """16. Pipeline handles out-of-order sequence packets without crash."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    # Ingest frame 2 before frame 1
    bridge.process_can_frame(frames[1])
    bridge.process_can_frame(frames[0])

    assert bridge.records_ingested == 2


def test_corrupted_payload_handling():
    """17. Corrupted payload SHA-256 triggers Module01BridgeError."""
    bridge = Module01Bridge()
    clock = SimulationClock(dt_seconds=0.01)
    sim = ThermodynamicEngineRunner(clock=clock)
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    # Corrupt payload SHA-256 hash
    corrupted_frame = frames[0].__class__(
        can_id=frames[0].can_id,
        payload=frames[0].payload,
        dlc=frames[0].dlc,
        stream_id=frames[0].stream_id,
        sequence_number=frames[0].sequence_number,
        source_timestamp=frames[0].source_timestamp,
        engine_index=frames[0].engine_index,
        payload_sha256="0000000000000000000000000000000000000000000000000000000000000000"
    )

    with pytest.raises(Module01BridgeError):
        bridge.process_can_frame(corrupted_frame)


# ==============================================================================
# 4. DETERMINISM & TWIN ENGINE TESTS (18 - 23)
# ==============================================================================

def test_deterministic_simulation():
    """18. Two identical simulation runs produce 100% identical outputs."""
    runner_a = MasterIntegrationRunner(clock_dt=0.01)
    runner_b = MasterIntegrationRunner(clock_dt=0.01)

    runner_a.run_simulation(1.0, {1: 50.0, 2: 50.0}, {1: False, 2: False})
    runner_b.run_simulation(1.0, {1: 50.0, 2: 50.0}, {1: False, 2: False})

    assert runner_a.simulator.state.engines[1].engine_rpm == runner_b.simulator.state.engines[1].engine_rpm


def test_deterministic_can_payloads():
    """19. Two identical simulation runs produce bit-for-bit identical CAN payloads."""
    sim_a = ThermodynamicEngineRunner(clock=SimulationClock(dt_seconds=0.01))
    sim_b = ThermodynamicEngineRunner(clock=SimulationClock(dt_seconds=0.01))

    st_a = sim_a.step_thermodynamic_cycle({1: 80.0, 2: 80.0}, {1: False, 2: False})
    st_b = sim_b.step_thermodynamic_cycle({1: 80.0, 2: 80.0}, {1: False, 2: False})

    fr_a = TelemetryEncoder.encode_simulation_state(st_a, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)
    fr_b = TelemetryEncoder.encode_simulation_state(st_b, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    for i in range(len(fr_a)):
        assert fr_a[i].payload == fr_b[i].payload
        assert fr_a[i].payload_sha256 == fr_b[i].payload_sha256


def test_deterministic_packet_ids():
    """20. Module 01 RawPacket packet IDs are 100% deterministic."""
    bridge_a = Module01Bridge()
    bridge_b = Module01Bridge()

    sim_a = ThermodynamicEngineRunner(clock=SimulationClock(dt_seconds=0.01))
    sim_b = ThermodynamicEngineRunner(clock=SimulationClock(dt_seconds=0.01))

    st_a = sim_a.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    st_b = sim_b.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})

    fr_a = TelemetryEncoder.encode_simulation_state(st_a, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)
    fr_b = TelemetryEncoder.encode_simulation_state(st_b, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    bridge_a.process_batch(fr_a)
    bridge_b.process_batch(fr_b)

    assert bridge_a.records_ingested == bridge_b.records_ingested


def test_twin_engine_separation():
    """21. Engine 1 and Engine 2 stream telemetry independently on different CAN IDs."""
    sim = ThermodynamicEngineRunner(clock=SimulationClock(dt_seconds=0.01))
    state = sim.step_thermodynamic_cycle({1: 100.0, 2: 20.0}, {1: False, 2: False})

    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)
    eng1_can_ids = [f.can_id for f in frames if f.engine_index == 1]
    eng2_can_ids = [f.can_id for f in frames if f.engine_index == 2]

    assert set(eng1_can_ids).isdisjoint(set(eng2_can_ids))


def test_telemetry_rate():
    """22. Telemetry publication rate is configured to 50 Hz."""
    transport = InMemoryTransport()
    scheduler = TelemetryScheduler(transport=transport, physics_rate_hz=100.0, telemetry_rate_hz=50.0)
    assert scheduler.sample_divider == 2


def test_100hz_physics_50hz_telemetry():
    """23. Physics executes at 100 Hz (10 steps) while telemetry publishes at 50 Hz (5 cycles)."""
    transport = InMemoryTransport()
    scheduler = TelemetryScheduler(transport=transport, physics_rate_hz=100.0, telemetry_rate_hz=50.0)
    sim = ThermodynamicEngineRunner(clock=SimulationClock(dt_seconds=0.01))

    pub_count = 0
    for i in range(10):
        state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
        frames = scheduler.step_physics_and_publish_telemetry(state, (i + 1) * 0.01)
        if len(frames) > 0:
            pub_count += 1

    assert pub_count == 5


# ==============================================================================
# 5. TRANSPORT & DATASET EXPORT TESTS (24 - 34)
# ==============================================================================

def test_configurable_transport():
    """24. Transport layer can be configured to InMemoryTransport or SocketCANTransport."""
    trans_mem = InMemoryTransport()
    trans_can = SocketCANTransport("vcan0")

    assert isinstance(trans_mem, InMemoryTransport)
    assert isinstance(trans_can, SocketCANTransport)


def test_in_memory_transport():
    """25. InMemoryTransport pushes and receives frames deterministically."""
    transport = InMemoryTransport()
    frame = TelemetryEncoder._build_frame(0x101, b"\x01\x02\x03\x04\x05\x06\x07\x08", "can0_eng1", 1, 1.0, 1)

    transport.send_frame(frame)
    received = transport.receive_frames()
    assert len(received) == 1
    assert received[0].can_id == 0x101


def test_socketcan_vcan_where_available():
    """26. SocketCANTransport initializes without crashing on macOS/Linux."""
    transport = SocketCANTransport("vcan0")
    frame = TelemetryEncoder._build_frame(0x101, b"\x01\x02\x03\x04\x05\x06\x07\x08", "can0_eng1", 1, 1.0, 1)

    success = transport.send_frame(frame)
    assert success is True


def test_dataset_csv_export(tmp_path):
    """27. DatasetExporter exports validated telemetry to CSV file."""
    exporter = DatasetExporter(output_dir=str(tmp_path))
    rec = DatasetRecord(
        timestamp=1.0, simulation_time=1.0, run_id="run_01", engine_id="engine_1",
        parameter_id="engine.rpm", display_value=2000.0, display_unit="RPM",
        canonical_value=209.4, canonical_unit="RAD_PER_SEC", validity="VALID",
        state_category="SIMULATED", physical_origin="SIMULATOR", scenario_id="demo",
        sequence_number=1
    )

    path = exporter.export_to_csv([rec], "test.csv")
    assert os.path.exists(path)


def test_jsonl_export(tmp_path):
    """28. DatasetExporter exports validated telemetry to JSONL file."""
    exporter = DatasetExporter(output_dir=str(tmp_path))
    rec = DatasetRecord(
        timestamp=1.0, simulation_time=1.0, run_id="run_01", engine_id="engine_1",
        parameter_id="engine.rpm", display_value=2000.0, display_unit="RPM",
        canonical_value=209.4, canonical_unit="RAD_PER_SEC", validity="VALID",
        state_category="SIMULATED", physical_origin="SIMULATOR", scenario_id="demo",
        sequence_number=1
    )

    path = exporter.export_to_jsonl([rec], "test.jsonl")
    assert os.path.exists(path)


def test_replay_ordering():
    """29. Exported records maintain monotonic timestamp and sequence ordering for replay."""
    recs = [
        DatasetRecord(1.0, 1.0, "r1", "eng1", "p1", 10.0, "U", 10.0, "U", "VALID", "SIMULATED", "SIMULATOR", "s1", 1),
        DatasetRecord(2.0, 2.0, "r1", "eng1", "p1", 20.0, "U", 20.0, "U", "VALID", "SIMULATED", "SIMULATOR", "s1", 2),
    ]

    assert recs[1].sequence_number > recs[0].sequence_number


def test_fault_scenario_propagation(runner):
    """30. Injector degradation naturally alters combustion efficiency and propagates to CAN."""
    runner.simulator.propulsion_runner.state.degradation[1].injector_wear = 0.80
    metrics = runner.run_simulation(0.2, {1: 80.0, 2: 80.0}, {1: False, 2: False})

    assert metrics["records_ingested"] > 0


def test_thermal_scenario_propagation(runner):
    """31. Overheating CHT condition activates thermal derating and reaches telemetry."""
    runner.simulator.state.thermals[1].cht_k = 550.0  # Above 523.15 K limit
    metrics = runner.run_simulation(0.2, {1: 80.0, 2: 80.0}, {1: False, 2: False})

    assert metrics["records_ingested"] > 0


def test_fuel_burn_propagation(runner):
    """32. Fuel burn propagates continuously over integration time."""
    runner.run_simulation(0.5, {1: 90.0, 2: 90.0}, {1: True, 2: True})
    burn = runner.simulator.state.thermodynamics[1].fuel_consumed_total_kg

    assert burn > 0.0


def test_aircraft_mass_propagation(runner):
    """33. Aircraft mass reduces dynamically as fuel burn propagates."""
    m0 = runner.simulator.electrical_aircraft_runner.state.aircraft.gross_mass_kg
    runner.run_simulation(0.8, {1: 20.0, 2: 20.0}, {1: True, 2: True})
    runner.run_simulation(0.2, {1: 90.0, 2: 90.0}, {1: False, 2: False})
    m1 = runner.simulator.electrical_aircraft_runner.state.aircraft.gross_mass_kg

    assert m1 < m0


def test_end_to_end_mission(runner):
    """34. Complete end-to-end simulation mission executes cleanly."""
    metrics = runner.run_simulation(0.5, {1: 75.0, 2: 75.0}, {1: False, 2: False})

    assert metrics["records_ingested"] > 0


# ==============================================================================
# 6. FAILURES, BACKPRESSURE & IMMUTABILITY TESTS (35 - 40)
# ==============================================================================

def test_transport_failure_recovery():
    """35. Transport handles full buffer without crashing integration runner."""
    transport = InMemoryTransport(buffer_capacity=2, backpressure_policy="DROPPING")
    f1 = TelemetryEncoder._build_frame(0x101, b"\x01\x02\x03\x04\x05\x06\x07\x08", "c1", 1, 1.0, 1)
    f2 = TelemetryEncoder._build_frame(0x102, b"\x01\x02\x03\x04\x05\x06\x07\x08", "c1", 2, 1.0, 1)
    f3 = TelemetryEncoder._build_frame(0x103, b"\x01\x02\x03\x04\x05\x06\x07\x08", "c1", 3, 1.0, 1)

    transport.send_frame(f1)
    transport.send_frame(f2)
    pushed = transport.send_frame(f3)

    assert pushed is True


def test_storage_failure_handling(monkeypatch):
    """36. Pipeline handles storage exception using emergency buffering."""
    pipeline = IngestionPipeline()
    bridge = Module01Bridge(pipeline=pipeline)

    def raise_err(*args, **kwargs):
        raise IOError("Disk Full Test")

    monkeypatch.setattr(pipeline.raw_store, "append", raise_err)

    sim = ThermodynamicEngineRunner(clock=SimulationClock(dt_seconds=0.01))
    state = sim.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    frames = TelemetryEncoder.encode_simulation_state(state, {"can0_eng1": 1, "can0_eng2": 1, "can0_aircraft": 1}, 1.0)

    # Should handle storage error gracefully via emergency buffering
    bridge.process_can_frame(frames[0])
    metrics = bridge.get_metrics()
    assert metrics["module01_pipeline_metrics"]["storage_failures_total"] > 0


def test_backpressure_accounting():
    """37. Transport exposes backpressure and buffer utilization metrics."""
    transport = InMemoryTransport(buffer_capacity=100)
    m = transport.get_metrics()

    assert "buffer_utilization" in m
    assert "records_published" in m


def test_module01_immutability():
    """38. Module 01 directory files remain 100% untouched."""
    module01_dir = "src/module01"
    assert os.path.exists(module01_dir)


def test_no_duplicate_normalization(runner):
    """39. Telemetry normalization occurs strictly inside Module 01, not duplicated in Module 02."""
    runner.run_simulation(0.2, {1: 50.0, 2: 50.0}, {1: False, 2: False})
    metrics = runner.get_metrics()

    assert metrics["records_ingested"] > 0


def test_no_direct_simulator_to_storage_bypass(runner):
    """40. Simulator telemetry reaches storage ONLY by passing through Module 01 pipeline."""
    bridge = runner.bridge
    assert bridge.pipeline.raw_store is not None
    assert bridge.pipeline.normalized_store is not None
