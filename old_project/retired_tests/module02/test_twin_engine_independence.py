"""
Twin-Engine Independent Instantiation Validation Tests.
SIH26054 — Module 02 Engine Simulator.
"""

import pytest
from src.module02.models.states import EngineState, SimulationState


def test_twin_engine_independent_instantiation():
    """Verify that Engine 1 and Engine 2 states can be modified independently without cross-contamination."""
    eng1 = EngineState(engine_index=1, engine_id="engine_left")
    eng2 = EngineState(engine_index=2, engine_id="engine_right")

    eng1.throttle_percent = 85.0
    eng1.engine_rpm = 4200.0

    eng2.throttle_percent = 40.0
    eng2.engine_rpm = 2800.0

    # Verify independence
    assert eng1.throttle_percent == 85.0
    assert eng1.engine_rpm == 4200.0

    assert eng2.throttle_percent == 40.0
    assert eng2.engine_rpm == 2800.0

    # Verify simulation state container holds independent engines
    sim_state = SimulationState()
    sim_state.engines[1] = eng1
    sim_state.engines[2] = eng2

    assert len(sim_state.engines) == 2
    assert sim_state.engines[1].engine_rpm == 4200.0
    assert sim_state.engines[2].engine_rpm == 2800.0
