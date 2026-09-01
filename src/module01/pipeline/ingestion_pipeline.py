"""
Module 01 Main Ingestion Pipeline Orchestrator (V4.3 Import Fix).
SIH26054 — Data Acquisition & Ingestion Subsystem.
"""

import threading
import time
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Tuple

from src.module01.buffering.ring_buffer import RingBuffer
from src.module01.config.config_loader import ConfigLoader
from src.module01.decoding.can_decoder import CanDecoder
from src.module01.decoding.csv_decoder import CsvDecoder
from src.module01.decoding.interfaces import DecoderError, TelemetryDecoder
from src.module01.decoding.json_decoder import JsonDecoder
from src.module01.interfaces.contracts import (
    IDigitalTwinTelemetryStream,
    IReplayTelemetryProvider,
    ISimulationTelemetrySink,
    LineageResolver,
    MetricsProvider,
    TelemetryConsumer,
    TelemetryIngestor,
    TelemetryPublisher,
    TimeRange,
)
from src.module01.models.enums import (
    IntegrityStatus,
    ParameterClassification,
    PhysicalOrigin,
    ProcessingContext,
    StateCategory,
    StorageRecoveryState,
    TimestampDomain,
    TransportProtocol,
)
from src.module01.models.metadata import MeasurementLineage
from src.module01.models.raw_packet import DeepImmutableRawPacket, RawCanFrame
from src.module01.models.sensor_sample import SensorMeasurement
from src.module01.models.telemetry_frame import TelemetryFrame
from src.module01.observability.metrics import MetricsTracker
from src.module01.storage.datastore import NormalizedStore, RawStore, StorageRecoveryStateMachine
from src.module01.synchronization.time_synchronizer import TimestampSynchronizer
from src.module01.timestamps.clock_mapper import ClockMapper
from src.module01.validation.validity_validator import ValidityValidator


class IngestionPipeline(
    TelemetryIngestor,
    TelemetryPublisher,
    TelemetryConsumer,
    LineageResolver,
    MetricsProvider,
    ISimulationTelemetrySink,
    IReplayTelemetryProvider,
    IDigitalTwinTelemetryStream,
):
    """
    Main orchestrator for Module 01 executing the 4-stage pipeline flow:
    Raw Immutability -> Decode -> SI Normalize -> Validate -> Buffer -> Synchronize -> Frame
    """

    ALLOWED_ACTUAL_ORIGINS = frozenset({
        PhysicalOrigin.SENSOR,
        PhysicalOrigin.ECU,
        PhysicalOrigin.FADEC,
    })

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        if config_loader is None:
            config_loader = ConfigLoader()

        self.config_loader = config_loader
        self.acq_config = config_loader.load_acquisition_config()
        self.sensor_defs = config_loader.load_sensor_definitions()
        self.validity_limits = config_loader.load_validity_limits()
        self.can_mappings = config_loader.load_can_mappings()

        # Decoders
        self.can_decoder = CanDecoder(self.can_mappings)
        self.json_decoder = JsonDecoder(self.sensor_defs)
        self.csv_decoder = CsvDecoder(self.sensor_defs)

        # Validator & Clock Mapper
        self.validator = ValidityValidator(self.validity_limits, self.sensor_defs)
        self.clock_mapper = ClockMapper()
        self.synchronizer = TimestampSynchronizer(
            staleness_limit_seconds=self.acq_config["pipeline"].get("staleness_timeout_seconds", 5.0)
        )

        # Per-channel RingBuffers
        buffer_cap = self.acq_config["buffering"].get("max_ring_buffer_capacity", 10000)
        drop_pol = self.acq_config["buffering"].get("backpressure_drop_policy", "DROP_OLDEST")
        self.channel_buffers: Dict[str, RingBuffer] = {}
        for sensor_id in self.sensor_defs.get("sensors", {}):
            self.channel_buffers[sensor_id] = RingBuffer(capacity=buffer_cap, drop_policy=drop_pol)

        # Storage & Recovery
        raw_path = self.acq_config["storage"].get("raw_store_path", "storage/raw_store.jsonl")
        norm_path = self.acq_config["storage"].get("normalized_store_path", "storage/normalized_store.jsonl")
        self.raw_store = RawStore(raw_path)
        self.normalized_store = NormalizedStore(norm_path)
        self.storage_recovery = StorageRecoveryStateMachine(
            emergency_buffer_capacity=self.acq_config["buffering"].get("emergency_storage_buffer_capacity", 50000)
        )

        # Observability
        self.metrics = MetricsTracker()

        # Lock & Subscriber Callbacks
        self._lock = threading.Lock()
        self._latest_frame: Optional[TelemetryFrame] = None
        self._general_subscribers: Dict[str, Callable[[TelemetryFrame], None]] = {}
        self._actual_state_subscribers: Dict[str, Callable[[TelemetryFrame], None]] = {}
        self._sub_counter = 0

        # Duplicate / Retransmission / Conflict Packet Indices
        self._packet_id_index: Dict[str, bytes] = {}
        self._sequence_index: Dict[Tuple[str, int], Tuple[str, bytes]] = {}

        # Parameter-to-lineage index: measurement_id -> MeasurementLineage
        self._lineage_index: Dict[str, MeasurementLineage] = {}

    # =========================================================================
    # Duplicate / Retransmission / Conflict Classification
    # =========================================================================

    def _classify_integrity_status(self, packet: DeepImmutableRawPacket) -> IntegrityStatus:
        with self._lock:
            pid = packet.packet_id
            seq_key = (packet.stream_id, packet.sequence_number)
            raw_bytes = packet.raw_bytes

            if pid in self._packet_id_index:
                self.metrics.increment("duplicate_total")
                return IntegrityStatus.EXACT_DUPLICATE

            if seq_key in self._sequence_index:
                existing_pid, existing_bytes = self._sequence_index[seq_key]
                if existing_bytes == raw_bytes:
                    self.metrics.increment("duplicate_total")
                    return IntegrityStatus.RETRANSMISSION
                else:
                    self.metrics.increment("conflicting_payload_total")
                    return IntegrityStatus.CONFLICTING_PAYLOAD

            self._packet_id_index[pid] = raw_bytes
            self._sequence_index[seq_key] = (pid, raw_bytes)
            return IntegrityStatus.ORIGINAL

    # =========================================================================
    # Stage 1-4 Pipeline Execution
    # =========================================================================

    def ingest_raw_packet(self, packet: DeepImmutableRawPacket) -> bool:
        """
        Executes pipeline Stage 1 through Stage 4 for a single raw packet.
        Ambiguous File Provenance Rule: For file-origin packets, state_category MUST be explicitly supplied in metadata.
        """
        self.metrics.increment("records_received_total")

        state_cat_meta = packet.metadata.get("state_category")
        if packet.transport_protocol == TransportProtocol.FILE or packet.physical_origin == PhysicalOrigin.UNKNOWN:
            if not state_cat_meta:
                self.metrics.increment("records_physically_invalid_total")
                return False

        integrity_status = self._classify_integrity_status(packet)

        # 1. Raw Immutability & Forensic Raw Storage (Stage 1)
        try:
            if self.storage_recovery.state == StorageRecoveryState.EMERGENCY_BUFFERING:
                self.storage_recovery.handle_storage_failure(packet)
            else:
                self.raw_store.append(packet)
        except Exception:
            self.metrics.increment("storage_failures_total")
            self.storage_recovery.handle_storage_failure(packet)

        # Determine transport decoder
        if packet.transport_protocol == TransportProtocol.CAN or packet.transport_protocol == TransportProtocol.SOCKETCAN:
            decoder: TelemetryDecoder = self.can_decoder
        elif packet.metadata.get("protocol") == "JSON_ECU_V1" or packet.transport_protocol == TransportProtocol.API:
            decoder = self.json_decoder
        else:
            decoder = self.json_decoder

        # 2. Decoding & SI Unit Normalization (Stage 2)
        try:
            decoded_signals = decoder.decode(packet)
            self.metrics.increment("records_decoded_total", len(decoded_signals))
        except DecoderError:
            self.metrics.increment("records_physically_invalid_total")
            return False

        state_cat = StateCategory(state_cat_meta) if state_cat_meta else StateCategory.ACTUAL_MEASURED

        # 3. Validation & Quality/Usability Flagging (Stage 3)
        for decoded in decoded_signals:
            ts_model = self.clock_mapper.create_timestamp_model(
                source_timestamp=decoded.source_timestamp,
                domain=decoded.source_timestamp_domain,
                ingestion_utc=packet.ingestion_timestamp_utc,
                monotonic_nanos=packet.monotonic_ingestion_nanos,
            )

            if ts_model.normalized_source_utc is None and decoded.source_timestamp_domain != TimestampDomain.UTC:
                self.metrics.increment("unresolved_clock_total")

            measurement = self.validator.validate_and_create_measurement(
                decoded_signal=decoded,
                timestamps=ts_model,
                physical_origin=packet.physical_origin,
                transport_protocol=packet.transport_protocol,
                processing_context=ProcessingContext(packet.metadata.get("processing_context", "LIVE_STREAM")),
                state_category=state_cat,
                integrity_status=integrity_status,
            )

            with self._lock:
                self._lineage_index[measurement.measurement_id] = measurement.lineage

            if measurement.is_physically_valid:
                self.metrics.increment("records_physically_valid_total")
            else:
                self.metrics.increment("records_physically_invalid_total")

            # 4. Multi-Rate Buffering & Storage (Stage 4)
            param_id = measurement.parameter_id
            if param_id not in self.channel_buffers:
                buffer_cap = self.acq_config["buffering"].get("max_ring_buffer_capacity", 10000)
                drop_pol = self.acq_config["buffering"].get("backpressure_drop_policy", "DROP_OLDEST")
                self.channel_buffers[param_id] = RingBuffer(capacity=buffer_cap, drop_policy=drop_pol)

            pushed = self.channel_buffers[param_id].push(measurement)
            if not pushed:
                self.metrics.increment("dropped_records_total")

            try:
                self.normalized_store.append_measurement(measurement)
            except Exception:
                self.metrics.increment("storage_failures_total")

        return True

    # =========================================================================
    # Synchronization & Frame Generation
    # =========================================================================

    def generate_and_publish_frame(
        self,
        target_grid_utc: float,
        causal_mode: bool = True,
        mission_start_utc: Optional[float] = None,
    ) -> TelemetryFrame:
        frame = self.synchronizer.generate_frame(
            target_grid_timestamp_utc=target_grid_utc,
            channel_buffers=self.channel_buffers,
            causal_mode=causal_mode,
            mission_start_utc=mission_start_utc,
        )

        with self._lock:
            self._latest_frame = frame

        self.publish_frame(frame)
        return frame

    def publish_frame(self, frame: TelemetryFrame) -> None:
        with self._lock:
            gen_callbacks = list(self._general_subscribers.values())
            act_callbacks = list(self._actual_state_subscribers.values())

        for cb in gen_callbacks:
            try:
                cb(frame)
            except Exception:
                pass

        if act_callbacks and frame.measurements:
            is_pure_actual = True
            for m in frame.measurements.values():
                if m.state_category != StateCategory.ACTUAL_MEASURED or m.physical_origin not in self.ALLOWED_ACTUAL_ORIGINS:
                    is_pure_actual = False
                    break

            if is_pure_actual:
                for cb in act_callbacks:
                    try:
                        cb(frame)
                    except Exception:
                        pass

    def get_latest_frame(self) -> Optional[TelemetryFrame]:
        with self._lock:
            return self._latest_frame

    def get_frame_range(self, time_range: TimeRange, causal_mode: bool = True) -> List[TelemetryFrame]:
        if time_range.timestamp_domain != TimestampDomain.UTC:
            raise ValueError(f"Unsupported TimeRange domain '{time_range.timestamp_domain.value}' for UTC grid frame synchronization")

        frames = []
        dt = 0.02  # 50 Hz grid
        t = time_range.start_time
        while t <= time_range.end_time:
            frame = self.synchronizer.generate_frame(
                target_grid_timestamp_utc=t,
                channel_buffers=self.channel_buffers,
                causal_mode=causal_mode,
            )
            frames.append(frame)
            t += dt
        return frames

    # =========================================================================
    # Lineage & Metrics Provider
    # =========================================================================

    def resolve_raw_packet(self, raw_packet_id: str) -> Optional[DeepImmutableRawPacket]:
        return self.raw_store.get_by_packet_id(raw_packet_id)

    def resolve_measurement_lineage(self, measurement_id: str) -> Optional[MeasurementLineage]:
        with self._lock:
            return self._lineage_index.get(measurement_id)

    def get_ingestion_metrics(self) -> Dict[str, Any]:
        snap = self.metrics.get_snapshot()
        snap["storage_recovery_state"] = self.storage_recovery.state.value
        snap["dropped_records_total"] += self.storage_recovery.dropped_records_total
        return snap

    # =========================================================================
    # Module 02 & Module 03 Interfaces (Strict Provenance Compliance)
    # =========================================================================

    def inject_simulated_measurement(self, measurement: SensorMeasurement) -> bool:
        if measurement.physical_origin != PhysicalOrigin.SIMULATOR or measurement.state_category != StateCategory.SIMULATED:
            return False

        param_id = measurement.parameter_id
        if param_id not in self.channel_buffers:
            buffer_cap = self.acq_config["buffering"].get("max_ring_buffer_capacity", 10000)
            self.channel_buffers[param_id] = RingBuffer(capacity=buffer_cap)

        self.channel_buffers[param_id].push(measurement)
        return True

    def inject_simulated_frame(self, frame: TelemetryFrame) -> bool:
        if not frame.measurements:
            return False

        for meas in frame.measurements.values():
            if meas.physical_origin != PhysicalOrigin.SIMULATOR or meas.state_category != StateCategory.SIMULATED:
                return False

        self.publish_frame(frame)
        return True

    def get_historical_stream(self, mission_id: str, time_range: TimeRange) -> Iterator[TelemetryFrame]:
        """
        Demonstration placeholder method contract for Module 02 historical replay retrieval.
        NOTE: Module 01 provides the interface contract only. Mission-aware historical replay
        and physics reconstruction are deferred to Module 02.
        """
        frames = self.get_frame_range(time_range=time_range, causal_mode=False)
        return iter(frames)

    def subscribe_actual_state(self, callback: Callable[[TelemetryFrame], None]) -> str:
        with self._lock:
            self._sub_counter += 1
            sub_id = f"act_sub_{self._sub_counter}"
            self._actual_state_subscribers[sub_id] = callback
            return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        with self._lock:
            if subscription_id in self._actual_state_subscribers:
                del self._actual_state_subscribers[subscription_id]
                return True
            if subscription_id in self._general_subscribers:
                del self._general_subscribers[subscription_id]
                return True
            return False
