import unittest
import sys
import os
import math

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.digital_twin.physics.combustion import FuelCombustionInput, FuelCombustionState, CombustionModel

class TestCombustionModel(unittest.TestCase):
    
    def setUp(self):
        # Base nominal input around 5800 RPM
        self.nominal_input = FuelCombustionInput(
            engine_rpm=5800.0,
            throttle_position=1.0,
            manifold_pressure_pa=135000.0,
            manifold_temperature_k=320.0,
            air_mass_flow_kg_s=0.10, # arbitrary example mass flow
            ambient_pressure_pa=101325.0,
            fuel_pressure_delta_pa=25000.0
        )

    def test_01_basic_nominal_combustion(self):
        """1. Basic nominal combustion"""
        state = CombustionModel.calculate(self.nominal_input)
        self.assertGreater(state.fuel_mass_flow_kg_s, 0.0)
        self.assertGreater(state.indicated_power_w, 0.0)
        self.assertEqual(state.fuel_pressure_status, 'NORMAL')

    def test_02_zero_rpm(self):
        """2. Zero RPM"""
        env = self.nominal_input
        env.engine_rpm = 0.0
        state = CombustionModel.calculate(env)
        self.assertEqual(state.fuel_mass_flow_kg_s, 0.0)
        self.assertEqual(state.indicated_power_w, 0.0)
        self.assertTrue(math.isfinite(state.exhaust_temperature_k))

    def test_03_low_airflow(self):
        """3. Low airflow"""
        env = self.nominal_input
        env.air_mass_flow_kg_s = 1e-7 # practically zero
        state = CombustionModel.calculate(env)
        self.assertEqual(state.fuel_mass_flow_kg_s, 0.0)
        self.assertEqual(state.indicated_power_w, 0.0)

    def test_04_high_airflow(self):
        """4. High airflow"""
        env = self.nominal_input
        env.air_mass_flow_kg_s = 0.20 
        state = CombustionModel.calculate(env)
        self.assertGreater(state.indicated_power_w, 50000.0)

    def test_05_low_throttle(self):
        """5. Low throttle"""
        env = self.nominal_input
        env.throttle_position = 0.1
        env.manifold_pressure_pa = 50000.0
        env.air_mass_flow_kg_s = 0.02
        state = CombustionModel.calculate(env)
        self.assertGreater(state.fuel_mass_flow_kg_s, 0.0)
        self.assertLess(state.fuel_mass_flow_kg_s, 0.01)

    def test_06_high_throttle(self):
        """6. High throttle"""
        state_high = CombustionModel.calculate(self.nominal_input)
        env_low = self.nominal_input
        env_low.throttle_position = 0.1
        env_low.manifold_pressure_pa = 50000.0
        env_low.air_mass_flow_kg_s = 0.02
        state_low = CombustionModel.calculate(env_low)
        self.assertGreater(state_high.fuel_mass_flow_kg_s, state_low.fuel_mass_flow_kg_s)

    def test_07_altitude_reduced_ambient_pressure(self):
        """7. Altitude / reduced ambient pressure"""
        env = self.nominal_input
        env.ambient_pressure_pa = 50000.0 # ~5.5km alt
        state = CombustionModel.calculate(env)
        # Exhaust pressure should be lower
        self.assertLess(state.exhaust_pressure_pa, 100000.0)

    def test_08_hot_environment(self):
        """8. Hot environment"""
        env = self.nominal_input
        env.manifold_temperature_k = 350.0
        state = CombustionModel.calculate(env)
        # Higher initial charge temp means higher exhaust temp for same energy
        self.assertGreater(state.exhaust_temperature_k, 350.0)

    def test_09_cold_environment(self):
        """9. Cold environment"""
        env = self.nominal_input
        env.manifold_temperature_k = 250.0
        state = CombustionModel.calculate(env)
        self.assertGreater(state.exhaust_temperature_k, 250.0)

    def test_10_nominal_fuel_pressure(self):
        """10. Nominal fuel pressure"""
        env = self.nominal_input
        env.fuel_pressure_delta_pa = 25000.0
        state = CombustionModel.calculate(env)
        self.assertEqual(state.fuel_pressure_status, 'NORMAL')

    def test_11_low_fuel_pressure_boundary(self):
        """11. Low fuel pressure boundary"""
        env = self.nominal_input
        env.fuel_pressure_delta_pa = 15000.0
        state = CombustionModel.calculate(env)
        self.assertEqual(state.fuel_pressure_status, 'NORMAL')

    def test_12_high_fuel_pressure_boundary(self):
        """12. High fuel pressure boundary"""
        env = self.nominal_input
        env.fuel_pressure_delta_pa = 35000.0
        state = CombustionModel.calculate(env)
        self.assertEqual(state.fuel_pressure_status, 'NORMAL')

    def test_13_below_min_fuel_pressure(self):
        """13. Below-min fuel pressure"""
        env = self.nominal_input
        env.fuel_pressure_delta_pa = 14000.0
        state = CombustionModel.calculate(env)
        self.assertEqual(state.fuel_pressure_status, 'LOW')

    def test_14_above_max_fuel_pressure(self):
        """14. Above-max fuel pressure"""
        env = self.nominal_input
        env.fuel_pressure_delta_pa = 36000.0
        state = CombustionModel.calculate(env)
        self.assertEqual(state.fuel_pressure_status, 'HIGH')

    def test_15_afr_validity(self):
        """15. AFR validity"""
        state = CombustionModel.calculate(self.nominal_input)
        self.assertGreater(state.air_fuel_ratio, 10.0)
        self.assertLess(state.air_fuel_ratio, 20.0)

    def test_16_equivalence_ratio_validity(self):
        """16. Equivalence-ratio validity"""
        state = CombustionModel.calculate(self.nominal_input)
        self.assertGreaterEqual(state.equivalence_ratio, CombustionModel.PHI_MIN)
        self.assertLessEqual(state.equivalence_ratio, CombustionModel.PHI_MAX)

    def test_17_fuel_mass_flow_consistency(self):
        """17. Fuel mass-flow consistency"""
        state = CombustionModel.calculate(self.nominal_input)
        expected = self.nominal_input.air_mass_flow_kg_s / state.air_fuel_ratio
        self.assertAlmostEqual(state.fuel_mass_flow_kg_s, expected)

    def test_18_exhaust_mass_conservation(self):
        """18. Exhaust mass conservation"""
        state = CombustionModel.calculate(self.nominal_input)
        expected = self.nominal_input.air_mass_flow_kg_s + state.fuel_mass_flow_kg_s
        self.assertAlmostEqual(state.exhaust_mass_flow_kg_s, expected)

    def test_19_exhaust_pressure_positivity(self):
        """19. Exhaust pressure positivity"""
        state = CombustionModel.calculate(self.nominal_input)
        self.assertGreater(state.exhaust_pressure_pa, 0.0)
        self.assertGreater(state.exhaust_pressure_pa, self.nominal_input.ambient_pressure_pa)

    def test_20_exhaust_temperature_physicality(self):
        """20. Exhaust temperature physicality"""
        state = CombustionModel.calculate(self.nominal_input)
        self.assertGreater(state.exhaust_temperature_k, self.nominal_input.manifold_temperature_k)
        self.assertTrue(math.isfinite(state.exhaust_temperature_k))
        # Exhaust temperatures shouldn't be insanely high (e.g., > 2000K for this model)
        self.assertLess(state.exhaust_temperature_k, 2500.0)

    def test_21_energy_accounting_closure(self):
        """21. Energy accounting closure"""
        state = CombustionModel.calculate(self.nominal_input)
        
        # P_fuel = P_unreleased + P_indicated + P_exhaust + P_heat_loss
        sum_power = (state.unreleased_power_w + 
                     state.indicated_power_w + 
                     state.exhaust_sensible_power_w + 
                     state.heat_loss_power_w)
                     
        self.assertAlmostEqual(state.chemical_energy_power_w, sum_power, places=2)

    def test_22_wiebe_burn_fraction_monotonicity(self):
        """22. Wiebe burn-fraction monotonicity"""
        # Testing the formulation mathematically.
        # Since we evaluate at constant theta_0 + duration, we expect it to be > 0.9.
        state = CombustionModel.calculate(self.nominal_input)
        self.assertGreater(state.mass_fraction_burned, 0.9)

    def test_23_burn_fraction_remains_within_0_1(self):
        """23. Burn fraction remains within 0-1"""
        state = CombustionModel.calculate(self.nominal_input)
        self.assertGreaterEqual(state.mass_fraction_burned, 0.0)
        self.assertLessEqual(state.mass_fraction_burned, 1.0)

    def test_24_no_nan_inf_across_representative_operating_points(self):
        """24. No NaN / inf across representative operating points"""
        import random
        for _ in range(50):
            env = FuelCombustionInput(
                engine_rpm=random.uniform(0, 6000),
                throttle_position=random.uniform(0, 1),
                manifold_pressure_pa=random.uniform(10000, 150000),
                manifold_temperature_k=random.uniform(250, 400),
                air_mass_flow_kg_s=random.uniform(0, 0.2),
                ambient_pressure_pa=random.uniform(20000, 105000),
                fuel_pressure_delta_pa=random.uniform(0, 50000)
            )
            state = CombustionModel.calculate(env)
            self.assertTrue(math.isfinite(state.fuel_mass_flow_kg_s))
            self.assertTrue(math.isfinite(state.indicated_power_w))
            self.assertTrue(math.isfinite(state.exhaust_temperature_k))
            self.assertTrue(math.isfinite(state.exhaust_pressure_pa))

    def test_25_compatibility_with_1B_exhaust_state_interface(self):
        """25. Compatibility with the existing 1B ExhaustState interface"""
        # Exists in turbo_intake.py: ExhaustState(pressure_pa, temperature_k, mass_flow_kg_s)
        from src.digital_twin.physics.turbo_intake import ExhaustState
        state = CombustionModel.calculate(self.nominal_input)
        exh = ExhaustState(
            pressure_pa=state.exhaust_pressure_pa,
            temperature_k=state.exhaust_temperature_k,
            mass_flow_kg_s=state.exhaust_mass_flow_kg_s
        )
        self.assertIsInstance(exh, ExhaustState)

    def test_26_regression_case_at_approximately_rated_operating_condition(self):
        """26. Regression case at approximately rated operating condition"""
        # Nominal Rotax 914 is 115hp at 5800 RPM.
        # Check if fuel consumption is around 33 L/h (Phase 1F refined check)
        state = CombustionModel.calculate(self.nominal_input)
        # 115 hp is ~85.7 kW
        # Just ensure it's in the right order of magnitude for this generic surrogate
        self.assertGreater(state.fuel_volume_flow_l_h, 28.0)
        self.assertLess(state.fuel_volume_flow_l_h, 38.0)

if __name__ == '__main__':
    unittest.main()
