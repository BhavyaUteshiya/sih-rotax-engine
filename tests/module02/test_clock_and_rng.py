"""
Phase 1 Deterministic Clock & RNG Validation Tests.
SIH26054 — Module 02 Engine Simulator.
"""

import pytest
from src.module02.core.clock import ClockError, SimulationClock
from src.module02.core.rng import DeterministicRNG


def test_simulation_clock_time_stepping():
    """Verify deterministic timestep progression independent of wall-clock time."""
    clock = SimulationClock(dt_seconds=0.01, start_time_utc=1000.0)

    assert clock.dt_seconds == 0.01
    assert clock.current_time_utc == 1000.0
    assert clock.simulation_time_sec == 0.0
    assert clock.step_count == 0

    # Step 1
    t1 = clock.step()
    assert t1 == pytest.approx(1000.01)
    assert clock.simulation_time_sec == pytest.approx(0.01)
    assert clock.step_count == 1

    # Step 100 times -> exactly 1.0 second simulation time
    for _ in range(99):
        clock.step()

    assert clock.simulation_time_sec == pytest.approx(1.0)
    assert clock.current_time_utc == pytest.approx(1001.0)
    assert clock.step_count == 100


def test_simulation_clock_negative_dt_rejection():
    """Verify rejection of zero or negative timesteps."""
    with pytest.raises(ClockError):
        SimulationClock(dt_seconds=-0.01)

    with pytest.raises(ClockError):
        SimulationClock(dt_seconds=0.0)

    clock = SimulationClock(dt_seconds=0.01)
    with pytest.raises(ClockError):
        clock.step(custom_dt=-0.05)


def test_deterministic_rng_reproducibility():
    """Verify that same master seed produces 100% reproducible sequence of random samples."""
    rng1 = DeterministicRNG(master_seed=42)
    rng2 = DeterministicRNG(master_seed=42)

    samples1 = [rng1.gauss(0.0, 1.0) for _ in range(10)]
    samples2 = [rng2.gauss(0.0, 1.0) for _ in range(10)]

    assert samples1 == samples2

    # Verify uniform and choice determinism
    u1 = [rng1.uniform(10.0, 20.0) for _ in range(5)]
    u2 = [rng2.uniform(10.0, 20.0) for _ in range(5)]
    assert u1 == u2


def test_deterministic_rng_different_seeds():
    """Verify that different master seeds produce distinct sample sequences."""
    rng1 = DeterministicRNG(master_seed=42)
    rng2 = DeterministicRNG(master_seed=999)

    samples1 = [rng1.gauss(0.0, 1.0) for _ in range(10)]
    samples2 = [rng2.gauss(0.0, 1.0) for _ in range(10)]

    assert samples1 != samples2
