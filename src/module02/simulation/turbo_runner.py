"""
Module 02 Physically Closed Turbocharger Dynamic Integration Runner (Phase 3.4 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Any, Dict, Optional
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.models.states import EngineState, SimulationState
from src.module02.physics.turbocharger import TurbochargerModel


class TurboRunner:
    """
    Integration Runner for Phase 3.4 Physically Closed Turbocharger Dynamics.
    Replaces Phase 3.2 parametric placeholders with dynamic shaft energy balance integration:
    J_turbo * d(omega_turbo)/dt = tau_turbine - tau_compressor - tau_friction.
    Streams configuration values strictly from ConfigLoader without hardcoded Python defaults.
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

    def step_turbo(
        self,
        engine_index: int,
        exhaust_mass_flow_kg_s: float,
        exhaust_temp_k: float,
        exhaust_energy_rate_w: float,
        air_mass_flow_kg_s: float,
        ambient_pressure_pa: float = 101325.0,
        ambient_temp_k: float = 288.15,
        wastegate_position_percent: float = 0.0,
        engine_config: Optional[Dict[str, Any]] = None
    ) -> EngineState:
        """
        Executes one deterministic turbocharger shaft integration step for a specific engine instance.
        Reads physical parameters strictly from configuration.
        Modifying Engine 1 NEVER modifies Engine 2 state.
        """
        if engine_index not in self.state.engines:
            self.state.engines[engine_index] = EngineState(
                engine_index=engine_index,
                engine_id=f"engine_{engine_index}"
            )

        eng = self.state.engines[engine_index]
        cfg = engine_config if engine_config is not None else self.engine_config

        # Extract configuration values strictly via ConfigLoader schema
        j_turbo = cfg["turbocharger"]["rotational_inertia_kg_m2"]["value"]
        eta_t = cfg["turbocharger"]["turbine_efficiency_peak"]["value"]
        eta_c = cfg["turbocharger"]["compressor_efficiency_peak"]["value"]
        pi_max = cfg["turbocharger"]["max_compressor_pressure_ratio"]["value"]
        map_max = cfg["turbocharger"]["max_manifold_absolute_pressure_pa"]["value"]
        max_rpm = cfg["turbocharger"]["max_turbo_speed_rpm"]["value"]
        eps_ic = cfg["turbocharger"]["intercooler_effectiveness"]["value"]
        t_stat = cfg["turbocharger"]["turbo_friction_static_n_m"]["value"]
        c_visc = cfg["turbocharger"]["turbo_friction_viscous_n_m_s_rad"]["value"]
        c_hydro = cfg["turbocharger"]["turbo_friction_hydrodynamic_n_m_s2_rad2"]["value"]

        current_w = eng.turbocharger.turbo_omega_rad_per_sec

        # 1. Turbine Energy Extraction & Driving Torque
        p_turbine_w, tau_turbine_n_m = TurbochargerModel.compute_turbine_power_and_torque(
            exhaust_mass_flow_kg_s=exhaust_mass_flow_kg_s,
            exhaust_temp_k=exhaust_temp_k,
            exhaust_energy_rate_w=exhaust_energy_rate_w,
            turbine_efficiency=eta_t,
            turbo_omega_rad_per_sec=current_w,
            ambient_temp_k=ambient_temp_k,
            wastegate_position_percent=wastegate_position_percent
        )

        # 2. Compressor Work & Closed-Loop MAP
        map_pa, boost_pa, pi_c, t_comp_out_k, t_manifold_k, p_compressor_w, tau_compressor_n_m = (
            TurbochargerModel.compute_compressor_work_and_map(
                air_mass_flow_kg_s=air_mass_flow_kg_s,
                turbo_omega_rad_per_sec=current_w,
                max_turbo_speed_rpm=max_rpm,
                max_compressor_pressure_ratio=pi_max,
                max_map_pa=map_max,
                ambient_pressure_pa=ambient_pressure_pa,
                ambient_temp_k=ambient_temp_k,
                compressor_efficiency=eta_c,
                intercooler_effectiveness=eps_ic
            )
        )

        # 3. Turbocharger Shaft Friction Torque
        tau_friction_n_m = TurbochargerModel.compute_turbo_friction_torque(
            turbo_omega_rad_per_sec=current_w,
            friction_static_n_m=t_stat,
            friction_viscous_n_m_s_rad=c_visc,
            friction_hydrodynamic_n_m_s2_rad2=c_hydro
        )

        # 4. Integrate Turbo Shaft Rotational Acceleration: J_turbo * d(omega)/dt = tau_turbine - tau_compressor - tau_friction
        new_w, new_rpm, alpha = TurbochargerModel.step_turbo_shaft_dynamics(
            turbo_omega_rad_per_sec=current_w,
            tau_turbine_n_m=tau_turbine_n_m,
            tau_compressor_n_m=tau_compressor_n_m,
            tau_friction_n_m=tau_friction_n_m,
            rotational_inertia_kg_m2=j_turbo,
            max_turbo_speed_rpm=max_rpm,
            dt_seconds=self.clock.dt_seconds
        )

        # Update EngineState Subsystem Containers
        eng.manifold_pressure_pa = map_pa

        eng.turbocharger.turbo_speed_rpm = new_rpm
        eng.turbocharger.turbo_omega_rad_per_sec = new_w
        eng.turbocharger.turbine_torque_n_m = tau_turbine_n_m
        eng.turbocharger.compressor_torque_n_m = tau_compressor_n_m
        eng.turbocharger.turbo_friction_torque_n_m = tau_friction_n_m
        eng.turbocharger.turbine_power_w = p_turbine_w
        eng.turbocharger.compressor_power_w = p_compressor_w
        eng.turbocharger.compressor_pressure_ratio = pi_c
        eng.turbocharger.compressor_outlet_temp_k = t_comp_out_k
        eng.turbocharger.intercooler_effectiveness = eps_ic
        eng.turbocharger.max_manifold_absolute_pressure_pa = map_max
        eng.turbocharger.wastegate_position_percent = wastegate_position_percent

        return eng
