import unittest
import sys
import os
import math

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.digital_twin.physics.engine_dynamics import EngineDynamicsInput, EngineDynamicsState, EngineDynamicsModel

class TestEngineDynamicsModel(unittest.TestCase):
    
    def setUp(self):
        # Base nominal operating point roughly around 5800 RPM (607.37 rad/s)
        self.nominal_input = EngineDynamicsInput(
            engine_angular_speed_rad_s=607.37,
            indicated_power_w=85800.0,  # ~115 hp for rated testing
            starter_engaged=False,
            timestep_s=0.01,
            propeller_load_torque_nm=0.0
        )

    def test_01_rpm_angular_speed_conversion(self):
        """1. RPM ↔ angular-speed conversion"""
        state = EngineDynamicsModel.calculate(self.nominal_input)
        expected_rpm = state.engine_angular_speed_rad_s * 60.0 / (2.0 * math.pi)
        self.assertAlmostEqual(state.engine_rpm, expected_rpm, places=4)

    def test_02_power_to_torque_numerical_correctness(self):
        """2. power-to-torque numerical correctness"""
        state = EngineDynamicsModel.calculate(self.nominal_input)
        # T_ind = P_ind / omega_curr
        expected_t = 85800.0 / 607.37
        self.assertAlmostEqual(state.indicated_torque_nm, expected_t, places=4)

    def test_03_positive_net_torque_increases_rpm(self):
        """3. positive net torque increases RPM"""
        env = self.nominal_input
        env.indicated_power_w = 200000.0  # Massive power to force positive acceleration
        state = EngineDynamicsModel.calculate(env)
        self.assertGreater(state.net_torque_nm, 0.0)
        self.assertGreater(state.angular_acceleration_rad_s2, 0.0)
        self.assertGreater(state.engine_angular_speed_rad_s, env.engine_angular_speed_rad_s)

    def test_04_negative_net_torque_decreases_rpm(self):
        """4. negative net torque decreases RPM"""
        env = self.nominal_input
        env.indicated_power_w = 0.0  # Zero power
        state = EngineDynamicsModel.calculate(env)
        self.assertLess(state.net_torque_nm, 0.0)
        self.assertLess(state.angular_acceleration_rad_s2, 0.0)
        self.assertLess(state.engine_angular_speed_rad_s, env.engine_angular_speed_rad_s)

    def test_06_friction_increases_opposing_torque(self):
        """6. friction increases opposing torque"""
        env1 = self.nominal_input
        env1.engine_angular_speed_rad_s = 200.0
        state1 = EngineDynamicsModel.calculate(env1)
        
        env2 = self.nominal_input
        env2.engine_angular_speed_rad_s = 600.0
        state2 = EngineDynamicsModel.calculate(env2)
        
        self.assertGreater(state2.friction_torque_nm, state1.friction_torque_nm)

    def test_07_friction_remains_non_negative(self):
        """7. friction remains non-negative"""
        env = self.nominal_input
        env.engine_angular_speed_rad_s = -50.0  # Should be clamped
        state = EngineDynamicsModel.calculate(env)
        self.assertGreaterEqual(state.friction_torque_nm, 0.0)

    def test_08_starter_torque_accelerates_stationary_engine(self):
        """8. starter torque accelerates stationary engine"""
        env = self.nominal_input
        env.engine_angular_speed_rad_s = 0.0
        env.indicated_power_w = 0.0
        env.starter_engaged = True
        state = EngineDynamicsModel.calculate(env)
        self.assertGreater(state.net_torque_nm, 0.0)
        self.assertGreater(state.engine_angular_speed_rad_s, 0.0)

    def test_09_starter_disengagement_behavior(self):
        """9. starter disengagement behavior"""
        env = self.nominal_input
        env.engine_angular_speed_rad_s = 0.0
        env.indicated_power_w = 0.0
        env.starter_engaged = False
        state = EngineDynamicsModel.calculate(env)
        # Should sit still
        self.assertEqual(state.net_torque_nm, 0.0)
        self.assertEqual(state.engine_angular_speed_rad_s, 0.0)

    def test_10_zero_rpm_numerical_stability(self):
        """10. zero-RPM numerical stability"""
        env = self.nominal_input
        env.engine_angular_speed_rad_s = 0.0
        env.indicated_power_w = 1000.0  # Should yield 0 indicated torque for safety
        state = EngineDynamicsModel.calculate(env)
        self.assertEqual(state.indicated_torque_nm, 0.0)
        self.assertTrue(math.isfinite(state.engine_angular_speed_rad_s))

    def test_11_near_zero_rpm_numerical_stability(self):
        """11. near-zero-RPM numerical stability"""
        env = self.nominal_input
        env.engine_angular_speed_rad_s = 0.5  # < 1.0 rad/s
        env.indicated_power_w = 1000.0
        state = EngineDynamicsModel.calculate(env)
        self.assertEqual(state.indicated_torque_nm, 0.0)
        self.assertTrue(math.isfinite(state.angular_acceleration_rad_s2))

    def test_12_rpm_never_becomes_negative(self):
        """12. RPM never becomes negative"""
        env = self.nominal_input
        env.engine_angular_speed_rad_s = 1.0
        env.indicated_power_w = 0.0
        env.timestep_s = 10.0  # Massive step to force negative
        state = EngineDynamicsModel.calculate(env)
        self.assertGreaterEqual(state.engine_rpm, 0.0)

    def test_13_angular_velocity_never_becomes_negative(self):
        """13. angular velocity never becomes negative"""
        env = self.nominal_input
        env.engine_angular_speed_rad_s = 1.0
        env.indicated_power_w = 0.0
        env.timestep_s = 10.0
        state = EngineDynamicsModel.calculate(env)
        self.assertGreaterEqual(state.engine_angular_speed_rad_s, 0.0)

    def test_14_timestep_validation(self):
        """14. timestep validation"""
        env = self.nominal_input
        env.timestep_s = -0.1
        state = EngineDynamicsModel.calculate(env)
        # Should treat as 0.0 internally, no change in speed
        self.assertEqual(state.engine_angular_speed_rad_s, 607.37)

    def test_17_gearbox_speed_ratio_correctness(self):
        """17. gearbox speed-ratio correctness"""
        state = EngineDynamicsModel.calculate(self.nominal_input)
        expected = state.engine_rpm * EngineDynamicsModel.GEARBOX_RATIO
        self.assertAlmostEqual(state.propeller_rpm, expected)

    def test_24_engine_side_load_torque_has_correct_sign(self):
        """24. engine-side load torque has correct sign"""
        state = EngineDynamicsModel.calculate(self.nominal_input)
        self.assertGreaterEqual(state.propeller_load_torque_nm, 0.0)

    def test_25_rated_condition_5800_rpm_consistency_check(self):
        """25. rated-condition 5800 RPM consistency check"""
        # Nominal Rotax 115hp = 85.8 kW @ 5800 RPM
        env = self.nominal_input
        env.engine_angular_speed_rad_s = 5800.0 * 2.0 * math.pi / 60.0
        env.indicated_power_w = 85800.0
        state = EngineDynamicsModel.calculate(env)
        
        # P_shaft should be indicated minus friction
        self.assertLess(state.shaft_power_w, 85800.0)
        self.assertGreater(state.shaft_power_w, 65000.0) # Should not lose more than ~20kW to friction at rated
        
        # Indicated torque check
        expected_t_ind = 85800.0 / env.engine_angular_speed_rad_s
        self.assertAlmostEqual(state.indicated_torque_nm, expected_t_ind, places=2)

    def test_30_complete_1a_1e_test_suite(self):
        """30. complete 1A-1E test suite integration"""
        # A quick integration smoke test
        from src.digital_twin.physics.atmosphere import AtmosphereModel, EnvironmentInput
        from src.digital_twin.physics.turbo_intake import TurboIntakeModel, ExhaustState, TurboState
        from src.digital_twin.physics.airflow import AirflowModel, AirflowInput
        from src.digital_twin.physics.combustion import CombustionModel, FuelCombustionInput
        
        dt = 0.01
        
        atm_in = EnvironmentInput(altitude_m=1000.0, temperature_offset_k=0.0)
        atm_out = AtmosphereModel.calculate(atm_in)
        
        ti_state_in = TurboState(
            turbo_speed_rad_s=5000.0,
            manifold_pressure_pa=100000.0,
            manifold_temperature_k=300.0,
            wastegate_position=0.0,
            tcu_error_integral=0.0
        )
        
        exh = ExhaustState(atm_out.pressure_pa+10000, 1000.0, 0.1)
        
        ti_out = TurboIntakeModel.step(
            dt=dt,
            atm=atm_out,
            exh=exh,
            engine_mass_flow_kg_s=0.1,
            target_map_pa=110000.0,
            current_state=ti_state_in
        )
        
        af_in = AirflowInput(
            manifold_pressure_pa=ti_out.manifold_pressure_pa,
            manifold_temperature_k=ti_out.manifold_temperature_k,
            engine_rpm=5000.0,
            throttle_position=1.0
        )
        af_out = AirflowModel.calculate(af_in)
        
        cb_in = FuelCombustionInput(
            engine_rpm=5000.0,
            throttle_position=1.0,
            manifold_pressure_pa=ti_out.manifold_pressure_pa,
            manifold_temperature_k=ti_out.manifold_temperature_k,
            air_mass_flow_kg_s=af_out.air_mass_flow_kg_s,
            ambient_pressure_pa=atm_out.pressure_pa,
            fuel_pressure_delta_pa=25000.0
        )
        cb_out = CombustionModel.calculate(cb_in)
        
        ed_in = EngineDynamicsInput(
            engine_angular_speed_rad_s=5000.0 * 2*math.pi/60.0,
            indicated_power_w=cb_out.indicated_power_w,
            starter_engaged=False,
            timestep_s=dt,
            propeller_load_torque_nm=0.0
        )
        ed_out = EngineDynamicsModel.calculate(ed_in)
        
        self.assertGreater(ed_out.indicated_torque_nm, 0.0)
        self.assertGreater(ed_out.shaft_power_w, 0.0)

if __name__ == '__main__':
    unittest.main()
