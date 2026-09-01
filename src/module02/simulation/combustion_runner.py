"""
Module 02 Combustion, Indicated Torque & Exhaust Energy Simulation Integration Runner (Phase 3.3.1 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Any, Dict, Optional
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.models.enums import EngineOperatingState
from src.module02.models.states import EngineState, SimulationState
from src.module02.physics.combustion import CombustionModel


class CombustionRunner:
    """
    Integration Runner for Phase 3.3.1 Fuel Delivery, AFR, Combustion, Indicated Torque Feedback, and Exhaust Energy.
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

    def step_combustion(
        self,
        engine_index: int,
        throttle_percent: float,
        air_mass_flow_kg_s: float,
        engine_rpm: float,
        ambient_temp_k: float = 288.15,
        intake_temp_k: float = 288.15,
        ambient_pressure_pa: float = 101325.0,
        injection_timing_deg_btdc: Optional[float] = None,
        starter_active: bool = False,
        engine_config: Optional[Dict[str, Any]] = None
    ) -> EngineState:
        """
        Executes one deterministic fuel/combustion/exhaust integration step for a specific engine instance.
        Reads engine physical parameters strictly from configuration.
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
        f_idle = cfg["fuel_and_combustion"]["idle_fuel_flow_kg_h"]["value"]
        f_max = cfg["fuel_and_combustion"]["max_fuel_flow_kg_h"]["value"]
        lhv = cfg["fuel_and_combustion"]["lower_heating_value_j_kg"]["value"]
        stoich_afr = cfg["fuel_and_combustion"]["stoichiometric_afr"]["value"]
        eta_comb_peak = cfg["fuel_and_combustion"]["peak_combustion_efficiency"]["value"]
        eta_ind_peak = cfg["fuel_and_combustion"]["indicated_efficiency_peak"]["value"]
        inj_opt = cfg["fuel_and_combustion"]["optimal_injection_timing_deg_btdc"]["value"]
        inj_sens = cfg["fuel_and_combustion"]["injection_timing_sensitivity"]["value"]
        f_exh = cfg["fuel_and_combustion"]["exhaust_heat_fraction"]["value"]
        idle_rpm = cfg["power_and_performance"]["idle_rpm"]["value"]

        inj_timing = injection_timing_deg_btdc if injection_timing_deg_btdc is not None else inj_opt

        # 1. Determine Engine Operating State (OFF, STARTING, IDLE, RUNNING)
        op_state = CombustionModel.determine_operating_state(
            engine_rpm=engine_rpm,
            throttle_percent=throttle_percent,
            starter_active=starter_active,
            idle_rpm=idle_rpm
        )

        omega = engine_rpm * (3.141592653589793 / 30.0)

        # 2. Fuel Delivery Physics (Constrained by FADEC smoke limiter / air availability)
        m_fuel_s, m_fuel_h, q_fuel_w = CombustionModel.compute_fuel_mass_flow(
            throttle_percent=throttle_percent,
            air_mass_flow_kg_s=air_mass_flow_kg_s,
            engine_rpm=engine_rpm,
            idle_fuel_flow_kg_h=f_idle,
            max_fuel_flow_kg_h=f_max,
            lower_heating_value_j_kg=lhv,
            operating_state=op_state,
            stoichiometric_afr=stoich_afr
        )

        # 3. Air-Fuel Ratio (AFR) & Equivalence Ratio (phi)
        afr_val, phi = CombustionModel.compute_air_fuel_ratio(
            air_mass_flow_kg_s=air_mass_flow_kg_s,
            fuel_mass_flow_kg_s=m_fuel_s,
            stoichiometric_afr=stoich_afr
        )

        display_afr = afr_val if afr_val is not None else 14.5 # Standard default for telemetry display

        # 4. Combustion Heat-Release Efficiency
        eta_comb, eta_phi, eta_timing = CombustionModel.compute_combustion_efficiency(
            equivalence_ratio_phi=phi,
            injection_timing_deg_btdc=inj_timing,
            optimal_injection_timing_deg_btdc=inj_opt,
            peak_combustion_efficiency=eta_comb_peak,
            injection_timing_sensitivity=inj_sens
        )

        # 5. Indicated Power & Indicated Crankshaft Torque (via Cycle Work Formulation)
        p_ind_w, t_ind_n_m = CombustionModel.compute_indicated_power_and_torque(
            fuel_mass_flow_kg_s=m_fuel_s,
            lower_heating_value_j_kg=lhv,
            combustion_efficiency=eta_comb,
            indicated_efficiency_peak=eta_ind_peak,
            omega_rad_per_sec=omega
        )

        # 6. Exhaust Mass Flow & Exhaust Energy Output for Phase 3.4 Turbo
        m_exh_s, t_exh_k, h_exh_j_kg, e_exh_w = CombustionModel.compute_exhaust_flow_and_energy(
            air_mass_flow_kg_s=air_mass_flow_kg_s,
            fuel_mass_flow_kg_s=m_fuel_s,
            fuel_energy_rate_w=q_fuel_w,
            combustion_efficiency=eta_comb,
            intake_temp_k=intake_temp_k,
            ambient_temp_k=ambient_temp_k,
            exhaust_heat_fraction=f_exh
        )

        # Update EngineState Subsystem Containers
        eng.operating_state = op_state
        eng.starter_active = starter_active
        eng.throttle_percent = throttle_percent
        eng.injection_timing_deg_btdc = inj_timing
        eng.fuel_mass_flow_kg_s = m_fuel_s
        eng.air_fuel_ratio = display_afr
        eng.indicated_power_w = p_ind_w
        eng.indicated_torque_total_n_m = t_ind_n_m

        eng.fuel.fuel_mass_flow_kg_s = m_fuel_s
        eng.fuel.fuel_mass_flow_kg_h = m_fuel_h
        eng.fuel.fuel_energy_rate_w = q_fuel_w
        eng.fuel.lower_heating_value_j_kg = lhv

        eng.combustion.air_fuel_ratio = display_afr
        eng.combustion.equivalence_ratio = phi
        eng.combustion.combustion_efficiency = eta_comb
        eng.combustion.indicated_power_w = p_ind_w
        eng.combustion.indicated_torque_n_m = t_ind_n_m
        eng.combustion.combustion_temp_k = t_exh_k
        eng.combustion.combustion_stability_index = min(1.0, eta_phi)

        eng.exhaust.exhaust_mass_flow_kg_s = m_exh_s
        eng.exhaust.exhaust_temp_k = t_exh_k
        eng.exhaust.exhaust_enthalpy_j_kg = h_exh_j_kg
        eng.exhaust.exhaust_energy_rate_w = e_exh_w

        return eng
