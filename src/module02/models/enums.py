"""
Module 02 Core Enumerations & Stable Identifiers (Phase 1 Foundation & Provenance System).
SIH26054 — Module 02 Engine Simulator.
"""

from enum import Enum


class ProvenanceClassification(str, Enum):
    """Configuration parameter provenance classification hierarchy."""
    OFFICIAL = "OFFICIAL"               # Directly supported by DRDO / official releases
    REPORTED = "REPORTED"               # Reported in credible technical defense literature
    DERIVED = "DERIVED"                 # Mathematically derived from official/reported figures
    ASSUMED = "ASSUMED"                 # Grounded physical assumption
    ESTIMATED = "ESTIMATED"             # Engineering estimate requiring calibration
    CALIBRATED = "CALIBRATED"           # Calibrated against test-rig/flight telemetry data


class ParameterStatus(str, Enum):
    """Parameter implementation readiness in registry."""
    IMPLEMENTED = "IMPLEMENTED"         # Fully implemented in physics simulation engine
    CONFIGURED = "CONFIGURED"           # Defined in YAML configuration layer
    DERIVED = "DERIVED"                 # Calculated dynamically in physical state equations
    PLANNED = "PLANNED"                 # Planned for downstream simulation modules


class FlightPhase(str, Enum):
    """Mission Flight State Machine Phases."""
    GROUND = "GROUND"
    START = "START"
    TAXI = "TAXI"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    ENDURANCE = "ENDURANCE"     # Sustained on-station loiter at target altitude
    DESCENT = "DESCENT"
    LANDING = "LANDING"


class EngineOperatingState(str, Enum):
    """Engine Operating State Machine Modes."""
    OFF = "OFF"
    STARTING = "STARTING"
    IDLE = "IDLE"
    RUNNING = "RUNNING"


class FaultScenario(str, Enum):
    """Supported SIH Simulation & Fault Scenarios."""
    NONE = "NONE"
    MISFIRE = "MISFIRE"
    INJECTOR_ABNORMALITY = "INJECTOR_ABNORMALITY"
    LUBRICATION_ISSUE = "LUBRICATION_ISSUE"
    SENSOR_DRIFT = "SENSOR_DRIFT"
    SENSOR_FAILURE = "SENSOR_FAILURE"
    COMBUSTION_INSTABILITY = "COMBUSTION_INSTABILITY"
    OVERHEATING_TREND = "OVERHEATING_TREND"
    ABNORMAL_VIBRATION = "ABNORMAL_VIBRATION"
    CODING_DEGRADATION = "CODING_DEGRADATION"  # Data corruption/loss in transit


class PhysicalOrigin(str, Enum):
    """Source provenance identifier (Module 01 integration boundary)."""
    SIMULATOR = "SIMULATOR"


class StateCategory(str, Enum):
    """State classification identifier (Module 01 integration boundary)."""
    SIMULATED = "SIMULATED"


class ProcessingContext(str, Enum):
    """Processing context identifier (Module 01 integration boundary)."""
    SYNTHETIC_GENERATION = "SYNTHETIC_GENERATION"


class ParameterCategory(str, Enum):
    """Parameter classification categories."""
    ENVIRONMENT = "ENVIRONMENT"
    FLIGHT = "FLIGHT"
    ENGINE_CONTROL = "ENGINE_CONTROL"
    ENGINE_DYNAMICS = "ENGINE_DYNAMICS"
    COMBUSTION = "COMBUSTION"
    THERMAL = "THERMAL"
    LUBRICATION = "LUBRICATION"
    MECHANICAL = "MECHANICAL"
    ELECTRICAL = "ELECTRICAL"
    DEGRADATION = "DEGRADATION"
    SENSOR = "SENSOR"
    TURBOCHARGER = "TURBOCHARGER"
    GEARBOX = "GEARBOX"
    METADATA = "METADATA"
