import unittest
import sys
import os
import math
import copy

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.digital_twin.physics.thermal import ThermalModel, ThermalInput, ThermalState


class TestThermalModel(unittest.TestCase):

    def setUp(self):
        # Nominal operating point: warm engine at cruise
        self.nominal_input = ThermalInput(
            cht_temperature_k=380.0,     # ~107 °C
            oil_temperature_k=360.0,     # ~87 °C
            heat_loss_power_w=76900.0,   # From 1D at rated conditions
            ambient_temperature_k=288.15,
            ambient_density_kg_m3=1.225,
            airspeed_m_s=40.0,
            engine_rpm=5800.0,
            timestep_s=0.1
        )

    # === 1. Thermal capacity equation ===
    def test_01_thermal_capacity_equation(self):
        """1. thermal-capacity equation C = m * cp"""
        self.assertAlmostEqual(ThermalModel.C_CHT, ThermalModel.M_CHT * ThermalModel.CP_CHT)
        self.assertAlmostEqual(ThermalModel.C_OIL, ThermalModel.M_OIL * ThermalModel.CP_OIL)
        self.assertGreater(ThermalModel.C_CHT, 0.0)
        self.assertGreater(ThermalModel.C_OIL, 0.0)

    # === 2. Zero heat-input behavior ===
    def test_02_zero_heat_input_no_rise(self):
        """2. zero heat-input → CHT does not rise from heat source"""
        env = copy.deepcopy(self.nominal_input)
        env.heat_loss_power_w = 0.0
        # Start at ambient so no cooling gradient either
        env.cht_temperature_k = 288.15
        env.oil_temperature_k = 288.15
        state = ThermalModel.calculate(env)
        self.assertAlmostEqual(state.cht_heat_input_w, 0.0)
        # At equilibrium with ambient and zero input, dT/dt should be ~0
        self.assertAlmostEqual(state.dcht_dt_k_s, 0.0, places=5)

    # === 3. Positive heat-input raises CHT ===
    def test_03_positive_heat_input_raises_cht(self):
        """3. positive heat-input raises CHT"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 288.15
        env.oil_temperature_k = 288.15
        env.heat_loss_power_w = 50000.0
        state = ThermalModel.calculate(env)
        self.assertGreater(state.dcht_dt_k_s, 0.0)
        self.assertGreater(state.cht_temperature_k, 288.15)

    # === 4. CHT responds before oil ===
    def test_04_cht_responds_before_oil(self):
        """4. CHT initially responds faster than oil (direct heat input)"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 288.15
        env.oil_temperature_k = 288.15
        env.heat_loss_power_w = 50000.0
        state = ThermalModel.calculate(env)
        # CHT rate should be much larger than oil rate initially
        self.assertGreater(abs(state.dcht_dt_k_s), abs(state.doil_dt_k_s))

    # === 5. CHT-to-oil heat flow direction ===
    def test_05_cht_to_oil_heat_flow_direction(self):
        """5. heat flows from hotter CHT to cooler oil"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 400.0
        env.oil_temperature_k = 350.0
        state = ThermalModel.calculate(env)
        self.assertGreater(state.heat_cht_to_oil_w, 0.0)

    # === 6. Oil follows CHT with lag ===
    def test_06_oil_follows_cht_with_lag(self):
        """6. oil temperature follows CHT with thermal lag"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 400.0
        env.oil_temperature_k = 300.0
        state = ThermalModel.calculate(env)
        # Oil should be warming up (positive rate)
        self.assertGreater(state.doil_dt_k_s, 0.0)

    # === 7. Ambient cooling reduces temperature ===
    def test_07_ambient_cooling_reduces_temperature(self):
        """7. ambient cooling reduces temperature when no heat input"""
        env = copy.deepcopy(self.nominal_input)
        env.heat_loss_power_w = 0.0
        env.cht_temperature_k = 400.0
        env.oil_temperature_k = 370.0
        state = ThermalModel.calculate(env)
        self.assertLess(state.cht_temperature_k, 400.0)

    # === 8. Increased airspeed increases cooling ===
    def test_08_increased_airspeed_increases_cooling(self):
        """8. increased airspeed increases cooling"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.airspeed_m_s = 20.0
        state1 = ThermalModel.calculate(env1)

        env2 = copy.deepcopy(self.nominal_input)
        env2.airspeed_m_s = 60.0
        state2 = ThermalModel.calculate(env2)

        self.assertGreater(state2.cht_cooling_w, state1.cht_cooling_w)

    # === 9. Increased density increases cooling ===
    def test_09_increased_density_increases_cooling(self):
        """9. increased density increases cooling"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.ambient_density_kg_m3 = 0.8
        state1 = ThermalModel.calculate(env1)

        env2 = copy.deepcopy(self.nominal_input)
        env2.ambient_density_kg_m3 = 1.2
        state2 = ThermalModel.calculate(env2)

        self.assertGreater(state2.cht_cooling_w, state1.cht_cooling_w)

    # === 10. Lower density reduces forced cooling ===
    def test_10_lower_density_reduces_cooling(self):
        """10. lower density reduces forced cooling"""
        g_high = ThermalModel._calculate_cooling_conductance(
            ThermalModel.G_CHT_BASE, 1.225, 40.0)
        g_low = ThermalModel._calculate_cooling_conductance(
            ThermalModel.G_CHT_BASE, 0.7, 40.0)
        self.assertGreater(g_high, g_low)

    # === 11. High-power/low-airspeed hotter than high-power/high-airspeed ===
    def test_11_high_power_low_airspeed_hotter(self):
        """11. high-power/low-airspeed produces higher thermal state"""
        env1 = copy.deepcopy(self.nominal_input)
        env1.airspeed_m_s = 10.0
        env1.heat_loss_power_w = 76000.0
        state1 = ThermalModel.calculate(env1)

        env2 = copy.deepcopy(self.nominal_input)
        env2.airspeed_m_s = 60.0
        env2.heat_loss_power_w = 76000.0
        state2 = ThermalModel.calculate(env2)

        self.assertGreater(state1.cht_temperature_k, state2.cht_temperature_k)

    # === 12. No instantaneous temperature jump ===
    def test_12_no_instantaneous_temperature_jump(self):
        """12. temperature change is bounded by timestep (no teleporting)"""
        env = copy.deepcopy(self.nominal_input)
        env.timestep_s = 0.01
        state = ThermalModel.calculate(env)
        delta = abs(state.cht_temperature_k - env.cht_temperature_k)
        # For dt=0.01s, temperature change should be small (< 1 K)
        self.assertLess(delta, 1.0)

    # === 13. Zero/near-zero airspeed stability ===
    def test_13_zero_airspeed_stability(self):
        """13. zero/near-zero airspeed numerical stability"""
        env = copy.deepcopy(self.nominal_input)
        env.airspeed_m_s = 0.0
        state = ThermalModel.calculate(env)
        self.assertTrue(math.isfinite(state.cht_temperature_k))
        self.assertTrue(math.isfinite(state.oil_temperature_k))
        # Cooling should still be non-zero (natural convection via G_MIN)
        self.assertGreater(state.cht_cooling_w, 0.0)

    # === 14. Finite temperatures ===
    def test_14_finite_temperatures(self):
        """14. all output temperatures are finite"""
        state = ThermalModel.calculate(self.nominal_input)
        self.assertTrue(math.isfinite(state.cht_temperature_k))
        self.assertTrue(math.isfinite(state.oil_temperature_k))
        self.assertTrue(math.isfinite(state.cht_temperature_c))
        self.assertTrue(math.isfinite(state.oil_temperature_c))

    # === 15. Temperatures > 0 K ===
    def test_15_temperatures_above_zero_kelvin(self):
        """15. temperatures remain above 0 K"""
        state = ThermalModel.calculate(self.nominal_input)
        self.assertGreater(state.cht_temperature_k, 0.0)
        self.assertGreater(state.oil_temperature_k, 0.0)

    # === 16. No NaN ===
    def test_16_no_nan(self):
        """16. no NaN in outputs"""
        state = ThermalModel.calculate(self.nominal_input)
        for field in [state.cht_temperature_k, state.oil_temperature_k,
                      state.cht_heat_input_w, state.heat_cht_to_oil_w,
                      state.cht_cooling_w, state.oil_cooling_w,
                      state.dcht_dt_k_s, state.doil_dt_k_s]:
            self.assertFalse(math.isnan(field))

    # === 17. No inf ===
    def test_17_no_inf(self):
        """17. no inf in outputs"""
        state = ThermalModel.calculate(self.nominal_input)
        for field in [state.cht_temperature_k, state.oil_temperature_k,
                      state.cht_heat_input_w, state.heat_cht_to_oil_w,
                      state.cht_cooling_w, state.oil_cooling_w,
                      state.dcht_dt_k_s, state.doil_dt_k_s]:
            self.assertFalse(math.isinf(field))

    # === 18. Timestep validation ===
    def test_18_timestep_validation(self):
        """18. dt <= 0 produces no state change"""
        env = copy.deepcopy(self.nominal_input)
        env.timestep_s = 0.0
        state = ThermalModel.calculate(env)
        self.assertAlmostEqual(state.cht_temperature_k, env.cht_temperature_k)

        env2 = copy.deepcopy(self.nominal_input)
        env2.timestep_s = -1.0
        state2 = ThermalModel.calculate(env2)
        self.assertAlmostEqual(state2.cht_temperature_k, env2.cht_temperature_k)

    # === 19. Energy/heat-flow sign consistency ===
    def test_19_energy_sign_consistency(self):
        """19. heat flows have correct signs"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 400.0
        env.oil_temperature_k = 350.0
        state = ThermalModel.calculate(env)
        # Heat input is positive
        self.assertGreater(state.cht_heat_input_w, 0.0)
        # CHT > oil → positive heat flow CHT→oil
        self.assertGreater(state.heat_cht_to_oil_w, 0.0)
        # CHT > ambient → positive cooling
        self.assertGreater(state.cht_cooling_w, 0.0)
        # Oil > ambient → positive cooling
        self.assertGreater(state.oil_cooling_w, 0.0)

    # === 20. Convergence toward ambient when heat removed ===
    def test_20_convergence_toward_ambient(self):
        """20. thermal state converges toward ambient when heat input removed"""
        env = copy.deepcopy(self.nominal_input)
        env.heat_loss_power_w = 0.0
        env.cht_temperature_k = 400.0
        env.oil_temperature_k = 370.0
        env.timestep_s = 1.0

        t_cht = env.cht_temperature_k
        for _ in range(100):
            state = ThermalModel.calculate(env)
            env.cht_temperature_k = state.cht_temperature_k
            env.oil_temperature_k = state.oil_temperature_k

        # After 100 seconds of cooling, temperatures should be closer to ambient
        self.assertLess(state.cht_temperature_k, t_cht)
        self.assertGreater(state.cht_temperature_k, env.ambient_temperature_k - 1.0)

    # === 21. Thermal mass sensitivity ===
    def test_21_thermal_mass_sensitivity(self):
        """21. higher thermal mass reduces rate of temperature change"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 288.15
        env.oil_temperature_k = 288.15

        state_default = ThermalModel.calculate(env)

        # Temporarily modify C_CHT
        old_c = ThermalModel.C_CHT
        ThermalModel.C_CHT = old_c * 2.0
        state_heavy = ThermalModel.calculate(env)
        ThermalModel.C_CHT = old_c

        self.assertLess(abs(state_heavy.dcht_dt_k_s), abs(state_default.dcht_dt_k_s))

    # === 22. Thermal resistance sensitivity ===
    def test_22_thermal_resistance_sensitivity(self):
        """22. higher thermal resistance reduces CHT-to-oil heat flow"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 400.0
        env.oil_temperature_k = 350.0

        state_default = ThermalModel.calculate(env)

        old_r = ThermalModel.R_CHT_OIL
        ThermalModel.R_CHT_OIL = old_r * 2.0
        state_higher_r = ThermalModel.calculate(env)
        ThermalModel.R_CHT_OIL = old_r

        self.assertLess(state_higher_r.heat_cht_to_oil_w, state_default.heat_cht_to_oil_w)

    # === 23. Cooling conductance sensitivity ===
    def test_23_cooling_conductance_sensitivity(self):
        """23. higher base cooling conductance increases heat rejection"""
        env = copy.deepcopy(self.nominal_input)

        state_default = ThermalModel.calculate(env)

        old_g = ThermalModel.G_CHT_BASE
        ThermalModel.G_CHT_BASE = old_g * 2.0
        state_higher_g = ThermalModel.calculate(env)
        ThermalModel.G_CHT_BASE = old_g

        self.assertGreater(state_higher_g.cht_cooling_w, state_default.cht_cooling_w)

    # === 24. Initialization from ambient ===
    def test_24_initialization_from_ambient(self):
        """24. cold-start initialization from ambient temperature"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 288.15
        env.oil_temperature_k = 288.15
        env.heat_loss_power_w = 50000.0
        state = ThermalModel.calculate(env)
        # Both temperatures should increase from ambient
        self.assertGreater(state.cht_temperature_k, 288.15)

    # === 25. Hot environment (ISA+20) ===
    def test_25_hot_environment(self):
        """25. hot ambient produces higher steady-state temperatures"""
        env_std = copy.deepcopy(self.nominal_input)
        env_hot = copy.deepcopy(self.nominal_input)
        env_hot.ambient_temperature_k = 308.15  # ISA+20

        state_std = ThermalModel.calculate(env_std)
        state_hot = ThermalModel.calculate(env_hot)

        # Hotter ambient means less cooling → higher CHT
        self.assertGreater(state_hot.cht_temperature_k, state_std.cht_temperature_k)

    # === 26. High-altitude (reduced density → hotter) ===
    def test_26_high_altitude_environment(self):
        """26. high-altitude (low density) reduces cooling effectiveness"""
        env_sl = copy.deepcopy(self.nominal_input)
        env_sl.ambient_density_kg_m3 = 1.225

        env_alt = copy.deepcopy(self.nominal_input)
        env_alt.ambient_density_kg_m3 = 0.7  # ~15,000 ft
        env_alt.ambient_temperature_k = 258.0  # colder at altitude

        g_sl = ThermalModel._calculate_cooling_conductance(
            ThermalModel.G_CHT_BASE, 1.225, 40.0)
        g_alt = ThermalModel._calculate_cooling_conductance(
            ThermalModel.G_CHT_BASE, 0.7, 40.0)

        self.assertGreater(g_sl, g_alt)

    # === 27. High-power representative condition ===
    def test_27_high_power_representative_condition(self):
        """27. representative high-power condition produces reasonable CHT"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 288.15
        env.oil_temperature_k = 288.15
        env.heat_loss_power_w = 76900.0
        env.timestep_s = 1.0

        # Run for 600 seconds (10 minutes) to approach steady state
        for _ in range(600):
            state = ThermalModel.calculate(env)
            env.cht_temperature_k = state.cht_temperature_k
            env.oil_temperature_k = state.oil_temperature_k

        # CHT should be in a plausible range (80-140 °C)
        self.assertGreater(state.cht_temperature_c, 80.0)
        self.assertLess(state.cht_temperature_c, 140.0)

        # Oil should be in a plausible range (60-130 °C)
        self.assertGreater(state.oil_temperature_c, 60.0)
        self.assertLess(state.oil_temperature_c, 130.0)

    # === 28. Integration with 1D output ===
    def test_28_integration_with_1d_output(self):
        """28. 1G can consume 1D combustion heat_loss_power_w correctly"""
        from src.digital_twin.physics.combustion import CombustionModel, FuelCombustionInput

        cb_in = FuelCombustionInput(
            engine_rpm=5800.0,
            throttle_position=1.0,
            manifold_pressure_pa=110000.0,
            manifold_temperature_k=310.0,
            air_mass_flow_kg_s=0.10,
            ambient_pressure_pa=101325.0,
            fuel_pressure_delta_pa=25000.0
        )
        cb_out = CombustionModel.calculate(cb_in)

        env = ThermalInput(
            cht_temperature_k=380.0,
            oil_temperature_k=360.0,
            heat_loss_power_w=cb_out.heat_loss_power_w,
            ambient_temperature_k=288.15,
            ambient_density_kg_m3=1.225,
            airspeed_m_s=40.0,
            engine_rpm=5800.0,
            timestep_s=0.1
        )
        state = ThermalModel.calculate(env)

        # Verify we consumed the correct heat input
        expected_q_in = cb_out.heat_loss_power_w * ThermalModel.F_CHT
        self.assertAlmostEqual(state.cht_heat_input_w, expected_q_in, places=2)
        self.assertTrue(math.isfinite(state.cht_temperature_k))

    # === 29. Regression compatibility with 1A–1F ===
    def test_29_regression_compatibility(self):
        """29. 1G module does not break 1A–1F imports"""
        from src.digital_twin.physics.atmosphere import AtmosphereModel
        from src.digital_twin.physics.turbo_intake import TurboIntakeModel
        from src.digital_twin.physics.airflow import AirflowModel
        from src.digital_twin.physics.combustion import CombustionModel
        from src.digital_twin.physics.engine_dynamics import EngineDynamicsModel
        from src.digital_twin.physics.propeller import PropellerModel
        # Verify all classes still exist and are importable
        self.assertTrue(hasattr(AtmosphereModel, 'calculate'))
        self.assertTrue(hasattr(TurboIntakeModel, 'step'))
        self.assertTrue(hasattr(AirflowModel, 'calculate'))
        self.assertTrue(hasattr(CombustionModel, 'calculate'))
        self.assertTrue(hasattr(EngineDynamicsModel, 'calculate'))
        self.assertTrue(hasattr(PropellerModel, 'calculate'))

    # === 30. Full Phase 1 regression ===
    def test_30_invalid_temperature_raises_error(self):
        """30. invalid temperature (0 K) raises ValueError"""
        env = copy.deepcopy(self.nominal_input)
        env.cht_temperature_k = 0.0
        with self.assertRaises(ValueError):
            ThermalModel.calculate(env)


if __name__ == '__main__':
    unittest.main()
