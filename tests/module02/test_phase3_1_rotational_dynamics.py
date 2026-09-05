"""
Phase 3.1 Engine Rotational Dynamics Physics Test Suite (Hardened Provenance & Friction Direction).
SIH26054 — Module 02 Engine Simulator.
"""

import math
import pytest
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.physics.rotational_dynamics import RotationalDynamicsModel, RotationalDynamicsError
from src.module02.simulation.engine_runner import EngineRunner


def test_rpm_unit_conversion():
    """Verify RPM <-> rad/s conversions."""
    omega_3000 = RotationalDynamicsModel.rpm_to_rad_per_sec(3000.0)
    expected_omega = 3000.0 * (math.pi / 30.0) # ~314.159 rad/s
    assert omega_3000 == pytest.approx(expected_omega)

    rpm_back = RotationalDynamicsModel.rad_per_sec_to_rpm(omega_3000)
    assert rpm_back == pytest.approx(3000.0)


def test_throttle_bounds_and_torque_demand():
    """Verify throttle demand bounds [0%, 100%] and proportional indicated torque demand."""
    max_t = 320.0

    # Zero throttle
    t_zero = RotationalDynamicsModel.compute_torque_demand_interface(0.0, max_torque_n_m=max_t)
    assert t_zero == 0.0

    # 50% throttle
    t_half = RotationalDynamicsModel.compute_torque_demand_interface(50.0, max_torque_n_m=max_t)
    assert t_half == 160.0

    # 100% throttle
    t_full = RotationalDynamicsModel.compute_torque_demand_interface(100.0, max_torque_n_m=max_t)
    assert t_full == 320.0

    # Rejection of out of bounds throttle
    with pytest.raises(RotationalDynamicsError):
        RotationalDynamicsModel.compute_torque_demand_interface(-10.0, max_torque_n_m=max_t)

    with pytest.raises(RotationalDynamicsError):
        RotationalDynamicsModel.compute_torque_demand_interface(110.0, max_torque_n_m=max_t)


def test_friction_direction_and_zero_omega():
    """Verify friction opposes positive rotation (omega > 0), negative rotation (omega < 0), and is zero at rest (omega = 0)."""
    # omega = 0 => friction = 0
    t_fric_zero = RotationalDynamicsModel.compute_friction_torque(0.0, 15.0, 0.05, 0.0001)
    assert t_fric_zero == 0.0

    # omega > 0 => positive friction torque opposing positive rotation
    t_fric_pos = RotationalDynamicsModel.compute_friction_torque(100.0, 15.0, 0.05, 0.0001)
    assert t_fric_pos > 0.0

    # omega < 0 => negative friction torque opposing negative rotation
    t_fric_neg = RotationalDynamicsModel.compute_friction_torque(-100.0, 15.0, 0.05, 0.0001)
    assert t_fric_neg < 0.0
    assert abs(t_fric_neg) == pytest.approx(t_fric_pos)


def test_rotational_torque_balance_and_acceleration():
    """Verify Newton's rotational law J * alpha = T_ind - T_load - T_fric."""
    t_ind = 200.0
    t_load = 50.0
    t_fric = 25.0
    j_eng = 0.55

    t_net, alpha = RotationalDynamicsModel.compute_rotational_acceleration(
        t_indicated_n_m=t_ind,
        t_load_n_m=t_load,
        t_friction_n_m=t_fric,
        inertia_kg_m2=j_eng
    )

    expected_t_net = 200.0 - 50.0 - 25.0 # 125.0 N*m
    expected_alpha = 125.0 / 0.55       # ~227.27 rad/s^2

    assert t_net == pytest.approx(expected_t_net)
    assert alpha == pytest.approx(expected_alpha)


def test_configuration_flow_multi_engine_yaml():
    """Verify loading different engine YAML files alters dynamics causally through ConfigLoader."""
    cfg_tapas = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    cfg_gasoline = ConfigLoader.load_engine_config("configs/module02/engines/generic_115hp_gasoline.yaml")

    runner_tapas = EngineRunner(SimulationClock(dt_seconds=0.01), engine_config=cfg_tapas)
    runner_gasoline = EngineRunner(SimulationClock(dt_seconds=0.01), engine_config=cfg_gasoline)

    eng_tapas = runner_tapas.step_engine(engine_index=1, throttle_percent=100.0)
    eng_gasoline = runner_gasoline.step_engine(engine_index=1, throttle_percent=100.0)

    # Different engine configs must yield different RPM accelerations
    assert eng_tapas.engine_rpm != eng_gasoline.engine_rpm
    assert eng_tapas.indicated_torque_total_n_m == 320.0
    assert eng_gasoline.indicated_torque_total_n_m == 240.0


def test_torque_provenance_and_180hp_calculation():
    """Verify 180 HP at 4200 RPM yields ~305.2 N*m brake torque and max_indicated_torque is classified ESTIMATED."""
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")

    power_w = cfg["power_and_performance"]["takeoff_rated_power_w"]["value"] # 134226 W
    rpm = cfg["power_and_performance"]["rated_rpm"]["value"]                 # 4200 RPM

    omega = rpm * (math.pi / 30.0) # ~439.82 rad/s
    t_brake = power_w / omega

    assert t_brake == pytest.approx(305.18, abs=0.1)

    max_t_entry = cfg["power_and_performance"]["max_indicated_torque_n_m"]
    assert max_t_entry["classification"] == "ESTIMATED"
    assert max_t_entry["calibration_required"] is True


def test_numerical_safety_rejections():
    """Verify rejection of NaN, Inf, negative inertia, negative max torque, negative friction, non-positive dt."""
    # NaN / Inf
    with pytest.raises(RotationalDynamicsError):
        RotationalDynamicsModel.rpm_to_rad_per_sec(float("nan"))

    with pytest.raises(RotationalDynamicsError):
        RotationalDynamicsModel.rad_per_sec_to_rpm(float("inf"))

    # Negative inertia
    with pytest.raises(RotationalDynamicsError):
        RotationalDynamicsModel.compute_rotational_acceleration(100.0, 0.0, 0.0, inertia_kg_m2=-0.5)

    # Negative max torque
    with pytest.raises(RotationalDynamicsError):
        RotationalDynamicsModel.compute_torque_demand_interface(50.0, max_torque_n_m=-100.0)

    # Negative friction coefficients
    with pytest.raises(RotationalDynamicsError):
        RotationalDynamicsModel.compute_friction_torque(100.0, -15.0, 0.05, 0.0001)

    # Non-positive dt
    with pytest.raises(RotationalDynamicsError):
        RotationalDynamicsModel.integrate_angular_velocity(100.0, 10.0, dt_seconds=0.0)


def test_twin_engine_independence():
    """Verify Engine 1 and Engine 2 maintain completely independent rotational states."""
    runner = EngineRunner(SimulationClock(dt_seconds=0.01))

    # Throttle Engine 1 to 100%, Engine 2 stays at 0%
    runner.step_engine(engine_index=1, throttle_percent=100.0)
    runner.step_engine(engine_index=2, throttle_percent=0.0)

    eng1 = runner.state.engines[1]
    eng2 = runner.state.engines[2]

    assert eng1.throttle_percent == 100.0
    assert eng1.engine_rpm > 0.0

    assert eng2.throttle_percent == 0.0
    assert eng2.engine_rpm == 0.0, "Engine 2 must remain unaffected by Engine 1 modifications."


def test_repeated_simulation_determinism():
    """Verify identical throttle inputs produce 100% identical twin-engine trajectories."""
    runner1 = EngineRunner(SimulationClock(dt_seconds=0.01))
    runner2 = EngineRunner(SimulationClock(dt_seconds=0.01))

    traj1 = []
    traj2 = []

    for _ in range(50):
        st1 = runner1.step_all_engines(throttles={1: 80.0, 2: 40.0})
        st2 = runner2.step_all_engines(throttles={1: 80.0, 2: 40.0})

        traj1.append((st1[1].engine_rpm, st1[2].engine_rpm))
        traj2.append((st2[1].engine_rpm, st2[2].engine_rpm))

    assert traj1 == traj2, "Phase 3.1 twin-engine trajectories must be 100% deterministic."
