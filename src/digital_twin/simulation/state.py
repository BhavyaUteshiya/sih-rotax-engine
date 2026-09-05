"""
Digital Twin Shared State Module
SIH26054 — Digital Twin Core

Defines the SimulationState which aggregates the states of all physical sub-models.
"""
from dataclasses import dataclass
from ..physics.atmosphere import AtmosphericState
from ..physics.turbo_intake import TurboState
from ..physics.airflow import AirflowState
from ..physics.combustion import FuelCombustionState
from ..physics.engine_dynamics import EngineDynamicsState
from ..physics.propeller import PropellerState
from ..physics.thermal import ThermalState

@dataclass
class SimulationState:
    """Unified state of the entire Phase 1 Digital Twin at a given timestep."""
    time_s: float
    atmosphere: AtmosphericState
    turbo: TurboState
    airflow: AirflowState
    combustion: FuelCombustionState
    propeller: PropellerState
    engine_dynamics: EngineDynamicsState
    thermal: ThermalState

@dataclass
class SimulationInput:
    """External inputs driving the simulation."""
    timestep_s: float = 0.01
    altitude_m: float = 0.0
    ambient_temp_c: float = None
    temperature_offset_k: float = 0.0
    relative_humidity_pct: float = 0.0
    throttle_position: float = 0.0
    airspeed_m_s: float = 0.0
    fuel_pressure_pa: float = 250000.0  # Nominally 2.5 bar absolute
    # Explicit override for Fuel Pressure Delta (Fuel Line Pressure - Manifold Pressure).
    # Ensures accurate fuel injection rate independent of varying boost pressure.
    fuel_pressure_delta_pa: float = 25000.0 # 0.25 bar delta
    starter_engaged: bool = False
