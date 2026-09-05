"""
Metadata Data Structures Specification (V4.3 Compliant).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from src.module01.models.enums import AlignmentMethod, TimestampDomain


@dataclass(frozen=True)
class UnitMetadata:
    """Explicit unit metadata tracking raw, engineering, and canonical SI tiers."""
    raw_unit: str                               # e.g., "RPM", "DEGC", "PSI"
    engineering_unit: str                       # e.g., "RPM", "°C", "bar"
    canonical_si_unit: str                      # e.g., "RAD_PER_SEC", "KELVIN", "PASCAL"
    scale_factor: float = 1.0                   # Multiplicative conversion factor to SI
    offset: float = 0.0                         # Additive offset for SI conversion


@dataclass(frozen=True)
class ClockMapping:
    """Clock mapping & calibration metadata for converting source time to UTC."""
    reference_source_timestamp: float           # Reference timestamp in source clock domain
    reference_utc: float                        # Reference UTC timestamp corresponding to ref source ts
    offset_seconds: float                       # Constant offset in seconds
    drift_rate_ppm: float                       # Clock drift rate in parts per million
    confidence: float                           # Mapping confidence score [0.0 - 1.0]
    mapping_version: str                        # Version hash of mapping calibration
    valid_until_utc: float                      # Expiration UTC timestamp of calibration


@dataclass(frozen=True)
class TimestampModel:
    """Multi-domain timestamp container."""
    source_timestamp: float                     # Raw timestamp emitted by source
    source_timestamp_domain: TimestampDomain    # Domain of raw source timestamp
    normalized_source_utc: Optional[float]      # Converted UTC epoch seconds (None if unresolvable)
    ingestion_timestamp_utc: float              # Host UTC epoch seconds recorded upon pipeline entry
    processing_timestamp_utc: float             # Host UTC epoch seconds upon validation
    monotonic_ingestion_nanos: int              # Host monotonic clock tick for latency tracking
    mission_start_timestamp_utc: Optional[float] = None # UTC timestamp of mission start (t0)
    mission_elapsed_seconds: Optional[float] = None     # Seconds elapsed since mission start
    clock_mapping: Optional[ClockMapping] = None # Clock calibration mapping metadata


@dataclass(frozen=True)
class MeasurementLineage:
    """Complete 4-stage processing lineage tracking."""
    raw_packet_id: Optional[str] = None          # Link to DeepImmutableRawPacket
    input_measurement_ids: Tuple[str, ...] = ()  # Input measurement IDs (for DERIVED)
    source_sample_ids: Tuple[str, ...] = ()      # Source sample IDs (for INTERPOLATED)
    simulation_run_id: Optional[str] = None      # Simulation run UUID (for SIMULATED)
    simulation_config_hash: Optional[str] = None # Config hash (for SIMULATED)
    model_version: Optional[str] = None          # Model version (for DERIVED / SIMULATED)


@dataclass(frozen=True)
class AlignmentMetadata:
    """Frame alignment details for individual synchronized measurements."""
    alignment_method: AlignmentMethod
    target_grid_timestamp: float                # Grid timestamp in target domain
    target_domain: TimestampDomain              # Domain of target grid timestamp
    sample_timestamps_used: Tuple[float, ...]
    time_distance_seconds: float
    is_causal: bool                             # True if REALTIME_CAUSAL_MODE (strictly no look-ahead)


@dataclass(frozen=True)
class SyncMetadata:
    """Overall TelemetryFrame synchronization metadata."""
    alignment_mode: str                         # "REALTIME_CAUSAL" or "OFFLINE_REPLAY"
    target_grid_dt: float                       # Grid time step in seconds
    sync_quality_score: float                   # Aggregated grid quality score [0.0 - 1.0]
    total_channels: int
    valid_channels: int
    latency_ms: float


@dataclass(frozen=True)
class FrameTime:
    """Flexible multi-domain frame timestamp container."""
    primary_timestamp: float                     # Authoritative timestamp value for frame grid
    primary_timestamp_domain: TimestampDomain    # Domain of primary timestamp
    normalized_utc: Optional[float]              # UTC epoch seconds (None if unresolvable)
    mission_elapsed_seconds: Optional[float]     # Seconds elapsed since mission start
    sync_quality_score: float                    # Alignment confidence score [0.0 - 1.0]
    clock_mapping_version: str                   # Version hash of active ClockMapping


@dataclass(frozen=True)
class DecodedSignal:
    """Layer 2 decoded raw signal before unit normalization and validation."""
    signal_id: str
    parameter_id: str
    raw_numeric_value: Any                       # Unscaled decoded raw value (e.g. unscaled integer from CAN)
    raw_unit: str
    source_timestamp: float
    source_timestamp_domain: TimestampDomain
    raw_packet_id: str
    decoding_metadata: Dict[str, Any] = field(default_factory=dict)
