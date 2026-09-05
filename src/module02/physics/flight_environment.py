"""
Module 02 Flight Environment & Wind Vector Aerodynamics Subsystem (Phase 2 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Tuple
from src.module02.models.states import FlightState


class FlightEnvironmentError(ValueError):
    """Raised when invalid flight environment parameters occur."""
    pass


class FlightEnvironmentModel:
    """
    Flight Environment & Aerodynamic Vector Subsystem using North-East-Down (NED) coordinate convention.
    Computes vector relationships between Ground Speed, Wind Vector, True Airspeed (TAS),
    Indicated Airspeed (IAS), Dynamic Pressure (q), and Vertical Altitude Progression (V_z).
    """

    @classmethod
    def compute_relative_air_velocity_ned(
        cls,
        v_ground_ned: Tuple[float, float, float],
        v_wind_ned: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Computes air-relative velocity vector V_rel = V_ground - V_wind in NED coordinates.
        V_ground = (V_g_north, V_g_east, V_g_down)
        V_wind   = (V_w_north, V_w_east, V_w_down)
        """
        v_r_north = float(v_ground_ned[0]) - float(v_wind_ned[0])
        v_r_east  = float(v_ground_ned[1]) - float(v_wind_ned[1])
        v_r_down  = float(v_ground_ned[2]) - float(v_wind_ned[2])
        return (v_r_north, v_r_east, v_r_down)

    @classmethod
    def compute_true_airspeed_tas(cls, v_rel_ned: Tuple[float, float, float]) -> float:
        """Computes scalar True Airspeed (TAS) V_TAS = ||V_rel|| in m/s."""
        vn, ve, vd = v_rel_ned
        return math.sqrt(vn * vn + ve * ve + vd * vd)

    @classmethod
    def compute_ground_speed_scalar(cls, v_ground_ned: Tuple[float, float, float]) -> float:
        """Computes horizontal ground speed scalar V_ground in m/s."""
        vn, ve, _ = v_ground_ned
        return math.sqrt(vn * vn + ve * ve)

    @classmethod
    def compute_indicated_airspeed_ias(cls, dynamic_pressure_pa: float, sea_level_density_kg_m3: float = 1.225) -> float:
        """
        Derives Indicated Airspeed (IAS) from dynamic pressure q:
        q = 0.5 * rho_sea * V_IAS^2 => V_IAS = sqrt(2 * q / rho_sea)
        """
        if dynamic_pressure_pa < 0:
            raise FlightEnvironmentError(f"Negative dynamic pressure: {dynamic_pressure_pa} Pa.")
        return math.sqrt((2.0 * dynamic_pressure_pa) / sea_level_density_kg_m3)

    @classmethod
    def update_altitude_progression(cls, current_altitude_m: float, vertical_speed_m_s: float, dt_seconds: float) -> float:
        """
        Advances altitude dh/dt = V_z:
        altitude(t + dt) = altitude(t) + (V_z * dt)
        Clamped to valid Troposphere limits [0.0, 20000.0 m].
        """
        if dt_seconds <= 0:
            raise FlightEnvironmentError(f"Invalid timestep dt: {dt_seconds} s. Must be > 0.")

        dh = float(vertical_speed_m_s) * float(dt_seconds)
        new_alt = float(current_altitude_m) + dh
        return max(0.0, min(20000.0, new_alt))

    @classmethod
    def compute_current_aircraft_mass(cls, flight_state: FlightState) -> float:
        """
        Computes configuration-driven aircraft current mass:
        m_current = m_dry + m_payload + m_fuel_remaining
        """
        m_curr = flight_state.current_mass_kg
        if m_curr < 0:
            raise FlightEnvironmentError(f"Computed current aircraft mass is negative: {m_curr} kg.")
        return m_curr
