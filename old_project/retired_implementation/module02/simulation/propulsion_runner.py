"""
Module 02 Propeller Aerodynamics, Reflected Gearbox Load, Wear Degradation, and Vibration Integration Runner (Phase 3.6 Engine).
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Any, Dict, Optional, Tuple
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.models.states import (
    DegradationState,
    EngineState,
    GearboxState,
    PropellerState,
    SimulationState,
    VibrationState,
)
from src.module02.physics.propulsion_wear_vibration import PropulsionWearVibrationModel
from src.module02.physics.rotational_dynamics import RotationalDynamicsModel


class PropulsionRunner:
    """
    Integration Runner for Phase 3.6 Propeller Aerodynamic Load, Gearbox Reflection,
    Cumulative Wear Degradation, and 1000 Hz Structural Vibration Acceleration Synthesis.
    Streams configuration values strictly from ConfigLoader without hardcoded Python defaults.
    """

    def __init__(self, clock: Optional[SimulationClock] = None, engine_config: Optional[Dict[str, Any]] = None) -> None:
        self.clock = clock if clock is not None else SimulationClock()
        self.state = SimulationState()
        self.engine_config = engine_config if engine_config is not None else ConfigLoader.load_engine_config()
        self._initialize_twin_engines()

    def _initialize_twin_engines(self) -> None:
        """Initializes independent EngineState, PropellerState, DegradationState, and VibrationState for Engine 1 and 2."""
        self.state.engines[1] = EngineState(engine_index=1, engine_id="engine_left")
        self.state.engines[2] = EngineState(engine_index=2, engine_id="engine_right")
        self.state.propellers[1] = PropellerState(engine_index=1)
        self.state.propellers[2] = PropellerState(engine_index=2)
        self.state.degradation[1] = DegradationState()
        self.state.degradation[2] = DegradationState()
        self.state.vibration[1] = VibrationState()
        self.state.vibration[2] = VibrationState()

    def step_propulsion(
        self,
        engine_index: int,
        engine_rpm: float,
        air_density_kg_m3: float,
        indicated_torque_n_m: float,
        fuel_mass_flow_kg_s: float,
        cht_k: float = 288.15,
        oil_temp_k: float = 288.15,
        oil_viscosity_pa_s: float = 0.08,
        engine_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[EngineState, PropellerState, DegradationState, VibrationState]:
        """
        Executes one deterministic propulsion load, gearbox reflection, wear degradation,
        and vibration synthesis step for a specific engine instance.
        Modifying Engine 1 NEVER modifies Engine 2 state.
        """
        if engine_index not in self.state.engines:
            self.state.engines[engine_index] = EngineState(engine_index=engine_index, engine_id=f"engine_{engine_index}")
            self.state.propellers[engine_index] = PropellerState(engine_index=engine_index)
            self.state.degradation[engine_index] = DegradationState()
            self.state.vibration[engine_index] = VibrationState()

        eng = self.state.engines[engine_index]
        prop = self.state.propellers[engine_index]
        deg = self.state.degradation[engine_index]
        vib = self.state.vibration[engine_index]
        cfg = engine_config if engine_config is not None else self.engine_config

        # Synchronize engine RPM and indicated torque
        eng.engine_rpm = float(engine_rpm)
        eng.engine_speed_rad_per_sec = float(engine_rpm) * (3.141592653589793 / 30.0)
        eng.indicated_torque_total_n_m = float(indicated_torque_n_m)

        # Extract configuration values strictly via ConfigLoader schema
        s_ratio = cfg["gearbox"]["engine_to_propeller_speed_ratio"]["value"]
        eta_gb = cfg["gearbox"]["gearbox_efficiency"]["value"]
        d_prop = cfg["propeller"]["diameter_m"]["value"]
        c_q = cfg["propeller"]["torque_coefficient_cq"]["value"]
        c_t = cfg["propeller"]["thrust_coefficient_ct"]["value"]
        b_blades = int(cfg["propeller"]["blade_count"]["value"])

        kb_rate = cfg["degradation"]["bearing_wear_rate_per_sec"]["value"]
        kr_rate = cfg["degradation"]["ring_wear_rate_per_sec"]["value"]
        kinj_rate = cfg["degradation"]["injector_wear_rate_per_sec"]["value"]

        f_wear_sens = cfg["degradation"]["friction_wear_sensitivity"]["value"]

        f_stat = cfg["friction_and_mechanical"]["friction_static_n_m"]["value"]
        f_visc = cfg["friction_and_mechanical"]["friction_viscous_n_m_s_rad"]["value"]
        f_hydro = cfg["friction_and_mechanical"]["friction_hydrodynamic_n_m_s2_rad2"]["value"]

        rot_amp = cfg["vibration"]["rotational_amplitude_base_m_s2"]["value"]
        fire_amp = cfg["vibration"]["firing_amplitude_base_m_s2"]["value"]
        prop_amp = cfg["vibration"]["propeller_amplitude_base_m_s2"]["value"]
        deg_sens = cfg["vibration"]["degradation_vibration_sensitivity"]["value"]
        sample_rate = cfg["vibration"]["sample_rate_hz"]["value"]

        rated_rpm = cfg["power_and_performance"]["rated_rpm"]["value"]
        max_torque = cfg["power_and_performance"]["max_indicated_torque_n_m"]["value"]
        mu_ref = cfg["lubrication"]["reference_viscosity_pa_s"]["value"]
        t_ref_oil = cfg["lubrication"]["reference_oil_temperature_k"]["value"]
        max_fuel_h = cfg["fuel_and_combustion"]["max_fuel_flow_kg_h"]["value"]
        max_fuel_s = max_fuel_h / 3600.0

        # Validate inputs
        PropulsionWearVibrationModel.validate_inputs(
            engine_rpm=engine_rpm,
            air_density_kg_m3=air_density_kg_m3,
            speed_ratio=s_ratio,
            gearbox_efficiency=eta_gb,
            dt_seconds=self.clock.dt_seconds
        )

        # 1. Propeller Aerodynamics & Gearbox Reflection
        rpm_prop, n_prop, omega_prop, t_prop_n_m, f_thrust_n, t_eng_load_n_m = (
            PropulsionWearVibrationModel.compute_propeller_and_gearbox(
                engine_rpm=engine_rpm,
                air_density_kg_m3=air_density_kg_m3,
                speed_ratio=s_ratio,
                gearbox_efficiency=eta_gb,
                diameter_m=d_prop,
                torque_coefficient_cq=c_q,
                thrust_coefficient_ct=c_t
            )
        )

        # 2. Cumulative Wear Degradation Integration
        new_d_b, new_d_r, new_d_inj = PropulsionWearVibrationModel.step_degradation(
            current_bearing_wear=deg.bearing_wear,
            current_ring_wear=deg.ring_wear,
            current_injector_wear=deg.injector_wear,
            engine_rpm=engine_rpm,
            indicated_torque_n_m=indicated_torque_n_m,
            fuel_mass_flow_kg_s=fuel_mass_flow_kg_s,
            cht_k=cht_k,
            oil_temp_k=oil_temp_k,
            oil_viscosity_pa_s=oil_viscosity_pa_s,
            dt_seconds=self.clock.dt_seconds,
            bearing_wear_rate_per_sec=kb_rate,
            ring_wear_rate_per_sec=kr_rate,
            injector_wear_rate_per_sec=kinj_rate,
            rated_rpm=rated_rpm,
            max_indicated_torque_n_m=max_torque,
            reference_viscosity_pa_s=mu_ref,
            reference_oil_temp_k=t_ref_oil,
            max_fuel_flow_kg_s=max_fuel_s
        )

        # 3. 1000 Hz Structural Vibration Acceleration Synthesis
        inst_accel, vib_rms, dom_freq, f_rot, f_fire, f_prop, time_buf = (
            PropulsionWearVibrationModel.synthesize_vibration(
                engine_rpm=engine_rpm,
                indicated_torque_n_m=indicated_torque_n_m,
                propeller_load_n_m=t_prop_n_m,
                bearing_wear=new_d_b,
                dt_seconds=self.clock.dt_seconds,
                sample_rate_hz=sample_rate,
                rotational_amplitude_base_m_s2=rot_amp,
                firing_amplitude_base_m_s2=fire_amp,
                propeller_amplitude_base_m_s2=prop_amp,
                degradation_vibration_sensitivity=deg_sens,
                blade_count=b_blades,
                speed_ratio=s_ratio,
                rated_rpm=rated_rpm,
                max_torque_n_m=max_torque
            )
        )

        # Update Subsystem Containers
        prop.propeller_rpm = rpm_prop
        prop.propeller_omega_rad_per_sec = omega_prop
        prop.rev_per_sec = n_prop
        prop.torque_coefficient_cq = c_q
        prop.thrust_coefficient_ct = c_t
        prop.diameter_m = d_prop
        prop.load_torque_n_m = t_prop_n_m
        prop.thrust_n = f_thrust_n
        prop.reflected_engine_load_n_m = t_eng_load_n_m

        eng.gearbox.engine_to_propeller_speed_ratio = s_ratio
        eng.gearbox.gearbox_efficiency = eta_gb
        eng.gearbox.propeller_torque_n_m = t_prop_n_m
        eng.gearbox.reflected_engine_load_n_m = t_eng_load_n_m

        deg.bearing_wear = new_d_b
        deg.ring_wear = new_d_r
        deg.injector_wear = new_d_inj
        if engine_rpm > 1.0:
            deg.cumulative_operating_sec += self.clock.dt_seconds

        # Ensure nominal friction torque is computed if uninitialized
        if eng.friction_torque_n_m <= 0.0 and engine_rpm > 0.0:
            omega_eng = engine_rpm * (3.141592653589793 / 30.0)
            eng.friction_torque_n_m = RotationalDynamicsModel.compute_friction_torque(
                omega_rad_per_sec=omega_eng,
                friction_static_n_m=f_stat,
                friction_viscous_n_m_s_rad=f_visc,
                friction_hydrodynamic_n_m_s2_rad2=f_hydro
            )

        # Bearing wear modifies engine friction torque
        eng.friction_torque_n_m *= (1.0 + (f_wear_sens * new_d_b))

        vib.vibration_rms_m_s2 = vib_rms
        vib.dominant_frequency_hz = dom_freq
        vib.rotational_order_freq_hz = f_rot
        vib.firing_order_freq_hz = f_fire
        vib.propeller_order_freq_hz = f_prop
        vib.time_domain_buffer = time_buf

        return (eng, prop, deg, vib)
