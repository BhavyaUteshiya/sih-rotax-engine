"""
Module 02 Twin Engine Dynamics Simulation Runner (Phase 3.7 Alternator & Starter Shaft Coupling Update).
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Any, Dict, Optional
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.models.states import EngineState, SimulationState
from src.module02.physics.rotational_dynamics import RotationalDynamicsModel


class EngineRunner:
    """
    Integration Runner for Phase 3.1 & Phase 3.7 Engine Rotational Dynamics & Twin Engine State Progression.
    Conveys configuration values strictly from ConfigLoader without hardcoded Python defaults.
    Accepts indicated combustion torque, reflected propeller load, alternator shaft load, and starter torque into crankshaft integration.
    """

    def __init__(self, clock: Optional[SimulationClock] = None, engine_config: Optional[Dict[str, Any]] = None) -> None:
        self.clock = clock if clock is not None else SimulationClock()
        self.state = SimulationState()
        self.engine_config = engine_config if engine_config is not None else ConfigLoader.load_engine_config()
        self._initialize_twin_engines()

    def _initialize_twin_engines(self) -> None:
        """Initializes independent EngineState instances for Engine 1 and Engine 2."""
        self.state.engines[1] = EngineState(engine_index=1, engine_id="engine_left")
        self.state.engines[2] = EngineState(engine_index=2, engine_id="engine_right")

    def step_engine(
        self,
        engine_index: int,
        throttle_percent: float,
        load_torque_n_m: float = 0.0,
        indicated_torque_n_m: Optional[float] = None,
        alternator_torque_n_m: float = 0.0,
        starter_torque_n_m: float = 0.0,
        engine_config: Optional[Dict[str, Any]] = None
    ) -> EngineState:
        """
        Executes one deterministic rotational physics integration step for a specific engine instance.
        Reads engine physical parameters strictly from the provided or default loaded configuration dictionary.
        Incorporates indicated combustion torque, propeller load, alternator load, starter torque, and mechanical friction.
        Modifying Engine 1 NEVER modifies Engine 2 state.
        """
        if engine_index not in self.state.engines:
            self.state.engines[engine_index] = EngineState(
                engine_index=engine_index,
                engine_id=f"engine_{engine_index}"
            )

        eng = self.state.engines[engine_index]
        dt = self.clock.dt_seconds
        cfg = engine_config if engine_config is not None else self.engine_config

        # Extract configuration values strictly via ConfigLoader schema
        inertia_kg_m2 = cfg["geometry_and_inertia"]["rotational_inertia_kg_m2"]["value"]
        max_torque_n_m = cfg["power_and_performance"]["max_indicated_torque_n_m"]["value"]
        f_static = cfg["friction_and_mechanical"]["friction_static_n_m"]["value"]
        f_viscous = cfg["friction_and_mechanical"]["friction_viscous_n_m_s_rad"]["value"]
        f_hydro = cfg["friction_and_mechanical"]["friction_hydrodynamic_n_m_s2_rad2"]["value"]

        # 1. Validate and set throttle input
        eng.throttle_percent = RotationalDynamicsModel.validate_throttle_input(throttle_percent)

        # 2. Compute or accept Indicated Torque
        if indicated_torque_n_m is not None:
            t_ind = max(0.0, float(indicated_torque_n_m))
        else:
            t_ind = RotationalDynamicsModel.compute_torque_demand_interface(
                throttle_percent=eng.throttle_percent,
                max_torque_n_m=max_torque_n_m
            )

        # 3. Compute Friction Torque
        t_fric = RotationalDynamicsModel.compute_friction_torque(
            omega_rad_per_sec=eng.engine_speed_rad_per_sec,
            friction_static_n_m=f_static,
            friction_viscous_n_m_s_rad=f_viscous,
            friction_hydrodynamic_n_m_s2_rad2=f_hydro
        )

        # 4. Total Driving Torque (Combustion + Starter) and Load Torque (Propeller + Alternator)
        t_driving_total = t_ind + max(0.0, float(starter_torque_n_m))
        t_load_total = max(0.0, float(load_torque_n_m)) + max(0.0, float(alternator_torque_n_m))

        # Compute Rotational Acceleration alpha = (T_driving - T_load - T_friction) / J_eng
        t_net, alpha = RotationalDynamicsModel.compute_rotational_acceleration(
            t_indicated_n_m=t_driving_total,
            t_load_n_m=t_load_total,
            t_friction_n_m=t_fric,
            inertia_kg_m2=inertia_kg_m2
        )

        # 5. Integrate Angular Velocity omega(t + dt)
        new_omega = RotationalDynamicsModel.integrate_angular_velocity(
            current_omega_rad_per_sec=eng.engine_speed_rad_per_sec,
            alpha_rad_per_sec2=alpha,
            dt_seconds=dt
        )

        # 6. Derive Display RPM
        new_rpm = RotationalDynamicsModel.rad_per_sec_to_rpm(new_omega)

        # 7. Update Engine State Attributes
        eng.engine_speed_rad_per_sec = new_omega
        eng.engine_rpm = new_rpm
        eng.indicated_torque_total_n_m = t_ind
        eng.friction_torque_n_m = t_fric
        eng.alternator_load_torque_n_m = float(alternator_torque_n_m)

        return eng

    def step_all_engines(
        self,
        throttles: Dict[int, float],
        loads: Optional[Dict[int, float]] = None,
        engine_configs: Optional[Dict[int, Dict[str, Any]]] = None
    ) -> Dict[int, EngineState]:
        """Steps all active engines concurrently and advances simulation clock."""
        loads = loads if loads is not None else {}
        engine_configs = engine_configs if engine_configs is not None else {}

        for eng_idx in self.state.engines.keys():
            th = throttles.get(eng_idx, 0.0)
            load = loads.get(eng_idx, 0.0)
            cfg = engine_configs.get(eng_idx, self.engine_config)
            self.step_engine(engine_index=eng_idx, throttle_percent=th, load_torque_n_m=load, engine_config=cfg)

        self.clock.step()
        return self.state.engines
