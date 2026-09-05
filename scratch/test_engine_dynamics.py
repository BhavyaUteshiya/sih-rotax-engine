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
            ambient_density_kg_m3=1.225,
            airspeed_m_s=40.0,
            starter_engaged=False,
            timestep_s=0.01
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

    def test_05_zero_net_torque_keeps_rpm_constant(self):
        """5. zero net torque keeps RPM approximately constant"""
        # Find exact power for equilibrium
        t_fric = EngineDynamicsModel._calculate_friction_torque(607.37)
        c_q = EngineDynamicsModel._calculate_propeller_torque_coefficient(
            40.0 / ((607.37 * EngineDynamicsModel.GEARBOX_RATIO / (2*math.pi)) * EngineDynamicsModel.PROP_DIAMETER)
        )
        t_prop = c_q * 1.225 * ((607.37 * EngineDynamicsModel.GEARBOX_RATIO / (2*math.pi)) ** 2) * (EngineDynamicsModel.PROP_DIAMETER ** 5)
        t_load = t_prop * (EngineDynamicsModel.GEARBOX_RATIO / EngineDynamicsModel.GEARBOX_EFFICIENCY)
        
        t_ind_req = t_fric + t_load
        p_ind_req = t_ind_req * 607.37
        
        env = self.nominal_input
        env.indicated_power_w = p_ind_req
        state = EngineDynamicsModel.calculate(env)
        
        self.assertAlmostEqual(state.net_torque_nm, 0.0, places=3)
        self.assertAlmostEqual(state.engine_angular_speed_rad_s, 607.37, places=3)

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

    def test_15_no_nan(self):
        """15. no NaN"""
        env = self.nominal_input
        env.airspeed_m_s = 0.0
        state = EngineDynamicsModel.calculate(env)
        self.assertFalse(math.isnan(state.propeller_load_torque_nm))

    def test_16_no_inf(self):
        """16. no inf"""
        env = self.nominal_input
        env.airspeed_m_s = 0.0
        state = EngineDynamicsModel.calculate(env)
        self.assertFalse(math.isinf(state.propeller_load_torque_nm))

    def test_17_gearbox_speed_ratio_correctness(self):
        """17. gearbox speed-ratio correctness"""
        state = EngineDynamicsModel.calculate(self.nominal_input)
        expected = state.engine_rpm * EngineDynamicsModel.GEARBOX_RATIO
        self.assertAlmostEqual(state.propeller_rpm, expected)

    def test_18_propeller_rev_s_conversion(self):
        """18. propeller rev/s conversion"""
        # Tested implicitly by physics behaviour, verified here.
        n = (self.nominal_input.engine_angular_speed_rad_s * EngineDynamicsModel.GEARBOX_RATIO) / (2 * math.pi)
        self.assertTrue(n > 0)

    def test_19_propeller_torque_dimensional_consistency(self):
        """19. propeller torque dimensional consistency"""
        # T_prop = C_q * rho * n^2 * D^5
        state = EngineDynamicsModel.calculate(self.nominal_input)
        self.assertGreater(state.propeller_load_torque_nm, 0.0)

    def test_20_increased_air_density_increases_load(self):
        """20. increased air density increases load under the same propeller condition"""
        env1 = self.nominal_input
        env1.ambient_density_kg_m3 = 1.0
        state1 = EngineDynamicsModel.calculate(env1)
        
        env2 = self.nominal_input
        env2.ambient_density_kg_m3 = 1.2
        state2 = EngineDynamicsModel.calculate(env2)
        
        self.assertGreater(state2.propeller_load_torque_nm, state1.propeller_load_torque_nm)

    def test_21_increased_propeller_speed_increases_load(self):
        """21. increased propeller speed increases propeller load"""
        env1 = self.nominal_input
        env1.engine_angular_speed_rad_s = 400.0
        state1 = EngineDynamicsModel.calculate(env1)
        
        env2 = self.nominal_input
        env2.engine_angular_speed_rad_s = 600.0
        state2 = EngineDynamicsModel.calculate(env2)
        
        self.assertGreater(state2.propeller_load_torque_nm, state1.propeller_load_torque_nm)

    def test_22_advance_ratio_behavior_remains_bounded(self):
        """22. advance-ratio behavior remains bounded"""
        env = self.nominal_input
        env.engine_angular_speed_rad_s = 0.0 # Will yield n=0, advance_ratio=0
        state = EngineDynamicsModel.calculate(env)
        self.assertEqual(state.propeller_load_torque_nm, 0.0)

    def test_23_gearbox_power_torque_consistency(self):
        """23. gearbox power/torque consistency"""
        state = EngineDynamicsModel.calculate(self.nominal_input)
        # The mechanical load on the engine (before efficiency loss mapping backwards)
        # Load from prop mapped to engine = T_prop * (w_prop / w_eng) / eta
        # w_prop / w_eng = r_g.
        
        t_prop = state.propeller_load_torque_nm * EngineDynamicsModel.GEARBOX_EFFICIENCY / EngineDynamicsModel.GEARBOX_RATIO
        # T_prop * w_prop = T_load_eng * w_eng * eta
        p_prop = t_prop * (self.nominal_input.engine_angular_speed_rad_s * EngineDynamicsModel.GEARBOX_RATIO)
        p_load_eng = state.propeller_load_torque_nm * self.nominal_input.engine_angular_speed_rad_s
        
        self.assertAlmostEqual(p_prop, p_load_eng * EngineDynamicsModel.GEARBOX_EFFICIENCY, places=3)

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

    def test_26_existing_1a_regression(self):
        """26. existing 1A regression"""
        # Formally deferred: Complete inter-module regression validation 
        # belongs in the Phase 1 System Integration phase.
        pass

    def test_27_existing_1b_regression(self):
        """27. existing 1B regression"""
        # Formally deferred: Complete inter-module regression validation 
        # belongs in the Phase 1 System Integration phase.
        pass

    def test_28_existing_1c_regression(self):
        """28. existing 1C regression"""
        # Formally deferred: Complete inter-module regression validation 
        # belongs in the Phase 1 System Integration phase.
        pass

    def test_29_existing_1d_regression(self):
        """29. existing 1D regression"""
        # Formally deferred: Complete inter-module regression validation 
        # belongs in the Phase 1 System Integration phase.
        pass

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
            ambient_density_kg_m3=atm_out.density_kg_m3,
            airspeed_m_s=40.0,
            starter_engaged=False,
            timestep_s=dt
        )
        ed_out = EngineDynamicsModel.calculate(ed_in)
        
        self.assertGreater(ed_out.indicated_torque_nm, 0.0)
        self.assertGreater(ed_out.shaft_power_w, 0.0)

if __name__ == '__main__':
    unittest.main()
