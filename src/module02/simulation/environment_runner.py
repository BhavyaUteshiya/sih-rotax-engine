"""
Module 02 Environment & Atmosphere Simulation Integration Runner (Phase 2 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Tuple
from src.module02.core.clock import SimulationClock
from src.module02.models.states import (
    EnvironmentState,
    FlightState,
    SimulationState,
)
from src.module02.physics.atmosphere import AtmosphereModel
from src.module02.physics.flight_environment import FlightEnvironmentModel
from src.module02.simulation.flight_phase_machine import FlightPhaseMachine


class EnvironmentRunner:
    """
    Deterministic Integration Runner for Phase 2 Atmosphere, Wind, Airspeed, Dynamic Pressure,
    and Flight Phase physics progression.
    """

    def __init__(self, clock: SimulationClock = None) -> None:
        self.clock = clock if clock is not None else SimulationClock()
        self.state = SimulationState()

    def initialize_environment(
        self,
        initial_altitude_m: float = 0.0,
        temp_offset_k: float = 0.0,
        relative_humidity_percent: float = 0.0,
        wind_ned_m_s: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        v_ground_ned_m_s: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ) -> SimulationState:
        """Initializes state container for Phase 2 physics simulation."""
        self.state.environment = AtmosphereModel.compute_environment_snapshot(
            altitude_m=initial_altitude_m,
            temp_offset_k=temp_offset_k,
            relative_humidity_percent=relative_humidity_percent,
            wind_speed_m_s=FlightEnvironmentModel.compute_ground_speed_scalar(wind_ned_m_s)
        )

        v_rel = FlightEnvironmentModel.compute_relative_air_velocity_ned(v_ground_ned_m_s, wind_ned_m_s)
        tas = FlightEnvironmentModel.compute_true_airspeed_tas(v_rel)

        self.state.flight.altitude_m = initial_altitude_m
        self.state.flight.airspeed_m_s = tas
        self.state.flight.vertical_speed_m_s = - float(v_ground_ned_m_s[2]) # V_z = - V_g_down
        self.state.flight.flight_phase = FlightPhaseMachine.determine_flight_phase(
            altitude_m=initial_altitude_m,
            airspeed_m_s=tas,
            vertical_speed_m_s=self.state.flight.vertical_speed_m_s
        )

        return self.state

    def step(
        self,
        v_ground_ned_m_s: Tuple[float, float, float],
        wind_ned_m_s: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        temp_offset_k: float = 0.0,
        relative_humidity_percent: float = 0.0
    ) -> SimulationState:
        """
        Executes one deterministic physics integration step of duration dt_seconds.
        Calculates Atmosphere -> Wind -> TAS -> Dynamic Pressure -> Altitude -> Phase.
        """
        dt = self.clock.dt_seconds

        # 1. Advance altitude based on vertical velocity V_z = - V_g_down
        vz = - float(v_ground_ned_m_s[2])
        new_alt = FlightEnvironmentModel.update_altitude_progression(
            current_altitude_m=self.state.flight.altitude_m,
            vertical_speed_m_s=vz,
            dt_seconds=dt
        )

        # 2. Advance Simulation Clock
        self.clock.step()

        # 3. Calculate Atmosphere at new altitude
        env_snapshot = AtmosphereModel.compute_environment_snapshot(
            altitude_m=new_alt,
            temp_offset_k=temp_offset_k,
            relative_humidity_percent=relative_humidity_percent,
            wind_speed_m_s=FlightEnvironmentModel.compute_ground_speed_scalar(wind_ned_m_s)
        )
        self.state.environment = env_snapshot

        # 4. Calculate Relative Air Velocity Vector & True Airspeed (TAS)
        v_rel = FlightEnvironmentModel.compute_relative_air_velocity_ned(v_ground_ned_m_s, wind_ned_m_s)
        tas = FlightEnvironmentModel.compute_true_airspeed_tas(v_rel)

        # 5. Calculate Dynamic Pressure q = 0.5 * rho * V^2
        q = AtmosphereModel.compute_dynamic_pressure(env_snapshot.air_density_kg_m3, tas)

        # 6. Update Flight State
        self.state.flight.altitude_m = new_alt
        self.state.flight.airspeed_m_s = tas
        self.state.flight.vertical_speed_m_s = vz

        # 7. Determine Flight Phase
        self.state.flight.flight_phase = FlightPhaseMachine.determine_flight_phase(
            altitude_m=new_alt,
            airspeed_m_s=tas,
            vertical_speed_m_s=vz,
            target_altitude_m=self.state.flight.target_altitude_m
        )

        return self.state
