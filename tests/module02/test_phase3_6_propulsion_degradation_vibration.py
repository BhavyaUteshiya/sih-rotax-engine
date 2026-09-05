"""
Phase 3.6 Propulsion Aerodynamics, Gearbox Reflection, Cumulative Degradation, and 1000 Hz Vibration Test Suite.
SIH26054 — Module 02 Engine Simulator.
"""

import math
import pytest
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.physics.propulsion_wear_vibration import PropulsionWearVibrationModel, PropulsionWearVibrationError
from src.module02.simulation.combustion_runner import CombustionRunner
from src.module02.simulation.engine_runner import EngineRunner
from src.module02.simulation.intake_runner import IntakeRunner
from src.module02.simulation.propulsion_runner import PropulsionRunner
from src.module02.simulation.thermal_runner import ThermalRunner
from src.module02.simulation.turbo_runner import TurboRunner


def test_propeller_rpm_follows_gearbox_ratio():
    """1. Propeller RPM follows gearbox speed ratio N_prop = N_engine * speed_ratio."""
    rpm_p, n_p, w_p, t_p, f_th, t_ref = PropulsionWearVibrationModel.compute_propeller_and_gearbox(
        engine_rpm=4200.0,
        air_density_kg_m3=1.225,
        speed_ratio=0.65,
        gearbox_efficiency=0.97
    )

    assert math.isclose(rpm_p, 4200.0 * 0.65, rel_tol=1e-5)
    assert math.isclose(n_p, (4200.0 * 0.65) / 60.0, rel_tol=1e-5)


def test_propeller_torque_increases_with_rpm():
    """2. Propeller torque increases quadratically with RPM."""
    _, _, _, t_low, _, _ = PropulsionWearVibrationModel.compute_propeller_and_gearbox(2000.0, 1.225)
    _, _, _, t_high, _, _ = PropulsionWearVibrationModel.compute_propeller_and_gearbox(4000.0, 1.225)

    assert t_high > t_low
    assert math.isclose(t_high / t_low, (4000.0 / 2000.0) ** 2, rel_tol=1e-3)


def test_propeller_torque_responds_to_air_density():
    """3. Propeller torque responds linearly to air density."""
    _, _, _, t_dense, _, _ = PropulsionWearVibrationModel.compute_propeller_and_gearbox(3000.0, 1.225)
    _, _, _, t_thin, _, _ = PropulsionWearVibrationModel.compute_propeller_and_gearbox(3000.0, 0.6125)

    assert t_dense > t_thin
    assert math.isclose(t_dense / t_thin, 2.0, rel_tol=1e-3)


def test_propeller_thrust_responds_to_rpm():
    """4. Propeller thrust responds quadratically to RPM."""
    _, _, _, _, f_low, _ = PropulsionWearVibrationModel.compute_propeller_and_gearbox(2000.0, 1.225)
    _, _, _, _, f_high, _ = PropulsionWearVibrationModel.compute_propeller_and_gearbox(4000.0, 1.225)

    assert f_high > f_low
    assert math.isclose(f_high / f_low, (4000.0 / 2000.0) ** 2, rel_tol=1e-3)


def test_propeller_thrust_responds_to_density():
    """5. Propeller thrust responds to air density."""
    _, _, _, _, f_sea, _ = PropulsionWearVibrationModel.compute_propeller_and_gearbox(3000.0, 1.225)
    _, _, _, _, f_alt, _ = PropulsionWearVibrationModel.compute_propeller_and_gearbox(3000.0, 0.60)

    assert f_sea > f_alt


def test_gearbox_efficiency_preserves_power():
    """6 & 7. Gearbox efficiency preserves power relationship: P_prop = eta_gb * P_engine_load."""
    rpm_p, n_p, w_p, t_p, f_th, t_ref_eng = PropulsionWearVibrationModel.compute_propeller_and_gearbox(
        engine_rpm=4200.0,
        air_density_kg_m3=1.225,
        speed_ratio=0.65,
        gearbox_efficiency=0.97
    )

    w_eng = 4200.0 * (math.pi / 30.0)
    p_prop = t_p * w_p
    p_eng_load = t_ref_eng * w_eng

    assert p_prop <= p_eng_load
    assert math.isclose(p_prop, p_eng_load * 0.97, rel_tol=1e-3)


def test_propeller_load_affects_engine():
    """8-10. Propeller load closes engine feedback loop."""
    clock = SimulationClock(dt_seconds=0.01)
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")

    eng_runner = EngineRunner(clock, engine_config=cfg)
    prop_runner = PropulsionRunner(clock, engine_config=cfg)

    # Step engine with zero load
    st_no_load = eng_runner.step_engine(1, throttle_percent=100.0, load_torque_n_m=0.0)
    rpm_no_load = st_no_load.engine_rpm

    # Step engine with active propeller load reflected
    _, prop_st, _, _ = prop_runner.step_propulsion(1, engine_rpm=3000.0, air_density_kg_m3=1.225, indicated_torque_n_m=200.0, fuel_mass_flow_kg_s=0.005)
    st_with_load = eng_runner.step_engine(2, throttle_percent=100.0, load_torque_n_m=prop_st.reflected_engine_load_n_m)
    rpm_with_load = st_with_load.engine_rpm

    assert rpm_with_load < rpm_no_load, "Propeller load must decelerate engine shaft."


def test_twin_engine_asymmetric_propulsion():
    """11. Twin engine independence under asymmetric throttle (Engine 1 = 100%, Engine 2 = 50%)."""
    runner = PropulsionRunner(SimulationClock(dt_seconds=0.01))

    eng1, prop1, _, _ = runner.step_propulsion(1, engine_rpm=4200.0, air_density_kg_m3=1.225, indicated_torque_n_m=280.0, fuel_mass_flow_kg_s=0.008)
    eng2, prop2, _, _ = runner.step_propulsion(2, engine_rpm=2500.0, air_density_kg_m3=1.225, indicated_torque_n_m=140.0, fuel_mass_flow_kg_s=0.003)

    assert prop1.propeller_rpm > prop2.propeller_rpm
    assert prop1.load_torque_n_m > prop2.load_torque_n_m
    assert prop1.thrust_n > prop2.thrust_n


def test_deterministic_propulsion_trajectory():
    """12. Determinism: 100% bit-for-bit identical propulsion trajectories given identical inputs."""
    runner1 = PropulsionRunner(SimulationClock(dt_seconds=0.01))
    runner2 = PropulsionRunner(SimulationClock(dt_seconds=0.01))

    traj1 = []
    traj2 = []

    for _ in range(50):
        _, prop1, deg1, vib1 = runner1.step_propulsion(1, 3500.0, 1.225, 220.0, 0.006)
        _, prop2, deg2, vib2 = runner2.step_propulsion(1, 3500.0, 1.225, 220.0, 0.006)

        traj1.append((prop1.thrust_n, deg1.bearing_wear, vib1.vibration_rms_m_s2))
        traj2.append((prop2.thrust_n, deg2.bearing_wear, vib2.vibration_rms_m_s2))

    assert traj1 == traj2


def test_wear_degradation_accumulation():
    """13-16 & 20. Degradation accumulates under sustained operation and remains bounded [0, 1]. Zero wear when stopped."""
    db, dr, dinj = PropulsionWearVibrationModel.step_degradation(
        current_bearing_wear=0.0, current_ring_wear=0.0, current_injector_wear=0.0,
        engine_rpm=0.0, indicated_torque_n_m=0.0, fuel_mass_flow_kg_s=0.0, cht_k=288.15, oil_temp_k=288.15, oil_viscosity_pa_s=0.08, dt_seconds=1.0
    )
    assert db == 0.0 and dr == 0.0 and dinj == 0.0, "Stopped engine must produce zero wear."

    db_50, dr_50, dinj_50 = PropulsionWearVibrationModel.step_degradation(
        current_bearing_wear=0.0, current_ring_wear=0.0, current_injector_wear=0.0,
        engine_rpm=4200.0, indicated_torque_n_m=300.0, fuel_mass_flow_kg_s=0.008, cht_k=380.0, oil_temp_k=373.15, oil_viscosity_pa_s=0.012, dt_seconds=500.0,
        bearing_wear_rate_per_sec=0.001, ring_wear_rate_per_sec=0.001, injector_wear_rate_per_sec=0.001
    )

    assert db_50 > 0.0 and dr_50 > 0.0 and dinj_50 > 0.0
    assert db_50 <= 1.0 and dr_50 <= 1.0 and dinj_50 <= 1.0


def test_bearing_wear_increases_friction():
    """17. Bearing wear increases mechanical friction torque."""
    runner = PropulsionRunner(SimulationClock(dt_seconds=0.01))

    eng_nom, _, _, _ = runner.step_propulsion(1, 3000.0, 1.225, 200.0, 0.005)
    fric_nom = eng_nom.friction_torque_n_m

    runner.state.degradation[1].bearing_wear = 0.50  # 50% bearing wear
    eng_worn, _, _, _ = runner.step_propulsion(1, 3000.0, 1.225, 200.0, 0.005)
    fric_worn = eng_worn.friction_torque_n_m

    assert fric_worn > fric_nom, "Bearing wear must increase mechanical friction torque."


def test_vibration_synthesis():
    """21-28. 1000 Hz Vibration acceleration synthesis, physical frequencies, and 1000-sample buffer."""
    inst_a, rms_a, dom_f, f_rot, f_fire, f_prop, time_buf = PropulsionWearVibrationModel.synthesize_vibration(
        engine_rpm=3000.0,
        indicated_torque_n_m=200.0,
        propeller_load_n_m=150.0,
        bearing_wear=0.10,
        dt_seconds=0.01,
        sample_rate_hz=1000.0
    )

    assert len(time_buf) == 1000, "Must synthesize 1000 samples for 1-second 1000 Hz buffer."
    assert rms_a > 0.0
    assert math.isclose(f_rot, 50.0, rel_tol=1e-3)    # 3000 RPM / 60 = 50 Hz
    assert math.isclose(f_fire, 100.0, rel_tol=1e-3)  # 2 * 50 Hz = 100 Hz
    assert math.isclose(f_prop, 97.5, rel_tol=1e-3)   # 3 blades * (3000 * 0.65 / 60) = 97.5 Hz


def test_vibration_rpm_changes_dominant_frequency():
    """23. Engine RPM changes vibration dominant frequency."""
    _, _, dom_low, f_rot_low, _, _, _ = PropulsionWearVibrationModel.synthesize_vibration(2000.0, 150.0, 100.0, 0.0, 0.01)
    _, _, dom_high, f_rot_high, _, _, _ = PropulsionWearVibrationModel.synthesize_vibration(4000.0, 150.0, 100.0, 0.0, 0.01)

    assert f_rot_high > f_rot_low
    assert dom_high > dom_low


def test_vibration_load_changes_amplitude():
    """24. Load increases vibration amplitude RMS."""
    _, rms_idle, _, _, _, _, _ = PropulsionWearVibrationModel.synthesize_vibration(3000.0, 20.0, 10.0, 0.0, 0.01)
    _, rms_loaded, _, _, _, _, _ = PropulsionWearVibrationModel.synthesize_vibration(3000.0, 300.0, 200.0, 0.0, 0.01)

    assert rms_loaded > rms_idle


def test_degradation_modifies_vibration():
    """25. Degradation modifies vibration RMS signature."""
    _, rms_clean, _, _, _, _, _ = PropulsionWearVibrationModel.synthesize_vibration(3000.0, 200.0, 150.0, bearing_wear=0.0, dt_seconds=0.01)
    _, rms_degraded, _, _, _, _, _ = PropulsionWearVibrationModel.synthesize_vibration(3000.0, 200.0, 150.0, bearing_wear=0.5, dt_seconds=0.01)

    assert rms_degraded > rms_clean


def test_numerical_safety_rejections_propulsion():
    """29. Numerical safety: Rejects negative speeds, non-positive densities, dt <= 0, NaN/Inf."""
    with pytest.raises(PropulsionWearVibrationError):
        PropulsionWearVibrationModel.validate_inputs(-100.0, 1.225, 0.65, 0.97, 0.01)

    with pytest.raises(PropulsionWearVibrationError):
        PropulsionWearVibrationModel.validate_inputs(3000.0, -1.0, 0.65, 0.97, 0.01)

    with pytest.raises(PropulsionWearVibrationError):
        PropulsionWearVibrationModel.validate_inputs(3000.0, 1.225, 0.65, 0.97, -0.01)
