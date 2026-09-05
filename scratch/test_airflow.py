import unittest
import math
import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.digital_twin.physics.airflow import AirflowModel, AirflowInput
from src.digital_twin.physics.atmosphere import AtmosphereModel, EnvironmentInput, R_D
from src.digital_twin.physics.turbo_intake import TurboIntakeModel, TurboState, ExhaustState

class TestAirflowModel(unittest.TestCase):
    def setUp(self):
        # Standard nominal conditions
        self.std_p = 101325.0
        self.std_t = 288.15
        self.nominal_rpm = 5500.0
        self.nominal_throttle = 1.0
        
    def test_01_rotax_displacement(self):
        """1. Verify expected Rotax 914 displacement based on geometry."""
        # 79.5mm bore, 61.0mm stroke, 4 cylinders. Expected ~1.211 Liters
        expected_displacement_m3 = (math.pi / 4.0) * (0.0795 ** 2) * 0.061 * 4
        self.assertAlmostEqual(AirflowModel.V_D, expected_displacement_m3, places=6)
        self.assertTrue(1.210e-3 < AirflowModel.V_D < 1.212e-3)

    def test_02_independent_charge_density(self):
        """2. Independent charge density thermodynamics equation check."""
        # rho = P / (R * T)
        P = 150000.0
        T = 300.0
        
        # Independently calculate expected value
        rho_expected = P / (R_D * T)
        
        env = AirflowInput(P, T, 0.0, 1.0) # Zero RPM forces P_charge = P_airbox
        result = AirflowModel.calculate(env)
        
        # Verify implementation matches the independent equation
        self.assertAlmostEqual(result.charge_density_kg_m3, rho_expected, places=4)

    def test_03_independent_speed_density_equation(self):
        """3. Independent core cylinder speed-density equation verification."""
        P_charge = 150000.0
        T_charge = 300.0
        RPM = 5000.0
        
        # We manually calculate expected eta_v to avoid using the implementation's helper directly.
        rpm_term = 0.15 * (1.0 - ((5000.0 - 5800.0)/5800.0)**2)
        p_term = 0.05 * (150000.0 / 101325.0)
        expected_eta_v = 0.75 + rpm_term + p_term
        expected_eta_v = max(0.1, min(0.95, expected_eta_v))
        
        V_d = (math.pi / 4.0) * (0.0795 ** 2) * 0.061 * 4
        rho = P_charge / (R_D * T_charge)
        N = RPM / 60.0
        
        expected_mass_flow = expected_eta_v * rho * V_d * (N / 2.0)
        
        # Now run the model at this charge pressure condition using the internal helper for equation validation.
        actual_mass_flow = AirflowModel._cylinder_mass_flow(P_charge, T_charge, RPM, expected_eta_v)
        
        self.assertAlmostEqual(actual_mass_flow, expected_mass_flow, places=6)

    def test_04_independent_unchoked_restriction(self):
        """4. Independent unchoked throttle restriction flow."""
        P_up = 120000.0
        P_down = 100000.0 # PR = 100/120 = 0.833 (unchoked)
        T_up = 300.0
        gamma = 1.4
        A_eff = 0.001
        C_d = 0.8
        
        pr = P_down / P_up
        base = max(0.0, pr**(2.0/gamma) - pr**((gamma+1.0)/gamma))
        phi = math.sqrt((2.0 * gamma / (gamma - 1.0)) * base)
        
        expected_flow = C_d * A_eff * (P_up / math.sqrt(R_D * T_up)) * phi
        
        actual_flow = AirflowModel._throttle_mass_flow(P_up, P_down, T_up, A_eff)
        self.assertAlmostEqual(actual_flow, expected_flow, places=6)

    def test_05_independent_choked_restriction(self):
        """5. Independent choked throttle restriction flow."""
        P_up = 150000.0
        P_down = 50000.0 # PR = 50/150 = 0.333 (choked)
        T_up = 300.0
        gamma = 1.4
        A_eff = 0.001
        C_d = 0.8
        
        phi = math.sqrt(gamma * (2.0 / (gamma + 1.0))**((gamma + 1.0) / (gamma - 1.0)))
        expected_flow = C_d * A_eff * (P_up / math.sqrt(R_D * T_up)) * phi
        
        actual_flow = AirflowModel._throttle_mass_flow(P_up, P_down, T_up, A_eff)
        self.assertAlmostEqual(actual_flow, expected_flow, places=6)

    def test_06_rpm_increases_airflow(self):
        """6. Higher RPM generally increases airflow (holding pressure/throttle)."""
        env_low = AirflowInput(self.std_p, self.std_t, 3000.0, 1.0)
        env_high = AirflowInput(self.std_p, self.std_t, 5000.0, 1.0)
        
        res_low = AirflowModel.calculate(env_low)
        res_high = AirflowModel.calculate(env_high)
        
        self.assertGreater(res_high.air_mass_flow_kg_s, res_low.air_mass_flow_kg_s)
        
    def test_07_pressure_increases_airflow(self):
        """7. Higher charge pressure increases airflow."""
        env_low = AirflowInput(100000.0, self.std_t, self.nominal_rpm, 1.0)
        env_high = AirflowInput(150000.0, self.std_t, self.nominal_rpm, 1.0)
        
        res_low = AirflowModel.calculate(env_low)
        res_high = AirflowModel.calculate(env_high)
        
        self.assertGreater(res_high.air_mass_flow_kg_s, res_low.air_mass_flow_kg_s)
        
    def test_08_temperature_decreases_density_and_airflow(self):
        """8. Higher charge temperature decreases density and airflow."""
        env_cold = AirflowInput(self.std_p, 288.0, self.nominal_rpm, 1.0)
        env_hot = AirflowInput(self.std_p, 330.0, self.nominal_rpm, 1.0)
        
        res_cold = AirflowModel.calculate(env_cold)
        res_hot = AirflowModel.calculate(env_hot)
        
        self.assertLess(res_hot.charge_density_kg_m3, res_cold.charge_density_kg_m3)
        self.assertLess(res_hot.air_mass_flow_kg_s, res_cold.air_mass_flow_kg_s)
        
    def test_09_throttle_restriction_closed(self):
        """9. Throttle restriction reduces airflow when closed (idle)."""
        env_wot = AirflowInput(self.std_p, self.std_t, self.nominal_rpm, 1.0)
        env_idle = AirflowInput(self.std_p, self.std_t, self.nominal_rpm, 0.0)
        
        res_wot = AirflowModel.calculate(env_wot)
        res_idle = AirflowModel.calculate(env_idle)
        
        self.assertLess(res_idle.air_mass_flow_kg_s, res_wot.air_mass_flow_kg_s)
        self.assertLess(res_idle.charge_pressure_pa, res_wot.charge_pressure_pa)
        
    def test_10_throttle_opening_increases_airflow(self):
        """10. Opening throttle smoothly increases airflow."""
        env_25 = AirflowInput(self.std_p, self.std_t, self.nominal_rpm, 0.25)
        env_50 = AirflowInput(self.std_p, self.std_t, self.nominal_rpm, 0.50)
        env_75 = AirflowInput(self.std_p, self.std_t, self.nominal_rpm, 0.75)
        
        m_25 = AirflowModel.calculate(env_25).air_mass_flow_kg_s
        m_50 = AirflowModel.calculate(env_50).air_mass_flow_kg_s
        m_75 = AirflowModel.calculate(env_75).air_mass_flow_kg_s
        
        self.assertGreater(m_50, m_25)
        self.assertGreater(m_75, m_50)
        
    def test_11_cylinder_filling_limits_airflow(self):
        """11. Cylinder filling demand bounds the throttle capacity at WOT."""
        env = AirflowInput(self.std_p, self.std_t, self.nominal_rpm, 1.0)
        res = AirflowModel.calculate(env)
        
        self.assertGreater(res.charge_pressure_pa, self.std_p * 0.95)
        self.assertLessEqual(res.charge_pressure_pa, self.std_p)
        
    def test_12_airflow_non_negative(self):
        """12. Airflow remains non-negative."""
        env = AirflowInput(self.std_p, self.std_t, 0.0, 0.0)
        res = AirflowModel.calculate(env)
        self.assertGreaterEqual(res.air_mass_flow_kg_s, 0.0)

    def test_13_invalid_rpm_rejected(self):
        """13. Invalid RPM (< 0) raises ValueError."""
        with self.assertRaises(ValueError):
            AirflowModel.calculate(AirflowInput(self.std_p, self.std_t, -100.0, 1.0))

    def test_14_invalid_throttle_rejected(self):
        """14. Invalid throttle (< 0 or > 1) raises ValueError."""
        with self.assertRaises(ValueError):
            AirflowModel.calculate(AirflowInput(self.std_p, self.std_t, 1000.0, -0.1))
        with self.assertRaises(ValueError):
            AirflowModel.calculate(AirflowInput(self.std_p, self.std_t, 1000.0, 1.1))

    def test_15_invalid_pressure_rejected(self):
        """15. Invalid pressure (<= 0) raises ValueError."""
        with self.assertRaises(ValueError):
            AirflowModel.calculate(AirflowInput(0.0, self.std_t, 1000.0, 1.0))
            
    def test_16_invalid_temperature_rejected(self):
        """16. Invalid temperature (<= 0 K) raises ValueError."""
        with self.assertRaises(ValueError):
            AirflowModel.calculate(AirflowInput(self.std_p, 0.0, 1000.0, 1.0))

    def test_17_etav_remains_bounded(self):
        """17. eta_v remains inside documented bounds."""
        env_extreme = AirflowInput(300000.0, 200.0, 10000.0, 1.0) # Insane inputs
        res = AirflowModel.calculate(env_extreme)
        
        self.assertGreaterEqual(res.volumetric_efficiency, AirflowModel.ETA_V_MIN)
        self.assertLessEqual(res.volumetric_efficiency, AirflowModel.ETA_V_MAX)

    def test_18_numerical_stability(self):
        """18. Numerical solver stability over grid."""
        rpms = [1000, 3000, 5800, 7000]
        pressures = [50000, 100000, 150000]
        throttles = [0.1, 0.5, 1.0]
        
        for r in rpms:
            for p in pressures:
                for th in throttles:
                    env = AirflowInput(p, 300.0, r, th)
                    res = AirflowModel.calculate(env)
                    self.assertTrue(math.isfinite(res.air_mass_flow_kg_s))
                    self.assertGreaterEqual(res.air_mass_flow_kg_s, 0.0)
                    self.assertTrue(math.isfinite(res.charge_pressure_pa))
                    self.assertGreater(res.charge_pressure_pa, 0.0)

    def test_19_integration_with_phase_1b(self):
        """19. Coupled Integration Test with Phase 1B/1A."""
        atm_env = EnvironmentInput(altitude_m=2000.0) # ~ 6500 ft
        atm_state = AtmosphereModel.calculate(atm_env)
        
        exh = ExhaustState(pressure_pa=120000.0, temperature_k=900.0, mass_flow_kg_s=0.1)
        
        turbo_state = TurboState(
            turbo_speed_rad_s=10000.0,
            manifold_pressure_pa=atm_state.pressure_pa,
            manifold_temperature_k=atm_state.temperature_k,
            wastegate_position=0.0,
            tcu_error_integral=0.0
        )
        
        rpm = 5500.0
        throttle = 1.0
        
        dt = 0.01
        for _ in range(10):
            air_in = AirflowInput(
                manifold_pressure_pa=turbo_state.manifold_pressure_pa,
                manifold_temperature_k=turbo_state.manifold_temperature_k,
                engine_rpm=rpm,
                throttle_position=throttle
            )
            air_state = AirflowModel.calculate(air_in)
            
            turbo_state = TurboIntakeModel.step(
                dt=dt,
                atm=atm_state,
                exh=exh,
                engine_mass_flow_kg_s=air_state.air_mass_flow_kg_s,
                target_map_pa=130000.0,
                current_state=turbo_state
            )
            
            self.assertTrue(math.isfinite(turbo_state.manifold_pressure_pa))
            self.assertGreater(turbo_state.manifold_pressure_pa, 0.0)
            self.assertTrue(math.isfinite(air_state.air_mass_flow_kg_s))
            self.assertGreaterEqual(air_state.air_mass_flow_kg_s, 0.0)

    def test_20_hot_high_altitude(self):
        """
        20. Hot + High-Altitude validation scenario.
        Verifies correct causal propagation: Environment -> Atmosphere -> Turbo -> Airflow.
        """
        rpm = 5500.0
        throttle = 1.0
        target_map = 100000.0
        
        def simulate_conditions(alt_m, temp_offset):
            atm_env = EnvironmentInput(altitude_m=alt_m, temperature_offset_k=temp_offset)
            atm_state = AtmosphereModel.calculate(atm_env)
            
            exh = ExhaustState(pressure_pa=120000.0, temperature_k=900.0, mass_flow_kg_s=0.1)
            
            turbo_state = TurboState(
                turbo_speed_rad_s=50000.0,  # Fast enough to provide some boost
                manifold_pressure_pa=atm_state.pressure_pa,
                manifold_temperature_k=atm_state.temperature_k,
                wastegate_position=0.0,
                tcu_error_integral=0.0
            )
            
            # Step turbo to generate some MAP/MAT
            turbo_state = TurboIntakeModel.step(
                dt=0.1,
                atm=atm_state,
                exh=exh,
                engine_mass_flow_kg_s=0.05,
                target_map_pa=target_map,
                current_state=turbo_state
            )
            
            air_in = AirflowInput(
                manifold_pressure_pa=turbo_state.manifold_pressure_pa,
                manifold_temperature_k=turbo_state.manifold_temperature_k,
                engine_rpm=rpm,
                throttle_position=throttle
            )
            return AirflowModel.calculate(air_in)
            
        # A. Standard Sea Level
        state_sl = simulate_conditions(0.0, 0.0)
        # B. High Altitude (3000m)
        state_high = simulate_conditions(3000.0, 0.0)
        # C. Hot + High Altitude (3000m, +20K)
        state_hot_high = simulate_conditions(3000.0, 20.0)
        
        # Verify quantitative causality
        # Hotter temperature should yield lower charge density (at similar high altitude pressures)
        expected_hot_rho = state_hot_high.charge_pressure_pa / (R_D * state_hot_high.charge_temperature_k)
        self.assertAlmostEqual(state_hot_high.charge_density_kg_m3, expected_hot_rho, places=4)
        
        # Verify the direction of environmental effects:
        # Hotter air at the same altitude is less dense
        self.assertLess(state_hot_high.charge_density_kg_m3, state_high.charge_density_kg_m3)
        self.assertLess(state_hot_high.air_mass_flow_kg_s, state_high.air_mass_flow_kg_s)
        
        # High altitude air has lower pressure, so without infinite turbo spool, density is lower than SL
        self.assertLess(state_high.charge_density_kg_m3, state_sl.charge_density_kg_m3)

if __name__ == '__main__':
    unittest.main()
