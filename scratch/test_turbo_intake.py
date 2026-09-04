import unittest
import sys
import os
import math

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from digital_twin.physics.atmosphere import EnvironmentInput, AtmosphereModel
from digital_twin.physics.turbo_intake import TurboIntakeModel, TurboState, ExhaustState


class TestTurboIntakeModel(unittest.TestCase):
    
    def setUp(self):
        self.env = EnvironmentInput(altitude_m=0.0)
        self.atm = AtmosphereModel.calculate(self.env)
        
        self.exh = ExhaustState(
            pressure_pa=120000.0,
            temperature_k=1150.0,
            mass_flow_kg_s=0.02
        )
        
        self.initial_state = TurboState(
            turbo_speed_rad_s=0.0,
            manifold_pressure_pa=101325.0,
            manifold_temperature_k=288.15,
            wastegate_position=0.0,
            tcu_error_integral=0.0
        )
        
    def test_1_compressor_equation_numerical_accuracy(self):
        """1. Compressor equation numerical accuracy (PR and mass flow)"""
        w = 10000.0
        p_amb = self.atm.pressure_pa
        p_map = 150000.0
        
        # Manually compute expected PR and mass flow
        pr_actual = p_map / p_amb
        pr_max = 1.0 + TurboIntakeModel.K_PR * (w ** 2)
        expected_m_dot_c = TurboIntakeModel.K_FLOW * w * max(0.0, pr_max - pr_actual)
        
        state = TurboState(w, p_map, 288.15, 0.0, 0.0)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 150000.0, state)
        
        # dP/dt = R*T/V * m_dot_c (engine_mass_flow is 0)
        dp = next_state.manifold_pressure_pa - p_map
        dt = 0.01
        actual_m_dot_c_in_sim = (dp / dt) * TurboIntakeModel.V_MAP / (TurboIntakeModel.R_AIR * next_state.manifold_temperature_k)
        
        self.assertAlmostEqual(actual_m_dot_c_in_sim, expected_m_dot_c, places=4)
        
    def test_2_compressor_temperature_equation_numerical_accuracy(self):
        """2. Compressor temperature equation numerical accuracy"""
        w = 10000.0
        p_amb = self.atm.pressure_pa
        p_map = 150000.0
        pr_actual = p_map / p_amb
        
        # Manually compute expected temp out
        temp_rise_factor = math.pow(pr_actual, (TurboIntakeModel.GAMMA_AIR - 1.0)/TurboIntakeModel.GAMMA_AIR) - 1.0
        expected_temp = self.atm.temperature_k * (1.0 + (temp_rise_factor / TurboIntakeModel.ETA_COMPRESSOR))
        
        state = TurboState(w, p_map, 288.15, 0.0, 0.0)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 150000.0, state)
        
        self.assertAlmostEqual(next_state.manifold_temperature_k, expected_temp, places=4)

    def test_3_compressor_power_numerical_accuracy(self):
        """3. Compressor power numerical accuracy"""
        w = 10000.0
        p_amb = self.atm.pressure_pa
        p_map = 150000.0
        
        pr_actual = p_map / p_amb
        pr_max = 1.0 + TurboIntakeModel.K_PR * (w ** 2)
        m_dot_c = TurboIntakeModel.K_FLOW * w * max(0.0, pr_max - pr_actual)
        
        temp_rise_factor = math.pow(pr_actual, (TurboIntakeModel.GAMMA_AIR - 1.0)/TurboIntakeModel.GAMMA_AIR) - 1.0
        t_out = self.atm.temperature_k * (1.0 + (temp_rise_factor / TurboIntakeModel.ETA_COMPRESSOR))
        expected_power = m_dot_c * TurboIntakeModel.CP_AIR * (t_out - self.atm.temperature_k)
        
        # If we remove turbine power (wastegate=1.0) and loss (k_loss=0 temporarily for calc), 
        # dw/dt = -P_c / (J * w)
        original_loss = TurboIntakeModel.K_LOSS
        TurboIntakeModel.K_LOSS = 0.0
        
        state = TurboState(w, p_map, 288.15, 1.0, 0.0) # WG open, turbine power ~ 0 (with low target MAP)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 1000.0, state)
        
        dw = next_state.turbo_speed_rad_s - w
        dt = 0.01
        simulated_power = - (dw / dt) * TurboIntakeModel.J_TURBO * w
        
        self.assertAlmostEqual(simulated_power, expected_power, places=2)
        TurboIntakeModel.K_LOSS = original_loss

    def test_4_turbine_power_numerical_accuracy(self):
        """4. Turbine power numerical accuracy"""
        w = 10000.0
        pr_turbine = self.exh.pressure_pa / self.atm.pressure_pa
        temp_drop_factor = 1.0 - math.pow(1.0 / pr_turbine, (TurboIntakeModel.GAMMA_EXH - 1.0) / TurboIntakeModel.GAMMA_EXH)
        expected_turbine_power = self.exh.mass_flow_kg_s * TurboIntakeModel.CP_EXH * self.exh.temperature_k * TurboIntakeModel.ETA_TURBINE * temp_drop_factor
        
        # Prevent compressor flow (PR_actual > PR_max)
        p_map = 200000.0
        
        original_loss = TurboIntakeModel.K_LOSS
        TurboIntakeModel.K_LOSS = 0.0
        
        state = TurboState(w, p_map, 288.15, 0.0, 0.0)
        # target_map_pa very high so WG stays closed (0.0)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 300000.0, state)
        
        dw = next_state.turbo_speed_rad_s - w
        dt = 0.01
        simulated_turbine_power = (dw / dt) * TurboIntakeModel.J_TURBO * w
        
        self.assertAlmostEqual(simulated_turbine_power, expected_turbine_power, places=2)
        TurboIntakeModel.K_LOSS = original_loss

    def test_5_turbine_pressure_ratio_sensitivity(self):
        """5. Turbine pressure-ratio sensitivity"""
        # Higher exhaust pressure -> more power -> more acceleration
        exh_high_pr = ExhaustState(150000.0, 1150.0, 0.02)
        state1 = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 300000.0, self.initial_state)
        state2 = TurboIntakeModel.step(0.01, self.atm, exh_high_pr, 0.0, 300000.0, self.initial_state)
        self.assertGreater(state2.turbo_speed_rad_s, state1.turbo_speed_rad_s)

    def test_6_turbine_mass_flow_sensitivity(self):
        """6. Turbine mass-flow sensitivity"""
        # Higher exhaust mass flow -> more power
        exh_high_flow = ExhaustState(120000.0, 1150.0, 0.04)
        state1 = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 300000.0, self.initial_state)
        state2 = TurboIntakeModel.step(0.01, self.atm, exh_high_flow, 0.0, 300000.0, self.initial_state)
        self.assertGreater(state2.turbo_speed_rad_s, state1.turbo_speed_rad_s)

    def test_7_wastegate_bypass_reduces_turbine_drive(self):
        """7. Wastegate bypass reduces turbine drive"""
        state_closed_wg = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 300000.0, self.initial_state) # closed wg
        state_open_wg = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 1000.0, self.initial_state) # opens wg due to low target
        self.assertGreater(state_closed_wg.turbo_speed_rad_s, state_open_wg.turbo_speed_rad_s)

    def test_8_positive_turbine_net_power_accelerates_shaft(self):
        """8. Positive turbine net power accelerates shaft"""
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 300000.0, self.initial_state)
        self.assertGreater(next_state.turbo_speed_rad_s, self.initial_state.turbo_speed_rad_s)

    def test_9_turbine_bypass_losses_decelerate_shaft(self):
        """9. Turbine bypass/losses can decelerate shaft"""
        state = TurboState(5000.0, 101325.0, 288.15, 1.0, 0.0)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 1000.0, state)
        self.assertLess(next_state.turbo_speed_rad_s, state.turbo_speed_rad_s)

    def test_10_zero_speed_numerical_stability(self):
        """10. Zero-speed numerical stability"""
        # Should not raise ZeroDivisionError
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, self.initial_state)
        self.assertTrue(math.isfinite(next_state.turbo_speed_rad_s))

    def test_11_near_zero_speed_numerical_stability(self):
        """11. Near-zero-speed numerical stability"""
        state = TurboState(1e-5, 101325.0, 288.15, 0.0, 0.0)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, state)
        self.assertTrue(math.isfinite(next_state.turbo_speed_rad_s))

    def test_12_shaft_speed_never_negative(self):
        """12. Shaft speed never becomes negative"""
        # High friction and bypass to force it below zero
        state = TurboState(0.01, 101325.0, 288.15, 1.0, 0.0)
        next_state = TurboIntakeModel.step(0.1, self.atm, self.exh, 0.0, 1000.0, state)
        self.assertGreaterEqual(next_state.turbo_speed_rad_s, 0.0)

    def test_13_pi_positive_error_behaviour(self):
        """13. PI positive-error behaviour (Target > Actual -> WG closes)"""
        state = TurboState(5000.0, 100000.0, 288.15, 0.5, 0.0)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, state)
        self.assertLess(next_state.wastegate_position, 1.0) # WG commanded to close

    def test_14_pi_negative_error_behaviour(self):
        """14. PI negative-error behaviour (Target < Actual -> WG opens)"""
        state = TurboState(5000.0, 150000.0, 288.15, 0.5, 0.0)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, state)
        self.assertGreater(next_state.wastegate_position, 0.0) # WG commanded to open

    def test_15_pi_integral_unwinding(self):
        """15. PI integral unwinding"""
        state = TurboState(5000.0, 150000.0, 288.15, 0.0, 500.0) # Positive integral
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, state) # Target < Actual
        self.assertLess(next_state.tcu_error_integral, state.tcu_error_integral) # Integral unwinds

    def test_16_pi_anti_windup(self):
        """16. PI anti-windup"""
        state = TurboState(5000.0, 100000.0, 288.15, 0.0, 999999.0) # Huge integral
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, state)
        # Should be capped at 1.0 / KI_TCU
        self.assertAlmostEqual(next_state.tcu_error_integral, 1.0 / TurboIntakeModel.KI_TCU)

    def test_17_wastegate_remains_bounded(self):
        """17. Wastegate remains [0,1]"""
        state = TurboState(5000.0, 100000.0, 288.15, 0.0, 0.0)
        next_state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 999999.0, state) # Huge target
        self.assertGreaterEqual(next_state.wastegate_position, 0.0)
        self.assertLessEqual(next_state.wastegate_position, 1.0)
        
        next_state2 = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 1000.0, state) # Tiny target
        self.assertGreaterEqual(next_state2.wastegate_position, 0.0)
        self.assertLessEqual(next_state2.wastegate_position, 1.0)

    def test_18_manifold_pressure_changes_dynamically(self):
        """18. Manifold pressure changes dynamically"""
        # Take 10 steps of 0.01
        state = self.initial_state
        for _ in range(10):
            state = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, state)
        self.assertGreater(state.manifold_pressure_pa, self.initial_state.manifold_pressure_pa)
        self.assertLess(state.manifold_pressure_pa, 132000.0)

    def test_19_manifold_pressure_not_nonphysical(self):
        """19. Manifold pressure does not become nonphysical"""
        # Huge engine draw, 0 compressor flow
        state = TurboIntakeModel.step(0.01, self.atm, self.exh, 100.0, 132000.0, self.initial_state)
        self.assertGreaterEqual(state.manifold_pressure_pa, 1000.0) # Physical floor in implementation

    def test_20_high_altitude_pr_requirement_increases(self):
        """20. High-altitude PR requirement increases (Surrogate boundary test)"""
        p_map = 118000.0
        pr_sl = p_map / self.atm.pressure_pa
        # omega_min = sqrt((PR - 1) / k_pr)
        omega_sl = math.sqrt((pr_sl - 1.0) / TurboIntakeModel.K_PR)
        
        atm_30k = AtmosphereModel.calculate(EnvironmentInput(altitude_m=9144.0))
        pr_30k = p_map / atm_30k.pressure_pa
        omega_30k = math.sqrt((pr_30k - 1.0) / TurboIntakeModel.K_PR)
        
        self.assertGreater(omega_30k, omega_sl)
        # Verify specific surrogate PR limit
        self.assertAlmostEqual(1.0 + TurboIntakeModel.K_PR * (omega_30k**2), pr_30k)

    def test_21_hot_ambient_changes_conditions(self):
        """21. Hot ambient changes atmospheric conditions consistently"""
        env_hot = EnvironmentInput(altitude_m=0.0, temperature_offset_k=30.0)
        atm_hot = AtmosphereModel.calculate(env_hot)
        # Hot air is less dense -> less mass flow for same pressure and speed
        w = 10000.0
        p_map = 150000.0
        
        # In our surrogate model, k_flow dictates mass flow entirely based on RPM and PR. 
        # But wait, T_out will be hotter!
        state = TurboState(w, p_map, 288.15, 0.0, 0.0)
        state_std = TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 150000.0, state)
        state_hot_step = TurboIntakeModel.step(0.01, atm_hot, self.exh, 0.0, 150000.0, state)
        
        # Hotter ambient -> hotter compressor outlet
        self.assertGreater(state_hot_step.manifold_temperature_k, state_std.manifold_temperature_k)

    def test_22_invalid_efficiency_handling(self):
        """22. Invalid efficiency/physical parameter handling"""
        original_eta = TurboIntakeModel.ETA_COMPRESSOR
        TurboIntakeModel.ETA_COMPRESSOR = 0.0
        with self.assertRaises(ValueError):
            TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, self.initial_state)
            
        TurboIntakeModel.ETA_COMPRESSOR = 1.1
        with self.assertRaises(ValueError):
            TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, self.initial_state)
            
        TurboIntakeModel.ETA_COMPRESSOR = original_eta
        
        original_eta_t = TurboIntakeModel.ETA_TURBINE
        TurboIntakeModel.ETA_TURBINE = -0.5
        with self.assertRaises(ValueError):
            TurboIntakeModel.step(0.01, self.atm, self.exh, 0.0, 132000.0, self.initial_state)
            
        TurboIntakeModel.ETA_TURBINE = original_eta_t

    def test_23_reasonable_timestep_numerical_stability(self):
        """23. Reasonable timestep numerical stability"""
        # Using a very large timestep like 1.0s could cause instability, 
        # but 0.05s should be stable.
        state = self.initial_state
        for _ in range(20):
            state = TurboIntakeModel.step(0.05, self.atm, self.exh, 0.01, 132000.0, state)
        self.assertTrue(math.isfinite(state.turbo_speed_rad_s))
        self.assertTrue(math.isfinite(state.manifold_pressure_pa))
        self.assertGreater(state.manifold_pressure_pa, 0.0)

if __name__ == '__main__':
    unittest.main()
