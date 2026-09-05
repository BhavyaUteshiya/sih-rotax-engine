"""Validation-level contract checks for the active Phase 1 foundation."""

from src.digital_twin.physics.engine_dynamics import EngineDynamicsModel
from src.digital_twin.simulation.simulator import DigitalTwinSimulator
from src.digital_twin.simulation.state import SimulationInput


def test_gearbox_convention_and_reflected_inertia_are_consistent():
    ratio = EngineDynamicsModel.GEARBOX_RATIO
    expected = EngineDynamicsModel.J_ENGINE + EngineDynamicsModel.J_PROP * ratio**2
    assert EngineDynamicsModel.J_EQ == expected


def test_prototype_map_target_is_an_explicit_simulation_boundary():
    simulator = DigitalTwinSimulator()
    state = simulator.step(
        SimulationInput(target_map_at_full_throttle_pa=108000.0, throttle_position=1.0)
    )
    assert state.turbo.manifold_pressure_pa > 0.0
