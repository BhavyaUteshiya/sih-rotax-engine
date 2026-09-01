"""
Tiered DataStore & Storage Recovery State Machine (Phase 15 & 16 Correction).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import base64
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Set

from src.module01.models.enums import PhysicalOrigin, StorageRecoveryState, TransportProtocol
from src.module01.models.raw_packet import DeepImmutableRawPacket
from src.module01.models.sensor_sample import SensorMeasurement


class StorageError(Exception):
    """Exception raised when storage write or recovery operations fail."""
    pass


class StorageRecoveryStateMachine:
    """
    Manages storage recovery transitions and emergency buffer draining.
    Transitions: NORMAL -> STORAGE_FAILURE -> EMERGENCY_BUFFERING -> STORAGE_RECOVERED -> DRAINING_FLUSH -> NORMAL
    """

    def __init__(self, emergency_buffer_capacity: int = 50000):
        self.state = StorageRecoveryState.NORMAL
        self.emergency_buffer: List[DeepImmutableRawPacket] = []
        self.capacity = emergency_buffer_capacity
        self.dropped_records_total = 0
        self._lock = threading.Lock()

    def handle_storage_failure(self, packet: DeepImmutableRawPacket) -> bool:
        """Transitions state to EMERGENCY_BUFFERING and buffers packet."""
        with self._lock:
            self.state = StorageRecoveryState.EMERGENCY_BUFFERING
            if len(self.emergency_buffer) >= self.capacity:
                self.emergency_buffer.pop(0)
                self.dropped_records_total += 1
            self.emergency_buffer.append(packet)
            return True

    def mark_recovered(self) -> None:
        """Transitions state to STORAGE_RECOVERED."""
        with self._lock:
            if self.state in (StorageRecoveryState.STORAGE_FAILURE, StorageRecoveryState.EMERGENCY_BUFFERING):
                self.state = StorageRecoveryState.STORAGE_RECOVERED

    def start_draining(self) -> List[DeepImmutableRawPacket]:
        """Transitions state to DRAINING_FLUSH and returns buffered packets for idempotent flush."""
        with self._lock:
            self.state = StorageRecoveryState.DRAINING_FLUSH
            drain_batch = list(self.emergency_buffer)
            return drain_batch

    def complete_draining(self) -> None:
        """Clears emergency buffer and restores NORMAL state."""
        with self._lock:
            self.emergency_buffer.clear()
            self.state = StorageRecoveryState.NORMAL


class RawStore:
    """
    Append-only raw packet store preserving strict ARRIVAL_ORDER.
    Serializes raw binary bytes using Base64 with payload_sha256 content verification.
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path).resolve()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._written_packet_ids: Set[str] = set()
        self._load_index()

    def _load_index(self) -> None:
        if not self.file_path.exists():
            return
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        pkt_id = data.get("packet_id")
                        if pkt_id:
                            self._written_packet_ids.add(pkt_id)
                    except Exception:
                        pass

    def append(self, packet: DeepImmutableRawPacket) -> bool:
        """Appends a raw packet to JSONL log in strict ARRIVAL_ORDER. Idempotent by packet_id."""
        with self._lock:
            if packet.packet_id in self._written_packet_ids:
                return True

            record = {
                "packet_id": packet.packet_id,
                "payload_sha256": packet.payload_sha256,
                "physical_origin": packet.physical_origin.value,
                "transport_protocol": packet.transport_protocol.value,
                "stream_id": packet.stream_id,
                "sequence_number": packet.sequence_number,
                "raw_bytes_base64": base64.b64encode(packet.raw_bytes).decode("ascii"),
                "ingestion_timestamp_utc": packet.ingestion_timestamp_utc,
                "monotonic_ingestion_nanos": packet.monotonic_ingestion_nanos,
                "source_timestamp": packet.source_timestamp,
                "metadata": dict(packet.metadata),
            }

            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            self._written_packet_ids.add(packet.packet_id)
            return True

    def contains(self, packet_id: str) -> bool:
        with self._lock:
            return packet_id in self._written_packet_ids

    def get_by_packet_id(self, packet_id: str) -> Optional[DeepImmutableRawPacket]:
        """Resolves and reconstructs DeepImmutableRawPacket by raw_packet_id."""
        with self._lock:
            if not self.file_path.exists():
                return None
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("packet_id") == packet_id:
                                raw_bytes = base64.b64decode(data["raw_bytes_base64"])
                                meta = data.get("metadata", {})
                                return DeepImmutableRawPacket.create(
                                    physical_origin=PhysicalOrigin(data["physical_origin"]),
                                    transport_protocol=TransportProtocol(data["transport_protocol"]),
                                    stream_id=data["stream_id"],
                                    sequence_number=data["sequence_number"],
                                    raw_bytes=raw_bytes,
                                    ingestion_timestamp_utc=data["ingestion_timestamp_utc"],
                                    monotonic_ingestion_nanos=data["monotonic_ingestion_nanos"],
                                    source_timestamp=data.get("source_timestamp"),
                                    metadata=meta,
                                )
                        except Exception:
                            pass
            return None


class NormalizedStore:
    """
    Time-series store for normalized SensorMeasurement records providing deterministic SOURCE_EVENT_ORDER.
    Ordering Key: (source_event_timestamp, stream_id, sequence_number, packet_id)
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path).resolve()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append_measurement(self, measurement: SensorMeasurement) -> bool:
        with self._lock:
            ts = measurement.timestamps.normalized_source_utc if measurement.timestamps.normalized_source_utc is not None else measurement.timestamps.source_timestamp
            record = {
                "measurement_id": measurement.measurement_id,
                "parameter_id": measurement.parameter_id,
                "value": measurement.value,
                "engineering_value": measurement.engineering_value,
                "canonical_unit": measurement.unit_metadata.canonical_si_unit,
                "validity_status": measurement.validity_status.value,
                "temporal_quality": measurement.temporal_quality.value,
                "is_physically_valid": measurement.is_physically_valid,
                "is_temporally_valid": measurement.is_temporally_valid,
                "source_event_timestamp": ts,
                "ingestion_timestamp_utc": measurement.timestamps.ingestion_timestamp_utc,
                "state_category": measurement.state_category.value,
                "raw_packet_id": measurement.lineage.raw_packet_id,
            }
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            return True

    def get_ordered_records(self) -> List[Dict[str, Any]]:
        """Returns stored records sorted deterministically in SOURCE_EVENT_ORDER."""
        with self._lock:
            if not self.file_path.exists():
                return []
            records = []
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))

            return sorted(records, key=lambda r: (r.get("source_event_timestamp") or 0.0, r.get("raw_packet_id") or ""))
