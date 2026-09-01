"""
Phase 3.2 Intake Manifold & Turbocharger Compressor Physics Test Suite.
SIH26054 — Module 02 Engine Simulator.
Separates Physical Models from Temporary Parametric Turbo Representations.
"""

import math
import pytest
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.physics.atmosphere import AtmosphereModel
from src.module02.physics.intake_turbocharger import IntakeTurbochargerModel, IntakeTurbochargerError
from src.module02.simulation.intake_runner import IntakeRunner


# ==============================================================================
# SECTION 1: PHYSICAL MODEL TESTS
# ==============================================================================

def test_sea_level_intake_physical_model():
    """PHYSICAL MODEL TEST: Verify gauge boost calculation, intake density, and 4-stroke air mass flow."""
    p_amb = 101325.0
    p_map = 180000.0
    t_amb = 288.15
    eta_c = 0.78
    v_d = 0.0020
    rpm = 4200.0
    rated_rpm = 4200.0

    # 1. Gauge Boost Pressure (P_boost_gauge = P_MAP - P_amb)
    p_gauge = IntakeTurbochargerModel.compute_gauge_boost_pressure(p_map, p_amb)
    assert p_gauge == pytest.approx(p_map - p_amb)

    # 2. Isentropic Compressor Temperature Rise
    pi_c = p_map / p_amb
    t_comp_out = IntakeTurbochargerModel.compute_compressor_outlet_temperature(t_amb, pi_c, compressor_efficiency=eta_c)
    assert t_comp_out > t_amb

    # 3. Ideal Gas Law Intake Air Density
    rho_in = IntakeTurbochargerModel.compute_intake_air_density(p_map, t_comp_out)
    expected_rho = p_map / (287.058 * t_comp_out)
    assert rho_in == pytest.approx(expected_rho)

    # 4. 4-Stroke Cycle Air Mass Flow Rate
    eta_v = IntakeTurbochargerModel.compute_volumetric_efficiency(rpm, p_map, rated_rpm=rated_rpm)
    m_dot_s, m_dot_h = IntakeTurbochargerModel.compute_engine_air_mass_flow(rpm, rho_in, v_d, eta_v)

    expected_m_dot_s = eta_v * rho_in * v_d * (rpm / 120.0)
    assert m_dot_s == pytest.approx(expected_m_dot_s)
    assert m_dot_h == pytest.approx(m_dot_s * 3600.0)


def test_compressor_outlet_temperature_isentropic_model():
    """PHYSICAL MODEL TEST: Verify compressor efficiency reduces compressor discharge temperature for same pressure ratio."""
    t_amb = 288.15
    pi_c = 1.8

    t_out_low_eff = IntakeTurbochargerModel.compute_compressor_outlet_temperature(t_amb, pi_c, compressor_efficiency=0.65)
    t_out_high_eff = IntakeTurbochargerModel.compute_compressor_outlet_temperature(t_amb, pi_c, compressor_efficiency=0.85)

    assert t_out_high_eff < t_out_low_eff, "Higher compressor efficiency must result in lower outlet temperature."


def test_engine_air_mass_flow_4stroke_rpm_coupling():
    """PHYSICAL MODEL TEST: Verify air mass flow rate responds causally to engine RPM (zero at 0 RPM, increasing at high RPM)."""
    rho_in = 1.4
    v_d = 0.0020
    eta_v = 0.85

    # Zero RPM => Zero Airflow
    m_dot_zero_s, _ = IntakeTurbochargerModel.compute_engine_air_mass_flow(0.0, rho_in, v_d, eta_v)
    assert m_dot_zero_s == 0.0

    # Low RPM (1000 RPM)
    m_dot_low_s, _ = IntakeTurbochargerModel.compute_engine_air_mass_flow(1000.0, rho_in, v_d, eta_v)

    # High RPM (4000 RPM)
    m_dot_high_s, _ = IntakeTurbochargerModel.compute_engine_air_mass_flow(4000.0, rho_in, v_d, eta_v)

    assert m_dot_high_s > m_dot_low_s, "Air mass flow must increase with engine RPM."


def test_altitude_ambient_coupling_effect():
    """PHYSICAL MODEL TEST: Verify higher altitude produces lower ambient pressure."""
    p_amb_sea = AtmosphereModel.compute_ambient_pressure(0.0)
    p_amb_alt = AtmosphereModel.compute_ambient_pressure(3000.0)

    assert p_amb_alt < p_amb_sea


def test_numerical_safety_rejections():
    """PHYSICAL MODEL TEST: Verify rejection of NaN, Inf, non-positive pressure, non-positive temperature, and invalid efficiency."""
    with pytest.raises(IntakeTurbochargerError):
        IntakeTurbochargerModel.validate_inputs(-101325.0, 288.15, 2000.0, 0.0020)

    with pytest.raises(IntakeTurbochargerError):
        IntakeTurbochargerModel.validate_inputs(101325.0, -100.0, 2000.0, 0.0020)

    with pytest.raises(IntakeTurbochargerError):
        IntakeTurbochargerModel.validate_inputs(101325.0, 288.15, float("nan"), 0.0020)

    with pytest.raises(IntakeTurbochargerError):
        IntakeTurbochargerModel.compute_compressor_outlet_temperature(288.15, 1.5, compressor_efficiency=-0.5)

    with pytest.raises(IntakeTurbochargerError):
        IntakeTurbochargerModel.compute_intake_air_density(-50000.0, 300.0)


def test_twin_engine_intake_independence():
    """PHYSICAL MODEL TEST: Verify Engine 1 and Engine 2 maintain completely independent intake states."""
    runner = IntakeRunner(SimulationClock(dt_seconds=0.01))

    # Engine 1 at full throttle 4200 RPM, Engine 2 at idle 0% throttle 1400 RPM
    eng1 = runner.step_intake(1, 4200.0, 100.0, 101325.0, 288.15)
    eng2 = runner.step_intake(2, 1400.0, 0.0, 101325.0, 288.15)

    assert eng1.manifold_pressure_pa > eng2.manifold_pressure_pa
    assert eng1.air_mass_flow_kg_s > eng2.air_mass_flow_kg_s
    assert eng1.turbocharger.turbo_speed_rpm > eng2.turbocharger.turbo_speed_rpm


def test_repeated_simulation_determinism():
    """PHYSICAL MODEL TEST: Verify identical inputs produce 100% identical intake trajectories."""
    runner1 = IntakeRunner(SimulationClock(dt_seconds=0.01))
    runner2 = IntakeRunner(SimulationClock(dt_seconds=0.01))

    traj1 = []
    traj2 = []

    for _ in range(50):
        st1 = runner1.step_intake(1, 3000.0, 75.0, 90000.0, 280.0)
        st2 = runner2.step_intake(1, 3000.0, 75.0, 90000.0, 280.0)

        traj1.append((st1.manifold_pressure_pa, st1.air_mass_flow_kg_s))
        traj2.append((st2.manifold_pressure_pa, st2.air_mass_flow_kg_s))

    assert traj1 == traj2, "Phase 3.2 intake trajectories must be 100% deterministic."


# ==============================================================================
# SECTION 2: TEMPORARY PARAMETRIC TURBOCHARGER REPRESENTATION TESTS
# ==============================================================================

def test_temporary_parametric_boost_interface():
    """TEMPORARY PARAMETRIC TEST: Verify parametric throttle-to-MAP boost modulation interface."""
    p_amb = 101325.0
    max_map = 220000.0
    pi_max = 2.4

    # At 0% throttle => MAP = ambient pressure
    p_map_idle, pi_c_idle = IntakeTurbochargerModel.compute_manifold_absolute_pressure(p_amb, 0.0, max_map, pi_max)
    assert p_map_idle == p_amb
    assert pi_c_idle == 1.0

    # At 100% throttle => MAP = peak boost MAP
    p_map_full, pi_c_full = IntakeTurbochargerModel.compute_manifold_absolute_pressure(p_amb, 100.0, max_map, pi_max)
    assert p_map_full == max_map
    assert pi_c_full == pytest.approx(max_map / p_amb)


def test_configuration_parameters_reach_intake_runner():
    """TEMPORARY PARAMETRIC TEST: Verify configuration values stream strictly from YAML without Python defaults."""
    cfg_tapas = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    runner = IntakeRunner(SimulationClock(dt_seconds=0.01), engine_config=cfg_tapas)

    eng1 = runner.step_intake(
        engine_index=1,
        engine_rpm=4200.0,
        throttle_percent=100.0,
        ambient_pressure_pa=101325.0,
        ambient_temp_k=288.15
    )

    assert eng1.manifold_pressure_pa == 220000.0
    assert eng1.air_mass_flow_kg_s > 0.0
    assert eng1.turbocharger.compressor_efficiency == 0.78
    assert eng1.turbocharger.max_manifold_absolute_pressure_pa == 220000.0
