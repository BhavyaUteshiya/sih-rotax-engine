"""
Module 02 Deterministic Flight Phase State Machine (Phase 2 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

from src.module02.models.enums import FlightPhase
from src.module02.models.states import FlightState


class FlightPhaseMachine:
    """
    Deterministic Flight Phase Classifier based strictly on aircraft kinematic state and altitude progression.
    Phases: GROUND, START, TAXI, TAKEOFF, CLIMB, CRUISE, DESCENT, LANDING.
    """

    @classmethod
    def determine_flight_phase(
        cls,
        altitude_m: float,
        airspeed_m_s: float,
        vertical_speed_m_s: float,
        target_altitude_m: float = 10000.0,
        starter_active: bool = False
    ) -> FlightPhase:
        """
        Determines current flight phase deterministically without random timers.
        """
        alt = float(altitude_m)
        tas = float(airspeed_m_s)
        vz = float(vertical_speed_m_s)

        # 1. GROUND / START / TAXI
        if alt <= 0.5:
            if starter_active and tas <= 2.0:
                return FlightPhase.START
            elif tas <= 2.0:
                return FlightPhase.GROUND
            elif tas <= 15.0:
                return FlightPhase.TAXI
            else:
                return FlightPhase.TAKEOFF

        # 2. TAKEOFF / LANDING (Low Altitude Regime: 0.5m < alt <= 10m)
        if alt <= 10.0:
            if vz < -0.5:
                return FlightPhase.LANDING
            else:
                return FlightPhase.TAKEOFF

        # 3. AIRBORNE REGIME (alt > 10m)
        if vz >= 0.5:
            return FlightPhase.CLIMB
        elif vz <= -0.5:
            return FlightPhase.DESCENT
        else:
            # Steady altitude (|vz| < 0.5 m/s)
            if alt >= 100.0:
                return FlightPhase.CRUISE
            else:
                return FlightPhase.CLIMB
