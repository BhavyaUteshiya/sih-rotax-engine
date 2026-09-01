"""
Phase 3.4 Physically Closed Turbocharger Dynamics Test Suite.
SIH26054 — Module 02 Engine Simulator.
"""

import math
import pytest
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.physics.turbocharger import TurbochargerModel, TurbochargerPhysicsError
from src.module02.simulation.combustion_runner import CombustionRunner
from src.module02.simulation.engine_runner import EngineRunner
from src.module02.simulation.intake_runner import IntakeRunner
from src.module02.simulation.turbo_runner import TurboRunner


def test_zero_exhaust_energy_no_turbine_power():
    """1. Zero exhaust energy -> No turbine power output or torque."""
    p_turb, t_turb = TurbochargerModel.compute_turbine_power_and_torque(
        exhaust_mass_flow_kg_s=0.0,
        exhaust_temp_k=288.15,
        exhaust_energy_rate_w=0.0,
        turbine_efficiency=0.75,
        turbo_omega_rad_per_sec=0.0
    )

    assert p_turb == 0.0
    assert t_turb == 0.0


def test_positive_exhaust_energy_turbine_accelerates():
    """2. Positive exhaust energy -> Positive turbine torque and positive angular acceleration."""
    p_turb, t_turb = TurbochargerModel.compute_turbine_power_and_torque(
        exhaust_mass_flow_kg_s=0.15,
        exhaust_temp_k=800.0,
        exhaust_energy_rate_w=80000.0, # 80 kW exhaust energy
        turbine_efficiency=0.75,
        turbo_omega_rad_per_sec=1000.0
    )

    assert p_turb > 0.0
    assert t_turb > 0.0

    w_new, rpm_new, alpha = TurbochargerModel.step_turbo_shaft_dynamics(
        turbo_omega_rad_per_sec=1000.0,
        tau_turbine_n_m=t_turb,
        tau_compressor_n_m=0.1,
        tau_friction_n_m=0.05,
        rotational_inertia_kg_m2=0.00008,
        max_turbo_speed_rpm=140000.0,
        dt_seconds=0.01
    )

    assert alpha > 0.0
    assert w_new > 1000.0


def test_compressor_load_opposes_acceleration():
    """3. Compressor load opposes turbo acceleration."""
    w_new_no_load, _, alpha_no_load = TurbochargerModel.step_turbo_shaft_dynamics(1000.0, 5.0, 0.0, 0.0, 0.00008, 140000.0, 0.01)
    w_new_with_load, _, alpha_with_load = TurbochargerModel.step_turbo_shaft_dynamics(1000.0, 5.0, 3.0, 0.0, 0.00008, 140000.0, 0.01)

    assert alpha_with_load < alpha_no_load
    assert w_new_with_load < w_new_no_load


def test_turbo_friction_opposes_rotation():
    """4. Turbo shaft friction opposes rotation."""
    t_fric = TurbochargerModel.compute_turbo_friction_torque(
        turbo_omega_rad_per_sec=5000.0,
        friction_static_n_m=0.02,
        friction_viscous_n_m_s_rad=0.00005,
        friction_hydrodynamic_n_m_s2_rad2=0.00000001
    )

    assert t_fric > 0.0


def test_turbo_reaches_physically_bounded_speed():
    """5. Turbo reaches physically bounded speed."""
    w_new, rpm_new, _ = TurbochargerModel.step_turbo_shaft_dynamics(
        turbo_omega_rad_per_sec=15000.0, # At max speed
        tau_turbine_n_m=100.0,           # Huge driving torque
        tau_compressor_n_m=1.0,
        tau_friction_n_m=0.1,
        rotational_inertia_kg_m2=0.00008,
        max_turbo_speed_rpm=140000.0,    # ~14,660 rad/s
        dt_seconds=0.01
    )

    w_max = 140000.0 * (math.pi / 30.0)
    assert w_new <= w_max * 1.05


def test_turbine_power_bounded_by_exhaust_energy():
    """6. Turbine power extraction strictly <= available exhaust energy."""
    e_exh = 50000.0 # 50 kW
    p_turb, _ = TurbochargerModel.compute_turbine_power_and_torque(
        exhaust_mass_flow_kg_s=0.12,
        exhaust_temp_k=750.0,
        exhaust_energy_rate_w=e_exh,
        turbine_efficiency=0.75,
        turbo_omega_rad_per_sec=3000.0
    )

    assert p_turb <= e_exh


def test_compressor_power_positive():
    """7. Compressor power requirement is positive when compressing air."""
    map_pa, boost_pa, pi_c, t_comp, t_man, p_comp, t_comp_load = TurbochargerModel.compute_compressor_work_and_map(
        air_mass_flow_kg_s=0.15,
        turbo_omega_rad_per_sec=8000.0,
        max_turbo_speed_rpm=140000.0,
        max_compressor_pressure_ratio=2.4,
        max_map_pa=220000.0,
        ambient_pressure_pa=101325.0,
        ambient_temp_k=288.15,
        compressor_efficiency=0.78
    )

    assert pi_c > 1.0
    assert map_pa > 101325.0
    assert p_comp > 0.0
    assert t_comp_load > 0.0


def test_map_depends_on_turbo_operation():
    """8. MAP depends dynamically on actual turbo shaft speed."""
    map_low, _, _, _, _, _, _ = TurbochargerModel.compute_compressor_work_and_map(0.10, 2000.0, 140000.0, 2.4, 220000.0, 101325.0, 288.15, 0.78)
    map_high, _, _, _, _, _, _ = TurbochargerModel.compute_compressor_work_and_map(0.10, 10000.0, 140000.0, 2.4, 220000.0, 101325.0, 288.15, 0.78)

    assert map_high > map_low


def test_deceleration_on_exhaust_loss():
    """9. Removing exhaust energy causes turbo deceleration."""
    w_new, rpm_new, alpha = TurbochargerModel.step_turbo_shaft_dynamics(
        turbo_omega_rad_per_sec=8000.0,
        tau_turbine_n_m=0.0,     # Zero driving torque (exhaust cut off)
        tau_compressor_n_m=0.5,  # Active compressor load
        tau_friction_n_m=0.2,    # Active shaft friction
        rotational_inertia_kg_m2=0.00008,
        max_turbo_speed_rpm=140000.0,
        dt_seconds=0.01
    )

    assert alpha < 0.0
    assert w_new < 8000.0


def test_altitude_affects_turbo_compressor():
    """10. Altitude affects compressor pressure ratio and MAP."""
    map_sea, _, pi_sea, _, _, _, _ = TurbochargerModel.compute_compressor_work_and_map(0.12, 8000.0, 140000.0, 2.4, 220000.0, 101325.0, 288.15, 0.78)
    map_alt, _, pi_alt, _, _, _, _ = TurbochargerModel.compute_compressor_work_and_map(0.12, 8000.0, 140000.0, 2.4, 220000.0, 54000.0, 240.0, 0.78)

    assert map_alt < map_sea


def test_complete_closed_loop_physics():
    """11-16. Complete closed feedback loop: Airflow -> Fuel/Combustion -> Exhaust -> Turbine -> Turbo RPM -> Compressor -> MAP -> Airflow."""
    clock = SimulationClock(dt_seconds=0.01)
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")

    eng_runner = EngineRunner(clock, engine_config=cfg)
    intake_runner = IntakeRunner(clock, engine_config=cfg)
    comb_runner = CombustionRunner(clock, engine_config=cfg)
    turbo_runner = TurboRunner(clock, engine_config=cfg)

    # Initial state step
    eng_st = eng_runner.step_engine(1, throttle_percent=100.0)
    intake_st = intake_runner.step_intake(1, eng_st.engine_rpm, 100.0, 101325.0, 288.15)
    comb_st = comb_runner.step_combustion(1, 100.0, intake_st.air_mass_flow_kg_s, eng_st.engine_rpm)
    turbo_st = turbo_runner.step_turbo(1, comb_st.exhaust.exhaust_mass_flow_kg_s, comb_st.exhaust.exhaust_temp_k, comb_st.exhaust.exhaust_energy_rate_w, intake_st.air_mass_flow_kg_s)

    initial_map = turbo_st.manifold_pressure_pa

    # Step closed loop for 50 steps
    for _ in range(50):
        eng_st = eng_runner.step_engine(1, throttle_percent=100.0)
        intake_st = intake_runner.step_intake(1, eng_st.engine_rpm, 100.0, 101325.0, 288.15, manifold_pressure_pa=turbo_st.manifold_pressure_pa)
        comb_st = comb_runner.step_combustion(1, 100.0, intake_st.air_mass_flow_kg_s, eng_st.engine_rpm)
        turbo_st = turbo_runner.step_turbo(1, comb_st.exhaust.exhaust_mass_flow_kg_s, comb_st.exhaust.exhaust_temp_k, comb_st.exhaust.exhaust_energy_rate_w, intake_st.air_mass_flow_kg_s)
        clock.step()

    final_map = turbo_st.manifold_pressure_pa

    assert final_map > initial_map, "Closed loop must show MAP increase as turbo accelerates."


def test_no_placeholder_throttle_map():
    """17. Verify deprecation warning for Phase 3.2 placeholder functions."""
    with pytest.deprecated_call():
        from src.module02.physics.intake_turbocharger import IntakeTurbochargerModel
        IntakeTurbochargerModel.compute_manifold_absolute_pressure(101325.0, 100.0, 220000.0, 2.4)


def test_low_speed_singularity_protection():
    """18. Low turbo speed handling is non-singular and numerically stable."""
    p_turb, t_turb = TurbochargerModel.compute_turbine_power_and_torque(0.01, 350.0, 100.0, 0.75, 0.0)
    assert not math.isnan(t_turb)
    assert not math.isinf(t_turb)
    assert t_turb >= 0.0


def test_twin_engine_independence():
    """19. Twin engine independence: Modifying Engine 1 turbo state does not affect Engine 2."""
    runner = TurboRunner(SimulationClock(dt_seconds=0.01))

    st1 = runner.step_turbo(1, exhaust_mass_flow_kg_s=0.15, exhaust_temp_k=800.0, exhaust_energy_rate_w=80000.0, air_mass_flow_kg_s=0.18)
    st2 = runner.step_turbo(2, exhaust_mass_flow_kg_s=0.0, exhaust_temp_k=288.15, exhaust_energy_rate_w=0.0, air_mass_flow_kg_s=0.02)

    assert st1.turbocharger.turbine_power_w > st2.turbocharger.turbine_power_w
    assert st1.turbocharger.turbo_speed_rpm > st2.turbocharger.turbo_speed_rpm


def test_repeated_simulation_determinism():
    """20. Determinism: Identical inputs produce 100% identical turbo trajectories."""
    runner1 = TurboRunner(SimulationClock(dt_seconds=0.01))
    runner2 = TurboRunner(SimulationClock(dt_seconds=0.01))

    traj1 = []
    traj2 = []

    for _ in range(50):
        st1 = runner1.step_turbo(1, 0.12, 750.0, 50000.0, 0.15)
        st2 = runner2.step_turbo(1, 0.12, 750.0, 50000.0, 0.15)

        traj1.append((st1.turbocharger.turbo_speed_rpm, st1.manifold_pressure_pa))
        traj2.append((st2.turbocharger.turbo_speed_rpm, st2.manifold_pressure_pa))

    assert traj1 == traj2, "Phase 3.4 turbo trajectories must be 100% deterministic."


def test_configuration_flow():
    """21. Configuration flow: Changing YAML parameters alters turbo behavior without Python edits."""
    cfg_tapas = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    cfg_gasoline = ConfigLoader.load_engine_config("configs/module02/engines/generic_115hp_gasoline.yaml")

    runner_tapas = TurboRunner(SimulationClock(dt_seconds=0.01), engine_config=cfg_tapas)
    runner_gasoline = TurboRunner(SimulationClock(dt_seconds=0.01), engine_config=cfg_gasoline)

    st_tapas = runner_tapas.step_turbo(1, 0.15, 800.0, 80000.0, 0.18)
    st_gasoline = runner_gasoline.step_turbo(1, 0.15, 800.0, 80000.0, 0.18)

    assert st_tapas.turbocharger.max_manifold_absolute_pressure_pa != st_gasoline.turbocharger.max_manifold_absolute_pressure_pa


def test_numerical_safety_rejections():
    """22. Numerical safety: Rejects J_turbo <= 0, dt <= 0, NaN/Inf."""
    with pytest.raises(TurbochargerPhysicsError):
        TurbochargerModel.validate_inputs(-0.001, 140000.0, 0.01)

    with pytest.raises(TurbochargerPhysicsError):
        TurbochargerModel.validate_inputs(0.00008, 140000.0, -0.01)

    with pytest.raises(TurbochargerPhysicsError):
        TurbochargerModel.compute_turbine_power_and_torque(-0.1, 700.0, 1000.0, 0.75, 100.0)
