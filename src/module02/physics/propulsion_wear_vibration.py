"""
Module 02 Propeller Aerodynamics, Gearbox Reflection, Degradation Wear, and 1000 Hz Structural Vibration Physics (Phase 3.6 Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import List, Tuple


class PropulsionWearVibrationError(ValueError):
    """Raised when numerical safety or physical boundary violations occur in propulsion, wear, or vibration physics."""
    pass


class PropulsionWearVibrationModel:
    """
    Propeller Aerodynamic Load, Gearbox Reflection, Cumulative Wear Degradation,
    and 1000 Hz Structural Vibration Acceleration Synthesis Subsystem.
    All calculations strictly use Canonical SI Units (m, kg/m^3, N, N*m, W, rad/s, Hz, m/s^2).
    """

    @classmethod
    def validate_inputs(
        cls,
        engine_rpm: float,
        air_density_kg_m3: float,
        speed_ratio: float,
        gearbox_efficiency: float,
        dt_seconds: float
    ) -> None:
        """Validates numerical safety and physical bounds for propulsion inputs."""
        if math.isnan(engine_rpm) or math.isinf(engine_rpm) or engine_rpm < 0:
            raise PropulsionWearVibrationError(f"Invalid engine RPM: {engine_rpm}.")

        if math.isnan(air_density_kg_m3) or math.isinf(air_density_kg_m3) or air_density_kg_m3 <= 0:
            raise PropulsionWearVibrationError(f"Invalid air density: {air_density_kg_m3} kg/m^3.")

        if math.isnan(speed_ratio) or math.isinf(speed_ratio) or speed_ratio <= 0:
            raise PropulsionWearVibrationError(f"Invalid gearbox speed ratio: {speed_ratio}.")

        if math.isnan(gearbox_efficiency) or math.isinf(gearbox_efficiency) or not (0.1 <= gearbox_efficiency <= 1.0):
            raise PropulsionWearVibrationError(f"Invalid gearbox efficiency: {gearbox_efficiency}.")

        if math.isnan(dt_seconds) or math.isinf(dt_seconds) or dt_seconds <= 0:
            raise PropulsionWearVibrationError(f"Invalid simulation timestep dt: {dt_seconds} s.")

    @classmethod
    def compute_propeller_and_gearbox(
        cls,
        engine_rpm: float,
        air_density_kg_m3: float,
        speed_ratio: float = 0.65,
        gearbox_efficiency: float = 0.97,
        diameter_m: float = 1.90,
        torque_coefficient_cq: float = 0.014,
        thrust_coefficient_ct: float = 0.085
    ) -> Tuple[float, float, float, float, float, float]:
        """
        Computes propeller aerodynamic torque and thrust, and reflects load torque back to engine crankshaft:
        N_prop = N_engine * speed_ratio
        n_prop = N_prop / 60.0 (rev/s)
        T_prop = Cq * rho * n_prop^2 * D^5 (N*m)
        F_thrust = Ct * rho * n_prop^2 * D^4 (N)
        T_reflected_engine = (T_prop * speed_ratio) / gearbox_efficiency (N*m)
        Returns Tuple of (propeller_rpm, rev_per_sec, propeller_omega_rad_s, propeller_torque_n_m, thrust_n, reflected_engine_load_n_m).
        """
        rpm_eng = max(0.0, float(engine_rpm))
        rho = float(air_density_kg_m3)
        s_ratio = float(speed_ratio)
        eta_gb = float(gearbox_efficiency)
        d_prop = float(diameter_m)
        c_q = float(torque_coefficient_cq)
        c_t = float(thrust_coefficient_ct)

        if rho <= 0 or s_ratio <= 0 or eta_gb <= 0 or d_prop <= 0:
            raise PropulsionWearVibrationError("Physical dimensions and ratios must be positive.")

        # Propeller Shaft Rotational Speeds
        rpm_prop = rpm_eng * s_ratio
        n_prop = rpm_prop / 60.0  # rev/s
        omega_prop = rpm_prop * (math.pi / 30.0) # rad/s

        if n_prop <= 1e-6:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Propeller Aerodynamic Load Torque (N*m) & Thrust (N)
        n_sq = n_prop * n_prop
        d_4 = math.pow(d_prop, 4)
        d_5 = d_4 * d_prop

        t_prop = c_q * rho * n_sq * d_5
        f_thrust = c_t * rho * n_sq * d_4

        # Reflected Engine Crankshaft Load Torque (N*m) obeying Power Conservation:
        # P_prop = T_prop * omega_prop
        # P_engine_load = P_prop / eta_gb = (T_prop * s_ratio * omega_eng) / eta_gb
        # => T_reflected_engine = (T_prop * s_ratio) / eta_gb
        t_engine_load = (t_prop * s_ratio) / eta_gb

        return (rpm_prop, n_prop, omega_prop, t_prop, f_thrust, t_engine_load)

    @classmethod
    def step_degradation(
        cls,
        current_bearing_wear: float,
        current_ring_wear: float,
        current_injector_wear: float,
        engine_rpm: float,
        indicated_torque_n_m: float,
        fuel_mass_flow_kg_s: float,
        cht_k: float,
        oil_temp_k: float,
        oil_viscosity_pa_s: float,
        dt_seconds: float,
        bearing_wear_rate_per_sec: float = 1e-6,
        ring_wear_rate_per_sec: float = 1e-6,
        injector_wear_rate_per_sec: float = 1e-6,
        rated_rpm: float = 4200.0,
        max_indicated_torque_n_m: float = 320.0,
        reference_viscosity_pa_s: float = 0.012,
        reference_oil_temp_k: float = 373.15,
        max_fuel_flow_kg_s: float = 0.008194
    ) -> Tuple[float, float, float]:
        """
        Integrates dynamic cumulative wear degradation states for bearing, piston ring, and injector:
        0.0 <= D <= 1.0 (bounded).
        Returns Tuple of (new_bearing_wear, new_ring_wear, new_injector_wear).
        """
        d_b = float(current_bearing_wear)
        d_r = float(current_ring_wear)
        d_inj = float(current_injector_wear)

        rpm = max(0.0, float(engine_rpm))
        t_ind = max(0.0, float(indicated_torque_n_m))
        m_fuel = max(0.0, float(fuel_mass_flow_kg_s))
        cht = max(250.0, float(cht_k))
        t_oil = max(250.0, float(oil_temp_k))
        mu_oil = max(0.001, float(oil_viscosity_pa_s))
        dt = float(dt_seconds)

        if rpm <= 1.0:
            # Engine stopped -> Zero degradation accumulation
            return (d_b, d_r, d_inj)

        # Normalized Operating Ratios
        r_rpm = rpm / max(1.0, rated_rpm)
        r_torque = t_ind / max(1.0, max_indicated_torque_n_m)
        r_fuel = m_fuel / max(1e-5, max_fuel_flow_kg_s)
        r_visc_penalty = max(1.0, reference_viscosity_pa_s / mu_oil) if mu_oil < reference_viscosity_pa_s else 1.0
        r_temp_penalty = max(1.0, cht / reference_oil_temp_k)

        # 1. Bearing Wear Accumulation
        dd_b = bearing_wear_rate_per_sec * r_rpm * (0.5 + 0.5 * r_torque) * r_visc_penalty * dt
        new_d_b = max(0.0, min(1.0, d_b + dd_b))

        # 2. Piston Ring Wear Accumulation
        dd_r = ring_wear_rate_per_sec * r_rpm * r_temp_penalty * dt
        new_d_r = max(0.0, min(1.0, d_r + dd_r))

        # 3. Injector Erosion Wear Accumulation
        dd_inj = injector_wear_rate_per_sec * r_fuel * r_temp_penalty * dt
        new_d_inj = max(0.0, min(1.0, d_inj + dd_inj))

        return (new_d_b, new_d_r, new_d_inj)

    @classmethod
    def synthesize_vibration(
        cls,
        engine_rpm: float,
        indicated_torque_n_m: float,
        propeller_load_n_m: float,
        bearing_wear: float,
        dt_seconds: float,
        sample_rate_hz: float = 1000.0,
        rotational_amplitude_base_m_s2: float = 8.0,
        firing_amplitude_base_m_s2: float = 15.0,
        propeller_amplitude_base_m_s2: float = 6.0,
        degradation_vibration_sensitivity: float = 25.0,
        blade_count: int = 3,
        speed_ratio: float = 0.65,
        rated_rpm: float = 4200.0,
        max_torque_n_m: float = 320.0
    ) -> Tuple[float, float, float, float, float, float, List[float]]:
        """
        Synthesizes 1000 Hz structural vibration acceleration a_vibration(t) in m/s^2 from physical orders:
        f_rot = N_engine / 60 (Hz)
        f_fire = 2 * f_rot (Hz) (4-stroke 4-cylinder engine)
        f_prop = blade_count * (N_prop / 60) (Hz)
        Returns Tuple of (instantaneous_accel_m_s2, vibration_rms_m_s2, dominant_freq_hz, f_rot, f_fire, f_prop, time_buffer).
        """
        rpm = max(0.0, float(engine_rpm))
        t_ind = max(0.0, float(indicated_torque_n_m))
        t_prop = max(0.0, float(propeller_load_n_m))
        d_b = max(0.0, min(1.0, float(bearing_wear)))

        if rpm <= 1.0:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, [0.0] * 100)

        # Rotational Frequencies (Hz)
        f_rot = rpm / 60.0
        f_fire = 2.0 * f_rot  # 4-cylinder 4-stroke firing frequency (2 firings per crankshaft rev)
        f_prop = float(blade_count) * (rpm * speed_ratio / 60.0)

        # Dominant Spectral Frequency Peak
        dom_freq = f_fire if t_ind > 5.0 else f_rot

        # Amplitudes (m/s^2)
        r_rpm = rpm / max(1.0, rated_rpm)
        r_load = t_ind / max(1.0, max_torque_n_m)

        a_rot_amp = rotational_amplitude_base_m_s2 * (r_rpm ** 1.5)
        a_fire_amp = firing_amplitude_base_m_s2 * r_rpm * (0.3 + 0.7 * r_load)
        a_prop_amp = propeller_amplitude_base_m_s2 * (r_rpm ** 1.5) * (0.3 + 0.7 * (t_prop / 150.0))
        a_deg_amp = degradation_vibration_sensitivity * d_b * r_rpm

        # Synthesize 1-second 1000 Hz time-domain acceleration buffer
        n_samples = int(sample_rate_hz)
        time_buffer: List[float] = []
        sum_sq = 0.0

        for i in range(n_samples):
            t = float(i) / sample_rate_hz

            a_rot = a_rot_amp * math.sin(2.0 * math.pi * f_rot * t)
            a_fire = a_fire_amp * math.sin(2.0 * math.pi * f_fire * t + 0.5)
            a_prop = a_prop_amp * math.sin(2.0 * math.pi * f_prop * t + 1.2)
            a_deg = a_deg_amp * math.sin(2.0 * math.pi * (4.5 * f_rot) * t)

            a_total = a_rot + a_fire + a_prop + a_deg
            time_buffer.append(a_total)
            sum_sq += a_total * a_total

        inst_accel = time_buffer[0]
        vib_rms = math.sqrt(sum_sq / float(n_samples))

        return (inst_accel, vib_rms, dom_freq, f_rot, f_fire, f_prop, time_buffer)
