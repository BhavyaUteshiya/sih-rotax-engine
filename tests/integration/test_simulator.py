import unittest
import math

from src.digital_twin.simulation.simulator import DigitalTwinSimulator
from src.digital_twin.simulation.state import SimulationInput

class TestDigitalTwinSimulator(unittest.TestCase):
    def test_simulator_basic_step(self):
        # Initialize the simulator
        simulator = DigitalTwinSimulator()
        
        # We need a small timestep
        sim_input = SimulationInput(timestep_s=0.1)
        
        # Take a step
        new_state = simulator.step(sim_input)
        
        # Verify basic physics advanced
        self.assertIsNotNone(new_state.atmosphere)
        self.assertIsNotNone(new_state.turbo)
        self.assertIsNotNone(new_state.airflow)
        self.assertIsNotNone(new_state.combustion)
        self.assertIsNotNone(new_state.propeller)
        self.assertIsNotNone(new_state.engine_dynamics)
        self.assertIsNotNone(new_state.thermal)

        # Check values are physically sound
        self.assertTrue(math.isfinite(new_state.atmosphere.pressure_pa))
        self.assertTrue(math.isfinite(new_state.engine_dynamics.engine_rpm))

if __name__ == '__main__':
    unittest.main()
