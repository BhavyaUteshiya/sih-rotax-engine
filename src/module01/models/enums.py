"""
Module 01 Core Enums Specification (V4.3 Approved Architecture).
SIH26054 — Digital Twin System for Aero Piston Engines in MALE UAVs.
"""

from enum import Enum


class PhysicalOrigin(Enum):
    """Original physical or synthetic creator of telemetry data."""
    SENSOR = "SENSOR"                           # Physical hardware sensor
    ECU = "ECU"                                 # Engine Control Unit
    FADEC = "FADEC"                             # Full Authority Digital Engine Control
    SIMULATOR = "SIMULATOR"                     # Physics simulator (Module 02 ready)
    DERIVED = "DERIVED"                         # Module 01 mathematical formula
    UNKNOWN = "UNKNOWN"                         # Unspecified source origin


class TransportProtocol(Enum):
    """Transmission interface or wire protocol."""
    CAN = "CAN"                                 # Raw CAN bus
    SOCKETCAN = "SOCKETCAN"                     # Linux SocketCAN interface
    FILE = "FILE"                               # File stream (CSV / JSON / Parquet)
    MEMORY = "MEMORY"                           # In-memory queue / buffer
    API = "API"                                 # Socket / REST / gRPC endpoint
    NONE = "NONE"                               # Direct internal instantiation


class ProcessingContext(Enum):
    """Stream execution context."""
    LIVE_STREAM = "LIVE_STREAM"                 # Real-time UAV flight stream
    HISTORICAL_FILE = "HISTORICAL_FILE"         # Log file ingestion
    FLIGHT_REPLAY = "FLIGHT_REPLAY"             # Flight telemetry replay feed
    SIMULATION_RUN = "SIMULATION_RUN"           # Module 02 simulation execution
    SYNTHETIC_GENERATION = "SYNTHETIC_GENERATION" # Test dataset generator


class StateCategory(Enum):
    """Mathematical/logical observation state category."""
    ACTUAL_MEASURED = "ACTUAL_MEASURED"         # Physical observation
    DERIVED = "DERIVED"                         # Calculated value from measured inputs
    SIMULATED = "SIMULATED"                     # Physics model output (Module 02)
    ESTIMATED = "ESTIMATED"                     # State observer / Twin state output (Module 03)
    PREDICTED = "PREDICTED"                     # Forecast model output (Module 05)


class ValidityStatus(Enum):
    """Physical validity classification."""
    VALID = "VALID"                             # Physically plausible & sound
    INVALID = "INVALID"                         # Parse error, corrupted payload, or unresolvable unit
    OUT_OF_RANGE = "OUT_OF_RANGE"               # Min/Max physical plausibility limit failure
    RATE_OF_CHANGE_VIOLATION = "RATE_OF_CHANGE_VIOLATION" # Unphysical rate-of-change spike


class TemporalQuality(Enum):
    """Timestamp quality & alignment classification."""
    SYNCHRONIZED = "SYNCHRONIZED"               # Aligned to frame time grid
    UNSYNCHRONIZED = "UNSYNCHRONIZED"           # Native sample rate, unaligned
    STALE = "STALE"                             # Value stuck/unchanged beyond freshness limit
    DELAYED = "DELAYED"                         # Received past configured latency window
    UNRESOLVED_CLOCK = "UNRESOLVED_CLOCK"       # Source clock domain cannot be mapped to UTC


class TransformationMetadata(Enum):
    """Data processing transformation stage."""
    RAW = "RAW"                                 # Direct wire payload
    NORMALIZED = "NORMALIZED"                   # Converted to canonical SI unit
    INTERPOLATED = "INTERPOLATED"               # Computed via timestamp synchronizer grid alignment
    HELD = "HELD"                               # Held previous valid sample (causal hold)
    DERIVED = "DERIVED"                         # Module 01 mathematical formula (e.g. ISA Air Density)


class IntegrityStatus(Enum):
    """Payload transmission integrity classification."""
    ORIGINAL = "ORIGINAL"                       # First instance of event packet
    EXACT_DUPLICATE = "EXACT_DUPLICATE"         # Duplicate packet ID received again
    RETRANSMISSION = "RETRANSMISSION"           # Identical sequence number arriving late
    CONFLICTING_PAYLOAD = "CONFLICTING_PAYLOAD" # Duplicate sequence number with mismatched payload


class TimestampDomain(Enum):
    """Clock domain of raw source timestamp."""
    UTC = "UTC"                                 # UTC epoch seconds
    MONOTONIC = "MONOTONIC"                     # Monotonic clock seconds
    ECU_BOOT = "ECU_BOOT"                       # Seconds since ECU power-on
    MISSION_TIME = "MISSION_TIME"               # Seconds since mission start
    DEVICE_TICKS = "DEVICE_TICKS"               # Raw hardware clock ticks
    UNKNOWN = "UNKNOWN"                         # Unspecified domain


class FlightPhase(Enum):
    """Operational flight phase context."""
    GROUND = "GROUND"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    LOITER = "LOITER"
    DESCENT = "DESCENT"
    LANDING = "LANDING"
    EMERGENCY = "EMERGENCY"
    UNKNOWN = "UNKNOWN"


class ParameterClassification(Enum):
    """Parameter scope classification."""
    SIH_REQUIRED = "SIH_REQUIRED"               # Mandated by SIH26054 specification
    REPRESENTATIVE = "REPRESENTATIVE"           # Representative demonstration parameter
    DERIVED = "DERIVED"                         # Derived parameter
    OPTIONAL = "OPTIONAL"                       # Optional flight parameter
    UNKNOWN = "UNKNOWN"                         # Unspecified classification


class AlignmentMethod(Enum):
    """Timestamp grid alignment policy."""
    EXACT = "EXACT"                             # Sample timestamp matches T_grid exactly
    HOLD_LAST = "HOLD_LAST"                     # Held previous sample (t <= T_grid)
    LINEAR_INTERPOLATE = "LINEAR_INTERPOLATE"   # Interpolated between samples (OFFLINE_REPLAY_MODE only)
    NEAREST_SAMPLE = "NEAREST_SAMPLE"           # Nearest sample
    MISSING = "MISSING"                         # No valid sample available within window


class StorageRecoveryState(Enum):
    """Storage recovery state machine states."""
    NORMAL = "NORMAL"
    STORAGE_FAILURE = "STORAGE_FAILURE"
    EMERGENCY_BUFFERING = "EMERGENCY_BUFFERING"
    STORAGE_RECOVERED = "STORAGE_RECOVERED"
    DRAINING_FLUSH = "DRAINING_FLUSH"
