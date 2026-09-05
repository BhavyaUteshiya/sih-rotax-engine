"""
Module 02 Deterministic Simulation Clock (Phase 1 Foundation).
SIH26054 — Module 02 Engine Simulator.
"""

from dataclasses import dataclass


class ClockError(ValueError):
    """Raised when invalid clock operations occur."""
    pass


class SimulationClock:
    """
    Deterministic simulation clock supporting fixed or configurable timestep integration.
    The simulation time advances strictly by dt per step and DOES NOT depend on wall-clock time.
    """

    def __init__(self, dt_seconds: float = 0.01, start_time_utc: float = 1787733200.0) -> None:
        if dt_seconds <= 0:
            raise ClockError(f"Timestep dt_seconds must be positive. Got {dt_seconds}.")

        self._dt_seconds: float = float(dt_seconds)
        self._start_time_utc: float = float(start_time_utc)
        self._current_time_utc: float = float(start_time_utc)
        self._simulation_time_sec: float = 0.0
        self._mission_elapsed_sec: float = 0.0
        self._step_count: int = 0

    @property
    def dt_seconds(self) -> float:
        return self._dt_seconds

    @property
    def current_time_utc(self) -> float:
        return self._current_time_utc

    @property
    def simulation_time_sec(self) -> float:
        return self._simulation_time_sec

    @property
    def mission_elapsed_sec(self) -> float:
        return self._mission_elapsed_sec

    @property
    def step_count(self) -> int:
        return self._step_count

    def step(self, custom_dt: float = None) -> float:
        """
        Advances physics clock by dt (or custom_dt).
        Returns new current_time_utc.
        """
        step_dt = float(custom_dt) if custom_dt is not None else self._dt_seconds
        if step_dt <= 0:
            raise ClockError(f"Step dt must be positive. Got {step_dt}.")

        self._step_count += 1
        self._simulation_time_sec += step_dt
        self._mission_elapsed_sec += step_dt
        self._current_time_utc += step_dt
        return self._current_time_utc

    def set_mission_elapsed_sec(self, elapsed_sec: float) -> None:
        """Explicitly updates mission elapsed time (e.g. state machine transition)."""
        if elapsed_sec < 0:
            raise ClockError(f"Mission elapsed sec cannot be negative. Got {elapsed_sec}.")
        self._mission_elapsed_sec = float(elapsed_sec)

    def reset(self, start_time_utc: float = None) -> None:
        """Resets clock to initial state."""
        if start_time_utc is not None:
            self._start_time_utc = float(start_time_utc)
        self._current_time_utc = self._start_time_utc
        self._simulation_time_sec = 0.0
        self._mission_elapsed_sec = 0.0
        self._step_count = 0
