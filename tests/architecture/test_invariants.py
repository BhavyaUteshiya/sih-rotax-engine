"""
Mandatory Architectural Invariant & Compliance Tests for Module 01 (V4.3 Final Hardening Pass).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import math
import time
from pathlib import Path
from types import MappingProxyType
import pytest

from src.module01.acquisition.file_source import CSVFileSource, JSONFileSource
from src.module01.acquisition.mock_can_adapter import DemonstrationCanAdapter
from src.module01.acquisition.mock_ecu_adapter import MockEcuAdapter
from src.module01.config.config_loader import ConfigLoader
from src.module01.decoding.can_decoder import CanDecoder
from src.module01.models.enums import (
    AlignmentMethod,
    IntegrityStatus,
    ParameterClassification,
    PhysicalOrigin,
    ProcessingContext,
    StateCategory,
    StorageRecoveryState,
    TemporalQuality,
    TimestampDomain,
    TransformationMetadata,
    TransportProtocol,
    ValidityStatus,
)
from src.module01.models.metadata import AlignmentMetadata, ClockMapping, DecodedSignal, FrameTime, MeasurementLineage, SyncMetadata, TimestampModel
from src.module01.models.raw_packet import DeepImmutableRawPacket, compute_packet_id, compute_payload_sha256
from src.module01.models.sensor_sample import SensorMeasurement
from src.module01.models.telemetry_frame import TelemetryFrame
from src.module01.models.vibration_data import VibrationWaveformChunk
from src.module01.normalization.unit_normalizer import UnitConversionError, UnitNormalizer
from src.module01.pipeline.ingestion_pipeline import IngestionPipeline
from src.module01.storage.datastore import NormalizedStore, RawStore, StorageRecoveryStateMachine
from src.module01.synchronization.time_synchronizer import TimestampSynchronizer
from src.module01.timestamps.clock_mapper import ClockMapper
from src.module01.validation.validity_validator import ValidityValidator
from src.module01.interfaces.contracts import TimeRange


def test_1_raw_payload_immutability(sample_raw_packet):
    """1. Raw payload immutability."""
    assert isinstance(sample_raw_packet.raw_bytes, bytes)
    with pytest.raises(TypeError):
        sample_raw_packet.raw_bytes[0] = 0xFF

    assert isinstance(sample_raw_packet.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        sample_raw_packet.metadata["new_key"] = "test"


def test_2_payload_sha256_correctness():
    """2. payload_sha256 correctness (lowercase 64-hex chars)."""
    raw = b"test_payload_bytes_12345"
    sha = compute_payload_sha256(raw)
    assert len(sha) == 64
    assert sha == sha.lower()


def test_3_packet_id_deterministic_canonicalization():
    """3. packet_id deterministic canonicalization."""
    ts = 1771928000.123456
    sha = compute_payload_sha256(b"hello")
    pid1 = compute_packet_id("can0", 100, ts, sha)
    pid2 = compute_packet_id("can0", 100, ts, sha)
    assert pid1 == pid2
    assert len(pid1) == 64


def test_4_packet_id_not_equal_payload_sha256():
    """4. packet_id != payload_sha256 invariant."""
    raw = b"same_payload"
    sha = compute_payload_sha256(raw)
    pid = compute_packet_id("can0", 1, 100.0, sha)
    assert pid != sha


def test_5_different_packets_unique_identity():
    """5. Different packets do not accidentally share identity."""
    sha = compute_payload_sha256(b"payload")
    pid1 = compute_packet_id("can0", 1, 100.0, sha)
    pid2 = compute_packet_id("can0", 2, 100.0, sha)
    pid3 = compute_packet_id("can1", 1, 100.0, sha)
    assert pid1 != pid2
    assert pid1 != pid3


def test_6_synthetic_provenance():
    """6. Synthetic provenance (DemonstrationCanAdapter & MockEcuAdapter)."""
    can_ad = DemonstrationCanAdapter()
    can_ad.connect()
    frame = can_ad.read_frame()
    assert frame.raw_packet.physical_origin == PhysicalOrigin.SIMULATOR
    assert frame.raw_packet.metadata.get("state_category") == StateCategory.SIMULATED.value

    ecu_ad = MockEcuAdapter()
    ecu_ad.connect()
    pkt = ecu_ad.read_telemetry()
    assert pkt.physical_origin == PhysicalOrigin.SIMULATOR
    assert pkt.metadata.get("state_category") == StateCategory.SIMULATED.value


def test_7_simulation_provenance_rejection():
    """7. Simulation injection provenance rules: SIMULATOR + SIMULATED ACCEPT, others REJECT."""
    pipeline = IngestionPipeline()
    ts = TimestampModel(10.0, TimestampDomain.UTC, 10.0, 10.0, 10.0, 1000)

    m1 = SensorMeasurement.create_valid(
        "m1", "engine.rpm", 520.0, 5200.0, UnitNormalizer.get_unit_metadata("RPM"), ts, MeasurementLineage(),
        physical_origin=PhysicalOrigin.SIMULATOR, state_category=StateCategory.SIMULATED
    )
    assert pipeline.inject_simulated_measurement(m1) is True

    m2 = SensorMeasurement.create_valid(
        "m2", "engine.rpm", 520.0, 5200.0, UnitNormalizer.get_unit_metadata("RPM"), ts, MeasurementLineage(),
        physical_origin=PhysicalOrigin.ECU, state_category=StateCategory.SIMULATED
    )
    assert pipeline.inject_simulated_measurement(m2) is False

    m3 = SensorMeasurement.create_valid(
        "m3", "engine.rpm", 520.0, 5200.0, UnitNormalizer.get_unit_metadata("RPM"), ts, MeasurementLineage(),
        physical_origin=PhysicalOrigin.SIMULATOR, state_category=StateCategory.ACTUAL_MEASURED
    )
    assert pipeline.inject_simulated_measurement(m3) is False


def test_8_simulated_frame_injection_rejection():
    """8. Simulated frame injection rejection: ALL measurements MUST be SIMULATOR + SIMULATED."""
    pipeline = IngestionPipeline()
    ts = TimestampModel(10.0, TimestampDomain.UTC, 10.0, 10.0, 10.0, 1000)
    ftime = FrameTime(10.0, TimestampDomain.UTC, 10.0, None, 1.0, "v1")
    sync_meta = SyncMetadata("SIMULATED", 0.02, 1.0, 1, 1, 0.0)

    sim_m = SensorMeasurement.create_valid(
        "m1", "engine.rpm", 520.0, 5200.0, UnitNormalizer.get_unit_metadata("RPM"), ts, MeasurementLineage(),
        physical_origin=PhysicalOrigin.SIMULATOR, state_category=StateCategory.SIMULATED
    )
    valid_frame = TelemetryFrame.create("f1", ftime, 10.0, ProcessingContext.SIMULATION_RUN, {"engine.rpm": sim_m}, sync_meta)
    assert pipeline.inject_simulated_frame(valid_frame) is True

    act_m = SensorMeasurement.create_valid(
        "m2", "engine.rpm", 520.0, 5200.0, UnitNormalizer.get_unit_metadata("RPM"), ts, MeasurementLineage(),
        physical_origin=PhysicalOrigin.ECU, state_category=StateCategory.ACTUAL_MEASURED
    )
    invalid_frame = TelemetryFrame.create("f2", ftime, 10.0, ProcessingContext.LIVE_STREAM, {"engine.rpm": act_m}, sync_meta)
    assert pipeline.inject_simulated_frame(invalid_frame) is False

    mixed_frame = TelemetryFrame.create("f3", ftime, 10.0, ProcessingContext.SIMULATION_RUN, {"engine.rpm": sim_m, "engine.oil.pressure": act_m}, sync_meta)
    assert pipeline.inject_simulated_frame(mixed_frame) is False


def test_9_actual_state_subscription_boundary():
    """9. Actual-state subscription boundary: ONLY delivers pure ACTUAL_MEASURED frames."""
    pipeline = IngestionPipeline()
    ts = TimestampModel(10.0, TimestampDomain.UTC, 10.0, 10.0, 10.0, 1000)
    ftime = FrameTime(10.0, TimestampDomain.UTC, 10.0, None, 1.0, "v1")
    sync_meta = SyncMetadata("CAUSAL", 0.02, 1.0, 1, 1, 0.0)

    delivered_frames = []
    sub_id = pipeline.subscribe_actual_state(lambda f: delivered_frames.append(f))

    act_m = SensorMeasurement.create_valid(
        "m1", "engine.rpm", 520.0, 5200.0, UnitNormalizer.get_unit_metadata("RPM"), ts, MeasurementLineage(),
        physical_origin=PhysicalOrigin.ECU, state_category=StateCategory.ACTUAL_MEASURED
    )
    actual_frame = TelemetryFrame.create("f_act", ftime, 10.0, ProcessingContext.LIVE_STREAM, {"engine.rpm": act_m}, sync_meta)

    sim_m = SensorMeasurement.create_valid(
        "m2", "engine.rpm", 520.0, 5200.0, UnitNormalizer.get_unit_metadata("RPM"), ts, MeasurementLineage(),
        physical_origin=PhysicalOrigin.SIMULATOR, state_category=StateCategory.SIMULATED
    )
    sim_frame = TelemetryFrame.create("f_sim", ftime, 10.0, ProcessingContext.SIMULATION_RUN, {"engine.rpm": sim_m}, sync_meta)

    est_m = SensorMeasurement.create_valid(
        "m3", "engine.rpm", 520.0, 5200.0, UnitNormalizer.get_unit_metadata("RPM"), ts, MeasurementLineage(),
        physical_origin=PhysicalOrigin.DERIVED, state_category=StateCategory.ESTIMATED
    )
    est_frame = TelemetryFrame.create("f_est", ftime, 10.0, ProcessingContext.LIVE_STREAM, {"engine.rpm": est_m}, sync_meta)

    pipeline.publish_frame(actual_frame)
    assert len(delivered_frames) == 1
    assert delivered_frames[0].frame_id == "f_act"

    pipeline.publish_frame(sim_frame)
    assert len(delivered_frames) == 1

    pipeline.publish_frame(est_frame)
    assert len(delivered_frames) == 1


def test_10_historical_ambiguous_provenance_rejection(temp_dir):
    """10. Ambiguous historical file provenance: missing state_category metadata is REJECTED."""
    pipeline = IngestionPipeline()
    now = time.time()

    p1 = DeepImmutableRawPacket.create(
        PhysicalOrigin.UNKNOWN, TransportProtocol.FILE, "file_stream", 1, b'{"engine_rpm": 5200.0}', now, time.monotonic_ns(),
        metadata={"state_category": StateCategory.ACTUAL_MEASURED.value}
    )
    assert pipeline.ingest_raw_packet(p1) is True

    p2 = DeepImmutableRawPacket.create(
        PhysicalOrigin.UNKNOWN, TransportProtocol.FILE, "file_stream", 2, b'{"engine_rpm": 5200.0}', now, time.monotonic_ns(),
        metadata={"state_category": StateCategory.SIMULATED.value}
    )
    assert pipeline.ingest_raw_packet(p2) is True

    p3 = DeepImmutableRawPacket.create(
        PhysicalOrigin.UNKNOWN, TransportProtocol.FILE, "file_stream", 3, b'{"engine_rpm": 5200.0}', now, time.monotonic_ns(),
        metadata={}
    )
    assert pipeline.ingest_raw_packet(p3) is False


def test_11_clock_mapping_formula():
    """11. Clock mapping formula: zero drift, positive drift, negative drift, offset, expired."""
    ref_src = 1000.0
    ref_utc = 2000.0

    cm1 = ClockMapping(ref_src, ref_utc, offset_seconds=0.0, drift_rate_ppm=0.0, confidence=1.0, mapping_version="v1", valid_until_utc=3000.0)
    mapper1 = ClockMapper(cm1)
    assert mapper1.map_to_utc(1010.0, TimestampDomain.ECU_BOOT, ingestion_utc=2010.0) == 2010.0

    cm2 = ClockMapping(ref_src, ref_utc, offset_seconds=2.0, drift_rate_ppm=100.0, confidence=1.0, mapping_version="v1", valid_until_utc=3000.0)
    mapper2 = ClockMapper(cm2)
    assert mapper2.map_to_utc(1100.0, TimestampDomain.ECU_BOOT, ingestion_utc=2000.0) == pytest.approx(2102.01, rel=1e-5)

    cm3 = ClockMapping(ref_src, ref_utc, offset_seconds=0.0, drift_rate_ppm=0.0, confidence=1.0, mapping_version="v1", valid_until_utc=1500.0)
    mapper3 = ClockMapper(cm3)
    assert mapper3.map_to_utc(1010.0, TimestampDomain.ECU_BOOT, ingestion_utc=2000.0) is None


def test_12_unresolved_timestamp_synchronization_rejection():
    """12. Physically valid but temporally invalid sample (is_sync_eligible=False) is NOT consumed by TimestampSynchronizer."""
    sync = TimestampSynchronizer()
    from src.module01.buffering.ring_buffer import RingBuffer
    buf = RingBuffer()

    ts = TimestampModel(100.0, TimestampDomain.ECU_BOOT, None, 100.0, 100.0, 1000)
    m = SensorMeasurement(
        measurement_id="m_unresolved",
        parameter_id="engine.rpm",
        value=544.5,
        engineering_value=5200.0,
        raw_signal=None,
        unit_metadata=UnitNormalizer.get_unit_metadata("RPM"),
        validity_status=ValidityStatus.VALID,
        temporal_quality=TemporalQuality.UNRESOLVED_CLOCK,
        transformation_metadata=TransformationMetadata.NORMALIZED,
        integrity_status=IntegrityStatus.ORIGINAL,
        is_physically_valid=True,
        is_temporally_valid=False,
        is_sync_eligible=False,
        physical_origin=PhysicalOrigin.ECU,
        transport_protocol=TransportProtocol.CAN,
        processing_context=ProcessingContext.LIVE_STREAM,
        state_category=StateCategory.ACTUAL_MEASURED,
        timestamps=ts,
        lineage=MeasurementLineage(),
    )
    buf.push(m)

    frame = sync.generate_frame(target_grid_timestamp_utc=100.0, channel_buffers={"engine.rpm": buf}, causal_mode=True)
    assert frame.get_measurement("engine.rpm") is None


def test_13_out_of_order_normalized_storage(temp_dir):
    """13. Out-of-order ingestion sorted deterministically by SOURCE_EVENT_ORDER in NormalizedStore."""
    file_path = temp_dir / "norm.jsonl"
    store = NormalizedStore(file_path)

    ts1 = TimestampModel(10.0, TimestampDomain.UTC, 10.0, 10.0, 10.0, 1000)
    ts2 = TimestampModel(20.0, TimestampDomain.UTC, 20.0, 20.0, 20.0, 2000)

    m1 = SensorMeasurement.create_valid("m1", "engine.rpm", 500.0, 5000.0, UnitNormalizer.get_unit_metadata("RPM"), ts1, MeasurementLineage(raw_packet_id="pkt_10"))
    m2 = SensorMeasurement.create_valid("m2", "engine.rpm", 600.0, 6000.0, UnitNormalizer.get_unit_metadata("RPM"), ts2, MeasurementLineage(raw_packet_id="pkt_20"))

    store.append_measurement(m2)
    store.append_measurement(m1)

    ordered = store.get_ordered_records()
    assert len(ordered) == 2
    assert ordered[0]["source_event_timestamp"] == 10.0
    assert ordered[1]["source_event_timestamp"] == 20.0


def test_14_duplicate_retransmission_conflict_detection():
    """14. Transmission integrity detection: EXACT_DUPLICATE, RETRANSMISSION, CONFLICTING_PAYLOAD."""
    pipeline = IngestionPipeline()

    p1 = DeepImmutableRawPacket.create(PhysicalOrigin.ECU, TransportProtocol.CAN, "can0", 101, b"payload_A", 100.0, 1000, source_timestamp=100.0)
    p2 = DeepImmutableRawPacket.create(PhysicalOrigin.ECU, TransportProtocol.CAN, "can0", 101, b"payload_A", 101.0, 2000, source_timestamp=101.0)
    p3 = DeepImmutableRawPacket.create(PhysicalOrigin.ECU, TransportProtocol.CAN, "can0", 101, b"payload_B_CONFLICT", 102.0, 3000, source_timestamp=102.0)

    assert pipeline._classify_integrity_status(p1) == IntegrityStatus.ORIGINAL
    assert pipeline._classify_integrity_status(p1) == IntegrityStatus.EXACT_DUPLICATE
    assert pipeline._classify_integrity_status(p2) == IntegrityStatus.RETRANSMISSION
    assert pipeline._classify_integrity_status(p3) == IntegrityStatus.CONFLICTING_PAYLOAD


def test_15_raw_packet_lineage_resolution(temp_dir):
    """15. Raw packet lineage resolution using resolve_raw_packet()."""
    raw_path = temp_dir / "raw.jsonl"
    store = RawStore(raw_path)

    now = time.time()
    p = DeepImmutableRawPacket.create(PhysicalOrigin.ECU, TransportProtocol.CAN, "can0", 55, b"lineage_payload", now, time.monotonic_ns())

    store.append(p)
    resolved = store.get_by_packet_id(p.packet_id)

    assert resolved is not None
    assert resolved.packet_id == p.packet_id
    assert resolved.raw_bytes == b"lineage_payload"


def test_16_mission_id_contract():
    """16. Mission ID contract for historical stream retrieval."""
    pipeline = IngestionPipeline()
    tr = TimeRange(start_time=0.0, end_time=1.0, timestamp_domain=TimestampDomain.UTC)
    stream = pipeline.get_historical_stream("mission_001", tr)
    assert iter(stream) is not None


def test_17_pipeline_healthy_storage_no_name_error(temp_dir):
    """17. Regression test: Verify healthy storage in IngestionPipeline without NameError or false storage failures."""
    pipeline = IngestionPipeline()

    assert pipeline.storage_recovery.state == StorageRecoveryState.NORMAL

    now = time.time()
    pkt = DeepImmutableRawPacket.create(
        physical_origin=PhysicalOrigin.SIMULATOR,
        transport_protocol=TransportProtocol.API,
        stream_id="ecu0",
        sequence_number=1,
        raw_bytes=b'{"engine_rpm": 5200.0}',
        ingestion_timestamp_utc=now,
        monotonic_ingestion_nanos=time.monotonic_ns(),
        source_timestamp=now,
        metadata={"state_category": StateCategory.SIMULATED.value},
    )

    success = pipeline.ingest_raw_packet(pkt)
    assert success is True

    metrics = pipeline.get_ingestion_metrics()
    assert metrics["records_received_total"] == 1
    assert metrics["storage_failures_total"] == 0
    assert metrics["storage_recovery_state"] == "NORMAL"

    assert pipeline.raw_store.contains(pkt.packet_id)
    ordered_norm = pipeline.normalized_store.get_ordered_records()
    assert len(ordered_norm) > 0
    assert ordered_norm[-1]["raw_packet_id"] == pkt.packet_id


def test_18_rpm_validity_unit_contract_and_boundary_limits():
    """
    18. BUG-01 Regression Test: Verify RPM physical plausibility validation unit contract.
    Ensures ValidityValidator and sensor_validity_limits.yaml operate consistently in RAD_PER_SEC canonical SI units.
    """
    loader = ConfigLoader()
    limits_cfg = loader.load_validity_limits()
    sensor_cfg = loader.load_sensor_definitions()
    validator = ValidityValidator(limits_cfg, sensor_cfg)
    now = time.time()
    ts = TimestampModel(
        source_timestamp=now,
        source_timestamp_domain=TimestampDomain.UTC,
        normalized_source_utc=now,
        ingestion_timestamp_utc=now,
        processing_timestamp_utc=now,
        monotonic_ingestion_nanos=time.monotonic_ns(),
    )

    def validate_rpm(raw_rpm: float) -> SensorMeasurement:
        sig = DecodedSignal("sig_rpm", "engine.rpm", raw_rpm, "RPM", now, TimestampDomain.UTC, "pkt_rpm")
        return validator.validate_and_create_measurement(sig, ts)

    # 1. Below minimum (-10 RPM) -> OUT_OF_RANGE
    m_below = validate_rpm(-10.0)
    assert m_below.is_physically_valid is False
    assert m_below.validity_status == ValidityStatus.OUT_OF_RANGE

    # 2. Exact minimum (0 RPM) -> VALID
    m_min = validate_rpm(0.0)
    assert m_min.is_physically_valid is True
    assert m_min.validity_status == ValidityStatus.VALID

    # 3. Normal operating value (5200 RPM) -> VALID
    m_normal = validate_rpm(5200.0)
    assert m_normal.is_physically_valid is True
    assert m_normal.validity_status == ValidityStatus.VALID
    assert m_normal.value == pytest.approx(544.5427266, rel=1e-5) # RAD_PER_SEC

    # 4. Exact maximum (7000 RPM) -> VALID
    m_max = validate_rpm(7000.0)
    assert m_max.is_physically_valid is True
    assert m_max.validity_status == ValidityStatus.VALID
    assert m_max.value == pytest.approx(733.0382858, rel=1e-5) # RAD_PER_SEC

    # 5. Just above maximum (7001 RPM) -> OUT_OF_RANGE
    m_above = validate_rpm(7001.0)
    assert m_above.is_physically_valid is False
    assert m_above.validity_status == ValidityStatus.OUT_OF_RANGE

    # 6. Clearly above maximum (8000 RPM) -> OUT_OF_RANGE
    m_high = validate_rpm(8000.0)
    assert m_high.is_physically_valid is False
    assert m_high.validity_status == ValidityStatus.OUT_OF_RANGE

    # 7. Numerical non-plausible (NaN & Inf) -> INVALID
    m_nan = validate_rpm(math.nan)
    assert m_nan.is_physically_valid is False
    assert m_nan.validity_status == ValidityStatus.INVALID

    m_inf = validate_rpm(math.inf)
    assert m_inf.is_physically_valid is False
    assert m_inf.validity_status == ValidityStatus.INVALID
