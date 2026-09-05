import unittest
import sys
import os
import math
import copy

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.digital_twin.physics.propeller import PropellerModel, PropellerInput, PropellerState

class TestPropellerModel(unittest.TestCase):
    def setUp(self):
        # Base nominal operating point for Rotax 914 through gearbox
        # engine 5800 RPM / 2.4286 ≈ 2388 RPM propeller
        # Canonical diameter = 1.7 m from ROTAX_914_ENGINE_DATA.txt
        self.nominal_input = PropellerInput(
            propeller_rpm=2388.0,
            airspeed_m_s=40.0,
            ambient_density_kg_m3=1.225,
            propeller_diameter_m=1.7
        )

    def test_01_canonical_diameter_consistency(self):
        """1. canonical diameter consistency — must use 1.7 m"""
        self.assertAlmostEqual(self.nominal_input.propeller_diameter_m, 1.7)

    def test_02_rpm_to_rev_s_conversion(self):
        """2. RPM to rev/s conversion"""
        state = PropellerModel.calculate(self.nominal_input)
        n = self.nominal_input.propeller_rpm / 60.0
        expected_j = self.nominal_input.airspeed_m_s / (n * self.nominal_input.propeller_diameter_m)
        self.assertAlmostEqual(state.advance_ratio, expected_j)

    def test_03_rev_s_to_rad_s_consistency(self):
        """3. rev/s to rad/s consistency (P = omega * Q)"""
        state = PropellerModel.calculate(self.nominal_input)
        n = self.nominal_input.propeller_rpm / 60.0
        w = 2.0 * math.pi * n
        expected_p = w * state.aerodynamic_torque_nm
        self.assertAlmostEqual(state.absorbed_power_w, expected_p)

    def test_04_advance_ratio_numerical_correctness(self):
        """4. advance-ratio numerical correctness"""
        env = PropellerInput(
            propeller_rpm=2400.0,  # 40 rev/s
            airspeed_m_s=68.0,     # 68 m/s
            ambient_density_kg_m3=1.225,
            propeller_diameter_m=1.7
        )
        # J = 68 / (40 * 1.7) = 1.0
        state = PropellerModel.calculate(env)
        self.assertAlmostEqual(state.advance_ratio, 1.0)

    def test_05_zero_rpm_stability(self):
        """5. zero-RPM stability"""
        env = copy.deepcopy(self.nominal_input)
        env.propeller_rpm = 0.0
        state = PropellerModel.calculate(env)
        self.assertTrue(math.isfinite(state.advance_ratio))
        self.assertEqual(state.advance_ratio, 0.0)

    def test_06_near_zero_rpm_stability(self):
        """6. near-zero-RPM stability"""
        env = copy.deepcopy(self.nominal_input)
        env.propeller_rpm = 0.05
        state = PropellerModel.calculate(env)
        self.assertTrue(math.isfinite(state.advance_ratio))
        self.assertEqual(state.advance_ratio, 0.0)

    def test_07_zero_rpm_produces_zero_thrust(self):
        """7. zero-RPM produces zero aerodynamic thrust"""
        env = copy.deepcopy(self.nominal_input)
        env.propeller_rpm = 0.0
        state = PropellerModel.calculate(env)
        self.assertEqual(state.thrust_n, 0.0)

    def test_08_zero_rpm_produces_zero_torque(self):
        """8. zero-RPM produces zero aerodynamic torque"""
        env = copy.deepcopy(self.nominal_input)
        env.propeller_rpm = 0.0
        state = PropellerModel.calculate(env)
        self.assertEqual(state.aerodynamic_torque_nm, 0.0)

    def test_09_zero_rpm_produces_zero_power(self):
        """9. zero-RPM produces zero absorbed power"""
        env = copy.deepcopy(self.nominal_input)
        env.propeller_rpm = 0.0
        state = PropellerModel.calculate(env)
        self.assertEqual(state.absorbed_power_w, 0.0)

    def test_10_thrust_equation_numerical_accuracy(self):
        """10. thrust equation numerical accuracy"""
        state = PropellerModel.calculate(self.nominal_input)
        n = self.nominal_input.propeller_rpm / 60.0
        rho = self.nominal_input.ambient_density_kg_m3
        d = self.nominal_input.propeller_diameter_m
        expected_t = state.thrust_coefficient * rho * (n**2) * (d**4)
        self.assertAlmostEqual(state.thrust_n, expected_t)

    def test_11_torque_equation_numerical_accuracy(self):
        """11. torque equation numerical accuracy"""
        state = PropellerModel.calculate(self.nominal_input)
        n = self.nominal_input.propeller_rpm / 60.0
        rho = self.nominal_input.ambient_density_kg_m3
        d = self.nominal_input.propeller_diameter_m
        expected_q = state.torque_coefficient * rho * (n**2) * (d**5)
        self.assertAlmostEqual(state.aerodynamic_torque_nm, expected_q)

    def test_12_power_equation_numerical_accuracy(self):
        """12. power equation numerical accuracy"""
        state = PropellerModel.calculate(self.nominal_input)
        n = self.nominal_input.propeller_rpm / 60.0
        expected_p = 2.0 * math.pi * n * state.aerodynamic_torque_nm
        self.assertAlmostEqual(state.absorbed_power_w, expected_p)

    def test_13_efficiency_numerical_accuracy(self):
        """13. efficiency numerical accuracy"""
        state = PropellerModel.calculate(self.nominal_input)
        v = self.nominal_input.airspeed_m_s
        expected_eta = (state.thrust_n * v) / state.absorbed_power_w
        self.assertAlmostEqual(state.efficiency, expected_eta)

    def test_14_increased_density_increases_thrust(self):
        """14. increased density increases thrust"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.ambient_density_kg_m3 = 1.0
        state1 = PropellerModel.calculate(env1)
        
        env2 = copy.deepcopy(self.nominal_input)
        env2.ambient_density_kg_m3 = 1.2
        state2 = PropellerModel.calculate(env2)
        
        self.assertGreater(state2.thrust_n, state1.thrust_n)

    def test_15_increased_density_increases_torque(self):
        """15. increased density increases torque"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.ambient_density_kg_m3 = 1.0
        state1 = PropellerModel.calculate(env1)
        
        env2 = copy.deepcopy(self.nominal_input)
        env2.ambient_density_kg_m3 = 1.2
        state2 = PropellerModel.calculate(env2)
        
        self.assertGreater(state2.aerodynamic_torque_nm, state1.aerodynamic_torque_nm)

    def test_16_increased_speed_increases_thrust(self):
        """16. increased propeller speed increases thrust"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.propeller_rpm = 2000.0
        state1 = PropellerModel.calculate(env1)
        
        env2 = copy.deepcopy(self.nominal_input)
        env2.propeller_rpm = 2500.0
        state2 = PropellerModel.calculate(env2)
        
        self.assertGreater(state2.thrust_n, state1.thrust_n)

    def test_17_increased_speed_increases_torque(self):
        """17. increased propeller speed increases torque"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.propeller_rpm = 2000.0
        state1 = PropellerModel.calculate(env1)
        
        env2 = copy.deepcopy(self.nominal_input)
        env2.propeller_rpm = 2500.0
        state2 = PropellerModel.calculate(env2)
        
        self.assertGreater(state2.aerodynamic_torque_nm, state1.aerodynamic_torque_nm)

    def test_18_increased_diameter_scaling(self):
        """18. increased diameter produces expected scaling"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.propeller_diameter_m = 1.6
        state1 = PropellerModel.calculate(env1)
        
        env2 = copy.deepcopy(self.nominal_input)
        env2.propeller_diameter_m = 1.8
        state2 = PropellerModel.calculate(env2)
        
        self.assertGreater(state2.thrust_n, state1.thrust_n)
        self.assertGreater(state2.aerodynamic_torque_nm, state1.aerodynamic_torque_nm)

    def test_19_airspeed_increases_advance_ratio(self):
        """19. airspeed increases advance ratio"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.airspeed_m_s = 20.0
        state1 = PropellerModel.calculate(env1)
        
        env2 = copy.deepcopy(self.nominal_input)
        env2.airspeed_m_s = 40.0
        state2 = PropellerModel.calculate(env2)
        
        self.assertGreater(state2.advance_ratio, state1.advance_ratio)

    def test_20_coefficients_remain_bounded(self):
        """20. coefficient surrogate remains bounded"""
        env = copy.deepcopy(self.nominal_input)
        env.airspeed_m_s = 150.0  # Unreasonably high J
        state = PropellerModel.calculate(env)
        self.assertGreaterEqual(state.thrust_coefficient, PropellerModel.CT_MIN)
        self.assertGreaterEqual(state.torque_coefficient, PropellerModel.CQ_MIN)

    def test_21_thrust_remains_finite(self):
        """21. thrust remains finite"""
        env = copy.deepcopy(self.nominal_input)
        env.propeller_rpm = 10000.0
        state = PropellerModel.calculate(env)
        self.assertTrue(math.isfinite(state.thrust_n))

    def test_22_torque_remains_finite(self):
        """22. torque remains finite"""
        state = PropellerModel.calculate(self.nominal_input)
        self.assertTrue(math.isfinite(state.aerodynamic_torque_nm))

    def test_23_power_remains_finite(self):
        """23. power remains finite"""
        state = PropellerModel.calculate(self.nominal_input)
        self.assertTrue(math.isfinite(state.absorbed_power_w))

    def test_24_efficiency_remains_finite(self):
        """24. efficiency remains finite"""
        state = PropellerModel.calculate(self.nominal_input)
        self.assertTrue(math.isfinite(state.efficiency))

    def test_25_efficiency_remains_within_physical_bounds(self):
        """25. efficiency remains within documented physical bounds"""
        env = copy.deepcopy(self.nominal_input)
        env.airspeed_m_s = 100.0
        state = PropellerModel.calculate(env)
        self.assertGreaterEqual(state.efficiency, 0.0)
        self.assertLessEqual(state.efficiency, 1.0)

    def test_26_propeller_torque_sign_convention(self):
        """26. propeller torque opposes engine rotation by convention"""
        state = PropellerModel.calculate(self.nominal_input)
        self.assertGreater(state.aerodynamic_torque_nm, 0.0)

    def test_27_gearbox_speed_interpreted_correctly(self):
        """27. gearbox speed input is interpreted correctly"""
        env = copy.deepcopy(self.nominal_input)
        env.propeller_rpm = 5800.0  # wrong: this is engine RPM, not prop RPM
        state = PropellerModel.calculate(env)
        # Power scales roughly with n^3 so feeding wrong speed gives massively excessive power
        self.assertGreater(state.absorbed_power_w, 100000.0)

    def test_28_nominal_power_within_engine_shaft_envelope(self):
        """28. nominal operating-point power compatible with engine shaft-power envelope"""
        state = PropellerModel.calculate(self.nominal_input)
        # 1E shaft power at rated: ~71 kW (from 85.8 kW indicated minus friction)
        # Propeller absorbed power must NOT exceed this
        self.assertLess(state.absorbed_power_w, 71500.0)
        # It should still be a significant fraction of rated power (not trivially small)
        self.assertGreater(state.absorbed_power_w, 30000.0)

    def test_29_high_altitude_sanity_check(self):
        """29. high-altitude sanity check"""
        env = copy.deepcopy(self.nominal_input)
        env.ambient_density_kg_m3 = 0.5  # ~ 20,000 ft
        state = PropellerModel.calculate(env)
        self.assertTrue(math.isfinite(state.thrust_n))
        self.assertLess(state.thrust_n, PropellerModel.calculate(self.nominal_input).thrust_n)

    def test_30_static_condition_sanity_check(self):
        """30. static condition sanity check"""
        env = copy.deepcopy(self.nominal_input)
        env.airspeed_m_s = 0.0
        state = PropellerModel.calculate(env)
        self.assertEqual(state.advance_ratio, 0.0)
        self.assertEqual(state.efficiency, 0.0)
        self.assertGreater(state.thrust_n, 0.0)
        self.assertGreater(state.aerodynamic_torque_nm, 0.0)

    def test_31_regression_integration_with_upstream(self):
        """31. regression: 1F can consume upstream outputs cleanly"""
        from src.digital_twin.physics.atmosphere import AtmosphericState
        atm = AtmosphericState(1000.0, 15.0, 288.15, 90000.0, 1.1, 0.0, 340.0)
        engine_rpm = 5800.0
        prop_rpm = engine_rpm * 0.41176

        env = PropellerInput(
            propeller_rpm=prop_rpm,
            airspeed_m_s=30.0,
            ambient_density_kg_m3=atm.density_kg_m3,
            propeller_diameter_m=1.7
        )
        state = PropellerModel.calculate(env)
        self.assertTrue(math.isfinite(state.aerodynamic_torque_nm))
        self.assertGreater(state.aerodynamic_torque_nm, 0.0)

if __name__ == '__main__':
    unittest.main()
