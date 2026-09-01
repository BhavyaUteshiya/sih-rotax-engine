"""
Deeply Immutable Raw Packet & Canonical Hashing Specification (Phases 3 & 4).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import copy
import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Optional, Tuple

from src.module01.models.enums import PhysicalOrigin, TransportProtocol


def compute_payload_sha256(raw_bytes: bytes) -> str:
    """
    Computes lower-case 64-character SHA-256 hash over raw payload bytes.
    """
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise TypeError("raw_bytes must be bytes or bytearray")
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_packet_id(
    stream_id: str,
    sequence_number: int,
    source_timestamp: Optional[float],
    payload_sha256: str,
) -> str:
    """
    Computes deterministic packet_id using V4.3 canonical serialization:
    canonical_str = f"{stream_id}:{sequence_number}:{source_timestamp_repr}:{payload_sha256}"
    packet_id = sha256(canonical_str.encode('utf-8')).hexdigest()
    """
    if not isinstance(stream_id, str):
        raise TypeError("stream_id must be a string")
    if not isinstance(sequence_number, int):
        raise TypeError("sequence_number must be an integer")
    if not isinstance(payload_sha256, str) or len(payload_sha256) != 64:
        raise ValueError("payload_sha256 must be a 64-character hex string")

    if source_timestamp is None:
        source_ts_repr = "NULL"
    else:
        source_ts_repr = "{:.6f}".format(float(source_timestamp))

    canonical_str = f"{stream_id}:{sequence_number}:{source_ts_repr}:{payload_sha256}"
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def _deep_freeze_metadata(data: Dict[str, Any]) -> MappingProxyType:
    """
    Recursively freezes a nested dictionary using deep defensive copies and MappingProxyType/tuples.
    """
    copied = copy.deepcopy(data)

    def _freeze(obj: Any) -> Any:
        if isinstance(obj, dict):
            return MappingProxyType({k: _freeze(v) for k, v in obj.items()})
        elif isinstance(obj, list):
            return tuple(_freeze(item) for item in obj)
        elif isinstance(obj, set):
            return tuple(_freeze(item) for item in obj)
        return obj

    frozen = _freeze(copied)
    if isinstance(frozen, MappingProxyType):
        return frozen
    return MappingProxyType(dict(frozen))


@dataclass(frozen=True)
class DeepImmutableRawPacket:
    """
    Deeply immutable raw packet representation preserving forensic wire payload integrity.
    Once accepted, raw bytes and metadata CANNOT be mutated.
    """
    packet_id: str                              # Event identity hash (sha256 of canonical_str)
    payload_sha256: str                         # Content integrity hash (sha256 of raw_bytes)
    physical_origin: PhysicalOrigin             # SENSOR, ECU, FADEC, SIMULATOR, etc.
    transport_protocol: TransportProtocol       # CAN, SOCKETCAN, FILE, MEMORY, etc.
    stream_id: str                              # Interface/channel identifier (e.g. "can0")
    sequence_number: int                        # Protocol sequence number
    raw_bytes: bytes                            # Immutable raw byte payload
    ingestion_timestamp_utc: float              # Host UTC epoch seconds recorded upon pipeline entry
    monotonic_ingestion_nanos: int              # Host monotonic clock tick
    source_timestamp: Optional[float]           # Raw source event timestamp if available
    metadata: MappingProxyType                  # Deeply immutable metadata proxy

    @classmethod
    def create(
        cls,
        physical_origin: PhysicalOrigin,
        transport_protocol: TransportProtocol,
        stream_id: str,
        sequence_number: int,
        raw_bytes: bytes,
        ingestion_timestamp_utc: float,
        monotonic_ingestion_nanos: int,
        source_timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "DeepImmutableRawPacket":
        """
        Factory method to construct a DeepImmutableRawPacket with deep defensive copy & frozen metadata.
        """
        if not isinstance(raw_bytes, bytes):
            raw_bytes = bytes(raw_bytes)
        
        sha256_hash = compute_payload_sha256(raw_bytes)
        pkt_id = compute_packet_id(stream_id, sequence_number, source_timestamp, sha256_hash)
        
        meta_dict = metadata if metadata is not None else {}
        frozen_meta = _deep_freeze_metadata(meta_dict)

        return cls(
            packet_id=pkt_id,
            payload_sha256=sha256_hash,
            physical_origin=physical_origin,
            transport_protocol=transport_protocol,
            stream_id=stream_id,
            sequence_number=sequence_number,
            raw_bytes=raw_bytes,
            ingestion_timestamp_utc=ingestion_timestamp_utc,
            monotonic_ingestion_nanos=monotonic_ingestion_nanos,
            source_timestamp=source_timestamp,
            metadata=frozen_meta,
        )


@dataclass(frozen=True)
class RawCanFrame:
    """
    Immutable raw CAN frame representation wrapping CAN-specific protocol fields.
    """
    raw_packet: DeepImmutableRawPacket
    can_id: int                                  # 11-bit standard or 29-bit extended CAN arbitration ID
    dlc: int                                     # Data Length Code (0-8 or 0-64 for CAN-FD)
    is_extended: bool                            # Extended frame flag
    interface_name: str                          # e.g., "can0", "vcan0"

    @property
    def payload(self) -> bytes:
        return self.raw_packet.raw_bytes
