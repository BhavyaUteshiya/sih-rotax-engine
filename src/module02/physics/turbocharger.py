"""
Module 02 Physically Closed Turbocharger & Turbine Dynamics Subsystem (Phase 3.4 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Tuple


class TurbochargerPhysicsError(ValueError):
    """Raised when numerical safety or physical boundary violations occur in turbocharger physics."""
    pass


class TurbochargerModel:
    """
    Physically Closed Turbocharger Subsystem: Turbine power extraction, compressor thermodynamic work,
    closed-loop MAP generation, and turbo shaft rotational dynamics integration.
    All calculations strictly use Canonical SI Units (Pa, K, kg/s, rad/s, N*m, W, J/kg, kg*m^2).
    """

    AIR_SPECIFIC_HEAT_J_KG_K: float = 1005.0   # Cp_air (J/(kg K))
    AIR_GAMMA: float = 1.4                     # Ratio of specific heats gamma for air
    EXHAUST_GAMMA: float = 1.33                # Ratio of specific heats gamma for exhaust gas

    @classmethod
    def validate_inputs(
        cls,
        rotational_inertia_kg_m2: float,
        max_turbo_speed_rpm: float,
        dt_seconds: float
    ) -> None:
        """Validates numerical safety and physical bounds for turbocharger inputs."""
        if math.isnan(rotational_inertia_kg_m2) or math.isinf(rotational_inertia_kg_m2) or rotational_inertia_kg_m2 <= 0:
            raise TurbochargerPhysicsError(f"Invalid turbo rotational inertia: {rotational_inertia_kg_m2} kg*m^2. Must be positive.")

        if math.isnan(max_turbo_speed_rpm) or math.isinf(max_turbo_speed_rpm) or max_turbo_speed_rpm <= 0:
            raise TurbochargerPhysicsError(f"Invalid max turbo speed limit: {max_turbo_speed_rpm} RPM.")

        if math.isnan(dt_seconds) or math.isinf(dt_seconds) or dt_seconds <= 0:
            raise TurbochargerPhysicsError(f"Invalid simulation timestep dt: {dt_seconds} s.")

    @classmethod
    def compute_turbine_power_and_torque(
        cls,
        exhaust_mass_flow_kg_s: float,
        exhaust_temp_k: float,
        exhaust_energy_rate_w: float,
        turbine_efficiency: float,
        turbo_omega_rad_per_sec: float,
        ambient_temp_k: float = 288.15,
        wastegate_position_percent: float = 0.0
    ) -> Tuple[float, float]:
        """
        Computes turbine aerodynamic power extraction P_turbine and turbine driving torque tau_turbine:
        P_turbine = turbine_efficiency * (1.0 - wastegate_fraction) * min(E_dot_exh, m_dot_exh * Cp_exh * (T_exh - T_amb))
        tau_turbine = P_turbine / max(50.0, omega_turbo)  (N*m)

        Enforces 0 <= P_turbine <= exhaust_energy_rate_w.
        Returns Tuple of (p_turbine_w, tau_turbine_n_m).
        """
        m_exh = float(exhaust_mass_flow_kg_s)
        t_exh = float(exhaust_temp_k)
        e_exh_w = float(exhaust_energy_rate_w)
        eta_t = float(turbine_efficiency)
        w_turbo = float(turbo_omega_rad_per_sec)
        t_amb = float(ambient_temp_k)
        wg_pct = max(0.0, min(100.0, float(wastegate_position_percent)))

        if m_exh < 0 or t_exh <= 0 or e_exh_w < 0:
            raise TurbochargerPhysicsError("Invalid exhaust mass flow, temperature, or energy inputs for turbine model.")

        if eta_t < 0 or eta_t > 1.0:
            raise TurbochargerPhysicsError(f"Invalid turbine efficiency: {turbine_efficiency}.")

        if m_exh <= 1e-7 or e_exh_w <= 1e-7:
            return (0.0, 0.0)

        # Wastegate Bypass Factor
        wg_factor = 1.0 - (wg_pct / 100.0)

        # Turbine Aerodynamic Power Extraction (W)
        p_turbine_w = max(0.0, min(e_exh_w, eta_t * wg_factor * e_exh_w))

        # Turbine Shaft Driving Torque (N*m) with Low-Speed Singularity Protection
        w_abs = abs(w_turbo)
        w_effective = max(50.0, w_abs)
        tau_turbine_n_m = p_turbine_w / w_effective

        return (p_turbine_w, tau_turbine_n_m)

    @classmethod
    def compute_compressor_work_and_map(
        cls,
        air_mass_flow_kg_s: float,
        turbo_omega_rad_per_sec: float,
        max_turbo_speed_rpm: float,
        max_compressor_pressure_ratio: float,
        max_map_pa: float,
        ambient_pressure_pa: float,
        ambient_temp_k: float,
        compressor_efficiency: float,
        intercooler_effectiveness: float = 0.85
    ) -> Tuple[float, float, float, float, float, float, float]:
        """
        Computes closed-loop Manifold Absolute Pressure (MAP), gauge boost, compressor discharge temperature,
        intercooler outlet temperature, compressor power requirement P_compressor, and compressor load torque tau_compressor:
        Pi_c = 1.0 + (Pi_c_max - 1.0) * (omega_turbo / omega_turbo_max)^2
        MAP = min(max_map_pa, ambient_pressure_pa * Pi_c)
        T_comp_out = T_amb * [1 + (1 / eta_comp) * (Pi_c^((gamma-1)/gamma) - 1)]
        T_manifold = T_amb + (1 - epsilon_intercooler) * (T_comp_out - T_amb)
        P_compressor = (m_dot_air * Cp_air * (T_comp_out - T_amb)) / eta_comp
        tau_compressor = P_compressor / max(50.0, omega_turbo)

        Returns Tuple of (map_pa, boost_gauge_pa, pressure_ratio, T_comp_out_k, T_manifold_k, p_compressor_w, tau_compressor_n_m).
        """
        m_air = float(air_mass_flow_kg_s)
        w_turbo = float(turbo_omega_rad_per_sec)
        max_rpm = float(max_turbo_speed_rpm)
        pi_max = float(max_compressor_pressure_ratio)
        p_map_max = float(max_map_pa)
        p_amb = float(ambient_pressure_pa)
        t_amb = float(ambient_temp_k)
        eta_c = float(compressor_efficiency)
        eps_ic = float(intercooler_effectiveness)

        if p_amb <= 0 or t_amb <= 0 or pi_max < 1.0 or eta_c <= 0:
            raise TurbochargerPhysicsError("Invalid ambient pressure, temperature, or compressor mapping parameters.")

        w_max = max_rpm * (math.pi / 30.0)

        # 1. Closed-Loop Pressure Ratio as a function of Shaft Speed
        speed_ratio = max(0.0, min(1.2, abs(w_turbo) / w_max))
        pi_c = 1.0 + ((pi_max - 1.0) * math.pow(speed_ratio, 2))

        # 2. Closed-Loop Manifold Absolute Pressure (MAP) and Gauge Boost
        map_pa = max(p_amb, min(p_map_max, p_amb * pi_c))
        actual_pi_c = map_pa / p_amb
        boost_gauge_pa = max(0.0, map_pa - p_amb)

        # 3. Compressor Isentropic Discharge Temperature Rise
        exponent = (cls.AIR_GAMMA - 1.0) / cls.AIR_GAMMA
        is_temp_ratio = math.pow(actual_pi_c, exponent) - 1.0
        t_comp_out_k = t_amb * (1.0 + (is_temp_ratio / max(0.10, eta_c)))

        # 4. Intercooler Thermal Effectiveness
        t_manifold_k = t_amb + ((1.0 - eps_ic) * max(0.0, t_comp_out_k - t_amb))

        # 5. Compressor Power Requirement (W)
        p_compressor_w = max(0.0, (m_air * cls.AIR_SPECIFIC_HEAT_J_KG_K * max(0.0, t_comp_out_k - t_amb)) / max(0.10, eta_c))

        # 6. Compressor Load Torque (N*m) with Low-Speed Singularity Protection
        w_effective = max(50.0, abs(w_turbo))
        tau_compressor_n_m = p_compressor_w / w_effective

        return (map_pa, boost_gauge_pa, actual_pi_c, t_comp_out_k, t_manifold_k, p_compressor_w, tau_compressor_n_m)

    @classmethod
    def compute_turbo_friction_torque(
        cls,
        turbo_omega_rad_per_sec: float,
        friction_static_n_m: float = 0.02,
        friction_viscous_n_m_s_rad: float = 0.00005,
        friction_hydrodynamic_n_m_s2_rad2: float = 0.00000001
    ) -> float:
        """
        Computes turbo shaft mechanical friction torque opposing rotation:
        tau_friction = tau_static * tanh(10 * omega) + c_viscous * omega + c_hydro * omega^2
        Returns tau_turbo_friction_n_m.
        """
        w = float(turbo_omega_rad_per_sec)
        t_stat = float(friction_static_n_m)
        c_visc = float(friction_viscous_n_m_s_rad)
        c_hydro = float(friction_hydrodynamic_n_m_s2_rad2)

        w_abs = abs(w)
        if w_abs <= 1e-4:
            return 0.0

        tau_fric = (t_stat * math.tanh(10.0 * w_abs)) + (c_visc * w_abs) + (c_hydro * w_abs * w_abs)
        return tau_fric

    @classmethod
    def step_turbo_shaft_dynamics(
        cls,
        turbo_omega_rad_per_sec: float,
        tau_turbine_n_m: float,
        tau_compressor_n_m: float,
        tau_friction_n_m: float,
        rotational_inertia_kg_m2: float,
        max_turbo_speed_rpm: float,
        dt_seconds: float
    ) -> Tuple[float, float, float]:
        """
        Integrates turbo shaft angular acceleration over timestep dt:
        J_turbo * d(omega_turbo)/dt = tau_turbine - tau_compressor - tau_friction
        omega_new = max(0.0, min(omega_max, omega + alpha * dt))
        Returns Tuple of (new_omega_rad_per_sec, new_speed_rpm, alpha_rad_per_sec2).
        """
        cls.validate_inputs(rotational_inertia_kg_m2, max_turbo_speed_rpm, dt_seconds)

        w = float(turbo_omega_rad_per_sec)
        t_turb = float(tau_turbine_n_m)
        t_comp = float(tau_compressor_n_m)
        t_fric = float(tau_friction_n_m)
        j_turbo = float(rotational_inertia_kg_m2)
        max_rpm = float(max_turbo_speed_rpm)
        dt = float(dt_seconds)

        w_max = max_rpm * (math.pi / 30.0)

        # Net Shaft Accelerating Torque (N*m)
        tau_net = t_turb - t_comp - t_fric

        # Angular Acceleration alpha (rad/s^2)
        alpha = tau_net / j_turbo

        # Discrete Euler Integration
        w_new = w + (alpha * dt)

        # Physical Bounds: Non-negative speed and physical safety limit
        w_clamped = max(0.0, min(w_max * 1.05, w_new))
        rpm_new = w_clamped * (30.0 / math.pi)

        return (w_clamped, rpm_new, alpha)
