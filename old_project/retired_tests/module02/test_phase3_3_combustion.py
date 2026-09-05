"""
Phase 3.3.1 Fuel Delivery, AFR, Combustion & Exhaust Energy Physics Test Suite (Hardened Architecture).
SIH26054 — Module 02 Engine Simulator.
"""

import math
import pytest
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.models.enums import EngineOperatingState
from src.module02.physics.combustion import CombustionModel, CombustionPhysicsError
from src.module02.simulation.combustion_runner import CombustionRunner
from src.module02.simulation.engine_runner import EngineRunner
from src.module02.simulation.intake_runner import IntakeRunner


def test_engine_off_state_zero_outputs():
    """1. OFF state: fuel flow = 0, combustion = 0, power = 0, torque = 0, exhaust energy = 0."""
    m_s, m_h, q_w = CombustionModel.compute_fuel_mass_flow(
        throttle_percent=0.0,
        air_mass_flow_kg_s=0.0,
        engine_rpm=0.0,
        idle_fuel_flow_kg_h=2.2,
        max_fuel_flow_kg_h=29.5,
        lower_heating_value_j_kg=43000000.0,
        operating_state=EngineOperatingState.OFF
    )

    assert m_s == 0.0
    assert m_h == 0.0
    assert q_w == 0.0

    p_ind, t_ind = CombustionModel.compute_indicated_power_and_torque(m_s, 43000000.0, 0.96, 0.44, omega_rad_per_sec=0.0)
    assert p_ind == 0.0
    assert t_ind == 0.0

    m_exh, t_exh, h_exh, e_exh = CombustionModel.compute_exhaust_flow_and_energy(0.0, m_s, q_w, 0.96, 288.15, 288.15)
    assert m_exh == 0.0
    assert t_exh == 288.15
    assert e_exh == 0.0


def test_starting_state_bounded_torque_and_fuel():
    """2. STARTING state: bounded fuel schedule and no torque singularity at low RPM."""
    m_s, m_h, q_w = CombustionModel.compute_fuel_mass_flow(
        throttle_percent=100.0,
        air_mass_flow_kg_s=0.05,
        engine_rpm=200.0,
        idle_fuel_flow_kg_h=2.2,
        max_fuel_flow_kg_h=29.5,
        lower_heating_value_j_kg=43000000.0,
        operating_state=EngineOperatingState.STARTING
    )

    # Starting fuel must be bounded (does not allow full rated 29.5 kg/h at 200 RPM)
    assert m_h < 5.0

    p_ind, t_ind = CombustionModel.compute_indicated_power_and_torque(m_s, 43000000.0, 0.96, 0.44, omega_rad_per_sec=20.94)
    # Torque must be physically bounded (no 10,000 N*m singularity)
    assert t_ind < 400.0


def test_idle_state_finite_outputs():
    """3. IDLE state: finite fuel flow, finite AFR and equivalence ratio."""
    m_s, m_h, q_w = CombustionModel.compute_fuel_mass_flow(
        throttle_percent=0.0,
        air_mass_flow_kg_s=0.06,
        engine_rpm=1400.0,
        idle_fuel_flow_kg_h=2.2,
        max_fuel_flow_kg_h=29.5,
        lower_heating_value_j_kg=43000000.0,
        operating_state=EngineOperatingState.IDLE
    )

    assert m_h == pytest.approx(2.2)

    afr, phi = CombustionModel.compute_air_fuel_ratio(0.06, m_s, stoichiometric_afr=14.5)
    assert afr is not None
    assert afr > 14.5 # Diesel idle is lean
    assert phi < 1.0


def test_running_state_throttle_response():
    """4. RUNNING state: Fuel delivery increases with throttle demand."""
    m_s_low, m_h_low, _ = CombustionModel.compute_fuel_mass_flow(20.0, 0.20, 2500.0, 2.2, 29.5, 43000000.0, EngineOperatingState.RUNNING)
    m_s_high, m_h_high, _ = CombustionModel.compute_fuel_mass_flow(80.0, 0.20, 2500.0, 2.2, 29.5, 43000000.0, EngineOperatingState.RUNNING)

    assert m_h_high > m_h_low


def test_air_availability_smoke_limiter():
    """5. Air availability: FADEC smoke limiter constrains fuel mass flow when intake air is low."""
    # At low air (0.02 kg/s), full 100% throttle demand (29.5 kg/h = 0.00819 kg/s) is constrained by smoke limit phi <= 1.05
    m_s_constrained, m_h_constrained, _ = CombustionModel.compute_fuel_mass_flow(
        throttle_percent=100.0,
        air_mass_flow_kg_s=0.02,
        engine_rpm=1500.0,
        idle_fuel_flow_kg_h=2.2,
        max_fuel_flow_kg_h=29.5,
        lower_heating_value_j_kg=43000000.0,
        operating_state=EngineOperatingState.RUNNING,
        stoichiometric_afr=14.5,
        smoke_limit_phi=1.05
    )

    expected_max_fuel_s = (0.02 * 1.05) / 14.5 # ~0.001448 kg/s
    assert m_s_constrained == pytest.approx(expected_max_fuel_s)


def test_zero_fuel_afr_representation():
    """6. Zero fuel: AFR returns None / zero phi (never fake 500.0)."""
    afr, phi = CombustionModel.compute_air_fuel_ratio(0.10, 0.0, 14.5)
    assert afr is None
    assert phi == 0.0


def test_injection_timing_deviation_effect():
    """7. Injection timing: Timing deviation reduces combustion efficiency and power."""
    eta_comb_opt, _, _ = CombustionModel.compute_combustion_efficiency(
        equivalence_ratio_phi=0.5,
        injection_timing_deg_btdc=18.0,
        optimal_injection_timing_deg_btdc=18.0,
        peak_combustion_efficiency=0.96
    )

    eta_comb_dev, _, _ = CombustionModel.compute_combustion_efficiency(
        equivalence_ratio_phi=0.5,
        injection_timing_deg_btdc=10.0,
        optimal_injection_timing_deg_btdc=18.0,
        peak_combustion_efficiency=0.96
    )

    assert eta_comb_dev < eta_comb_opt


def test_rated_power_and_torque_consistency():
    """8. Rated operating point consistency: 180 HP (134.2 kW) at 4200 RPM."""
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")

    runner = CombustionRunner(SimulationClock(dt_seconds=0.01), engine_config=cfg)
    eng = runner.step_combustion(1, throttle_percent=100.0, air_mass_flow_kg_s=0.22, engine_rpm=4200.0)

    # Indicated power at rated speed should be ~145 - 155 kW (delivering 134.2 kW net shaft power after friction)
    assert eng.combustion.indicated_power_w > 134226.0
    assert eng.combustion.indicated_torque_n_m > 305.0
    assert eng.combustion.indicated_torque_n_m < 400.0


def test_altitude_combustion_coupling():
    """9. Altitude coupling: Lower ambient pressure reduces air mass flow, changing AFR and combustion response."""
    runner_sea = CombustionRunner(SimulationClock(dt_seconds=0.01))
    runner_alt = CombustionRunner(SimulationClock(dt_seconds=0.01))

    eng_sea = runner_sea.step_combustion(1, throttle_percent=100.0, air_mass_flow_kg_s=0.20, engine_rpm=4200.0)
    eng_alt = runner_alt.step_combustion(1, throttle_percent=100.0, air_mass_flow_kg_s=0.12, engine_rpm=4200.0)

    assert eng_alt.combustion.air_fuel_ratio < eng_sea.combustion.air_fuel_ratio
    assert eng_alt.combustion.equivalence_ratio > eng_sea.combustion.equivalence_ratio


def test_twin_engine_independence():
    """10. Twin engine independence: Engine 1 and Engine 2 maintain completely independent fuel/combustion states."""
    runner = CombustionRunner(SimulationClock(dt_seconds=0.01))

    eng1 = runner.step_combustion(1, throttle_percent=100.0, air_mass_flow_kg_s=0.20, engine_rpm=4200.0)
    eng2 = runner.step_combustion(2, throttle_percent=0.0, air_mass_flow_kg_s=0.05, engine_rpm=1400.0)

    assert eng1.operating_state == EngineOperatingState.RUNNING
    assert eng2.operating_state == EngineOperatingState.IDLE
    assert eng1.fuel.fuel_mass_flow_kg_h > eng2.fuel.fuel_mass_flow_kg_h


def test_repeated_simulation_determinism():
    """11. Determinism: Identical inputs produce 100% identical combustion trajectories."""
    runner1 = CombustionRunner(SimulationClock(dt_seconds=0.01))
    runner2 = CombustionRunner(SimulationClock(dt_seconds=0.01))

    traj1 = []
    traj2 = []

    for _ in range(50):
        st1 = runner1.step_combustion(1, throttle_percent=80.0, air_mass_flow_kg_s=0.15, engine_rpm=3500.0)
        st2 = runner2.step_combustion(1, throttle_percent=80.0, air_mass_flow_kg_s=0.15, engine_rpm=3500.0)

        traj1.append((st1.combustion.indicated_power_w, st1.exhaust.exhaust_temp_k))
        traj2.append((st2.combustion.indicated_power_w, st2.exhaust.exhaust_temp_k))

    assert traj1 == traj2, "Phase 3.3.1 combustion trajectories must be 100% deterministic."


def test_configuration_flow():
    """12. Configuration flow: Changing YAML parameters alters fuel/combustion behavior without Python changes."""
    cfg_tapas = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    cfg_gasoline = ConfigLoader.load_engine_config("configs/module02/engines/generic_115hp_gasoline.yaml")

    runner_tapas = CombustionRunner(SimulationClock(dt_seconds=0.01), engine_config=cfg_tapas)
    runner_gasoline = CombustionRunner(SimulationClock(dt_seconds=0.01), engine_config=cfg_gasoline)

    eng_tapas = runner_tapas.step_combustion(1, throttle_percent=100.0, air_mass_flow_kg_s=0.20, engine_rpm=4200.0)
    eng_gasoline = runner_gasoline.step_combustion(1, throttle_percent=100.0, air_mass_flow_kg_s=0.20, engine_rpm=4200.0)

    assert eng_tapas.fuel.fuel_mass_flow_kg_h != eng_gasoline.fuel.fuel_mass_flow_kg_h
    assert eng_tapas.combustion.indicated_power_w != eng_gasoline.combustion.indicated_power_w


def test_energy_conservation():
    """13. Energy conservation check: Indicated combustion power P_ind never exceeds total fuel chemical power Q_fuel."""
    m_s, _, q_fuel_w = CombustionModel.compute_fuel_mass_flow(100.0, 0.20, 4200.0, 2.2, 29.5, 43000000.0)
    p_ind_w, _ = CombustionModel.compute_indicated_power_and_torque(m_s, 43000000.0, 0.96, 0.44, omega_rad_per_sec=440.0)

    assert p_ind_w < q_fuel_w, "Indicated power must be strictly less than chemical fuel energy rate."


def test_exhaust_mass_flow_and_energy():
    """14. Exhaust: Exhaust mass flow equals sum of air and fuel mass flows, exhaust energy is finite and non-negative."""
    m_air = 0.18
    m_fuel = 0.008
    q_fuel_w = m_fuel * 43000000.0

    m_exh, t_exh, h_exh, e_exh_w = CombustionModel.compute_exhaust_flow_and_energy(
        air_mass_flow_kg_s=m_air,
        fuel_mass_flow_kg_s=m_fuel,
        fuel_energy_rate_w=q_fuel_w,
        combustion_efficiency=0.95,
        intake_temp_k=300.0,
        ambient_temp_k=288.15
    )

    assert m_exh == pytest.approx(m_air + m_fuel)
    assert t_exh > 300.0
    assert h_exh > 0.0
    assert e_exh_w > 0.0
