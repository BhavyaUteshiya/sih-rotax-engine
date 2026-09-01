"""
Full Engine Thermodynamic Combustion, Metered Fuel System, Dynamic Turbo Closure, and 1st-Order Thermal Management Physics (Phase 3.8 Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Tuple


class ThermodynamicPhysicsError(ValueError):
    """Raised when numerical safety or physical boundary violations occur in thermodynamic physics."""
    pass


class ThermodynamicsCombustionModel:
    """
    Full Thermodynamic Engine Physics Model:
    Metered Fuel Delivery, AFR, Equivalence Ratio, Bounded Combustion Efficiency, Heat Release Energy Audit,
    Indicated Power/Torque, Exhaust Gas Enthalpy, Dynamic Turbocharger Shaft Acceleration & MAP emergence,
    1st-Order Thermal Differential Equations (CHT, Coolant, Oil, EGT), Thermal Derating Protection,
    and Aircraft Fuel Burn Weight Coupling.
    All calculations strictly use Canonical SI Units (m, kg/s, N, N*m, W, V, A, J, K, rad/s, m/s^2).
    """

    @classmethod
    def validate_inputs(
        cls,
        air_mass_flow_kg_s: float,
        ambient_temp_k: float,
        ambient_pressure_pa: float,
        dt_seconds: float
    ) -> None:
        """Validates numerical safety and physical bounds for thermodynamic inputs."""
        if math.isnan(air_mass_flow_kg_s) or math.isinf(air_mass_flow_kg_s) or air_mass_flow_kg_s < 0:
            raise ThermodynamicPhysicsError(f"Invalid intake air mass flow: {air_mass_flow_kg_s} kg/s.")

        if math.isnan(ambient_temp_k) or math.isinf(ambient_temp_k) or ambient_temp_k <= 0:
            raise ThermodynamicPhysicsError(f"Invalid ambient temperature: {ambient_temp_k} K.")

        if math.isnan(ambient_pressure_pa) or math.isinf(ambient_pressure_pa) or ambient_pressure_pa <= 0:
            raise ThermodynamicPhysicsError(f"Invalid ambient pressure: {ambient_pressure_pa} Pa.")

        if math.isnan(dt_seconds) or math.isinf(dt_seconds) or dt_seconds <= 0:
            raise ThermodynamicPhysicsError(f"Invalid simulation timestep dt: {dt_seconds} s.")

    @classmethod
    def compute_metered_fuel_flow(
        cls,
        throttle_percent: float,
        engine_speed_rpm: float,
        air_mass_flow_kg_s: float,
        operating_state_str: str = "RUNNING",
        max_fuel_flow_kg_h: float = 18.5,
        idle_fuel_flow_kg_h: float = 1.8,
        stoichiometric_afr: float = 14.7,
        thermal_derating_factor: float = 1.0,
        lower_heating_value_j_kg: float = 44000000.0
    ) -> Tuple[float, float, float]:
        """
        Rotax 914-style carbureted fuel metering.

        The throttle command changes throttle-valve opening and therefore the
        operating air/fuel demand; it does not command RPM directly.  For the
        prototype, the constant-depression carburetor is represented by a
        throttle/load-dependent target AFR with an air-mass-flow ceiling.
        """
        th = max(0.0, min(115.0, float(throttle_percent)))
        rpm = max(0.0, float(engine_speed_rpm))
        m_air = max(0.0, float(air_mass_flow_kg_s))
        m_max_h = max(0.1, float(max_fuel_flow_kg_h))
        m_idle_h = max(0.0, float(idle_fuel_flow_kg_h))
        stoich = max(1.0, float(stoichiometric_afr))
        derate = max(0.0, min(1.0, float(thermal_derating_factor)))
        lhv = max(1.0, float(lower_heating_value_j_kg))
        state = str(operating_state_str).upper()

        if state == "OFF" or rpm <= 1.0 and state == "OFF":
            return (0.0, 0.0, 0.0)

        if m_air <= 1e-9:
            return (0.0, 0.0, 0.0)

        load = th / 115.0
        # Full-load gasoline target is deliberately richer than stoichiometric.
        target_afr = max(11.8, stoich - 2.2 * load)
        # Metering increases nonlinearly with throttle position. This retains
        # monotonic throttle response while keeping the carbureted mixture in
        # a plausible gasoline operating region as airflow changes.
        metering_factor = 0.45 + 0.55 * load
        demand_h = (m_air / target_afr) * 3600.0 * metering_factor

        if state == "STARTING":
            # Priming/cranking fuel remains bounded; combustion must still be
            # produced by the crankshaft model rather than a direct RPM command.
            demand_h = min(demand_h, max(m_idle_h * 1.8, 3.0))
        else:
            demand_h = max(m_idle_h if rpm >= 900.0 else 0.0, demand_h)

        m_flow_h = min(m_max_h, demand_h)
        m_flow_actual_h = m_flow_h * derate
        m_flow_actual_kg_s = m_flow_actual_h / 3600.0
        p_fuel_w = m_flow_actual_kg_s * lhv
        return (m_flow_actual_kg_s, m_flow_actual_h, p_fuel_w)

    @classmethod
    def compute_afr_and_equivalence_ratio(
        cls,
        air_mass_flow_kg_s: float,
        fuel_mass_flow_kg_s: float,
        stoichiometric_afr: float = 14.5
    ) -> Tuple[float, float]:
        """
        Computes Air-Fuel Ratio (AFR) and Equivalence Ratio phi = AFR_stoich / AFR_actual:
        If fuel == 0: AFR = 999.9 (lean limit), phi = 0.0
        Returns Tuple of (air_fuel_ratio, equivalence_ratio).
        """
        m_air = max(0.0, float(air_mass_flow_kg_s))
        m_fuel = max(0.0, float(fuel_mass_flow_kg_s))
        stoich = float(stoichiometric_afr)

        if m_fuel <= 1e-9:
            return (999.9, 0.0)

        afr_actual = m_air / m_fuel
        phi = stoich / afr_actual if afr_actual > 0 else 0.0

        return (afr_actual, phi)

    @classmethod
    def ignition_timing_from_rpm(cls, engine_speed_rpm: float, idle_rpm: float = 1400.0, advance_rpm: float = 4900.0) -> float:
        """Approximate dual-CDI spark advance: ~4 deg BTDC at low RPM to ~26 deg at higher RPM."""
        rpm = max(0.0, float(engine_speed_rpm))
        if rpm <= idle_rpm:
            return 4.0
        if rpm >= advance_rpm:
            return 26.0
        return 4.0 + (26.0 - 4.0) * ((rpm - idle_rpm) / max(1.0, advance_rpm - idle_rpm))

    @classmethod
    def compute_combustion_efficiency(
        cls,
        equivalence_ratio: float,
        engine_speed_rpm: float,
        ring_wear: float = 0.0,
        injector_wear: float = 0.0,
        peak_combustion_efficiency: float = 0.95,
        ignition_timing_deg_btdc: float = 26.0,
        active_cdi_circuits: int = 2
    ) -> float:
        """Computes bounded gasoline combustion efficiency from mixture, spark timing and CDI redundancy."""
        phi = float(equivalence_ratio)
        eta_max = float(peak_combustion_efficiency)
        d_ring = max(0.0, min(1.0, float(ring_wear)))
        d_fuel = max(0.0, min(1.0, float(injector_wear)))
        cdi = max(0, min(2, int(active_cdi_circuits)))
        if phi <= 0.0 or cdi == 0:
            return 0.0

        # Gasoline operating region centered near phi ~= 1.0.
        eta_phi = math.exp(-3.0 * ((phi - 1.0) ** 2))
        timing_opt = cls.ignition_timing_from_rpm(engine_speed_rpm)
        timing_penalty = math.exp(-0.0008 * ((float(ignition_timing_deg_btdc) - timing_opt) ** 2))
        cdi_factor = 1.0 if cdi == 2 else 0.94
        eta_wear = max(0.5, 1.0 - 0.15 * d_ring - 0.10 * d_fuel)
        return max(0.0, min(1.0, eta_max * eta_phi * timing_penalty * cdi_factor * eta_wear))

    @classmethod
    def compute_heat_release_and_energy_audit(
        cls,
        fuel_energy_rate_w: float,
        combustion_efficiency: float,
        useful_indicated_work_fraction: float = 0.42,
        exhaust_energy_fraction: float = 0.35,
        wall_heat_transfer_fraction: float = 0.20
    ) -> Tuple[float, float, float, float, float]:
        """
        Partitioning total chemical heat release into useful mechanical work, exhaust energy, wall heat loss, and residual:
        P_heat = P_fuel * eta_comb
        P_ind = useful_fraction * P_heat
        P_exh = exhaust_fraction * P_heat
        Q_wall = wall_fraction * P_heat
        P_residual = (1.0 - useful - exhaust - wall) * P_heat
        Returns Tuple of (heat_release_rate_w, indicated_power_w, exhaust_energy_w, wall_heat_w, residual_power_w).
        """
        p_fuel = max(0.0, float(fuel_energy_rate_w))
        eta_comb = max(0.0, min(1.0, float(combustion_efficiency)))
        f_work = float(useful_indicated_work_fraction)
        f_exh = float(exhaust_energy_fraction)
        f_wall = float(wall_heat_transfer_fraction)

        p_heat = p_fuel * eta_comb
        p_ind = f_work * p_heat
        p_exh = f_exh * p_heat
        q_wall = f_wall * p_heat

        f_res = max(0.0, 1.0 - f_work - f_exh - f_wall)
        p_residual = f_res * p_heat

        return (p_heat, p_ind, p_exh, q_wall, p_residual)

    @classmethod
    def compute_indicated_torque(
        cls,
        indicated_power_w: float,
        engine_speed_rpm: float,
        min_cranking_rad_s: float = 15.0,
        max_indicated_torque_n_m: float = 550.0
    ) -> float:
        """
        Computes indicated combustion torque T_ind = P_ind / max(w_crank_min, w_eng) bounded by max_indicated_torque_n_m.
        Safely handles zero/low RPM without division by zero or infinite torque.
        """
        p_ind = max(0.0, float(indicated_power_w))
        rpm = max(0.0, float(engine_speed_rpm))
        w_min = float(min_cranking_rad_s)
        t_max = float(max_indicated_torque_n_m)

        if p_ind <= 0.0:
            return 0.0

        omega_eng = rpm * (math.pi / 30.0)
        omega = max(w_min, omega_eng)

        t_ind = min(t_max, p_ind / omega)
        return t_ind

    @classmethod
    def step_turbocharger_dynamics_and_map(
        cls,
        current_turbo_speed_rpm: float,
        exhaust_mass_flow_kg_s: float,
        exhaust_energy_rate_w: float,
        air_mass_flow_kg_s: float,
        ambient_pressure_pa: float,
        ambient_temp_k: float,
        dt_seconds: float,
        turbo_inertia_kg_m2: float = 0.00015,
        turbine_efficiency: float = 0.76,
        compressor_efficiency: float = 0.78,
        turbo_friction_coeff: float = 0.00005,
        max_turbo_speed_rpm: float = 140000.0,
        max_map_pa: float = 220000.0,
        cp_exh_j_kg_k: float = 1150.0,
        throttle_percent: float = 100.0,
        target_map_pa: float = 132000.0,
        turbo_lag_tau_s: float = 0.8
    ) -> Tuple[float, float, float, float, float, float, float]:
        """
        Integrates dynamic turbocharger shaft rotational acceleration:
        P_turbine = eta_turbine * P_exh_available
        P_compressor = m_dot_air * cp * (T_out - T_in)
        J_turbo * domega/dt = tau_turbine - tau_compressor - tau_friction
        Derives compressor pressure ratio Pi_c and dynamic MAP = min(max_map_pa, Pi_c * P_amb).
        Returns Tuple of (new_turbo_rpm, new_turbo_omega, turbine_power_w, compressor_power_w, turbine_torque_n_m, compressor_torque_n_m, map_pa).
        """
        n_turbo = max(0.0, float(current_turbo_speed_rpm))
        m_exh = max(0.0, float(exhaust_mass_flow_kg_s))
        p_exh = max(0.0, float(exhaust_energy_rate_w))
        m_air = max(0.0, float(air_mass_flow_kg_s))
        p_amb = float(ambient_pressure_pa)
        t_amb = float(ambient_temp_k)
        dt = float(dt_seconds)

        j_turbo = max(1e-6, float(turbo_inertia_kg_m2))
        eta_turb = float(turbine_efficiency)
        eta_comp = float(compressor_efficiency)
        c_fric = float(turbo_friction_coeff)
        n_max = float(max_turbo_speed_rpm)
        map_ceiling = float(max_map_pa)
        cp_exh = float(cp_exh_j_kg_k)

        # Rotax-style TCU target: normalized throttle selects a target MAP,
        # while the wastegate meters exhaust energy into the turbine.
        th_norm = max(0.0, min(1.0, float(throttle_percent) / 115.0))
        target_map = max(p_amb, min(map_ceiling, float(target_map_pa)))
        requested_map = p_amb + th_norm * max(0.0, target_map - p_amb)

        omega_turbo = n_turbo * (math.pi / 30.0)
        pi_c_est = 1.0 + max(0.0, (map_ceiling / max(p_amb, 1.0)) - 1.0) * ((n_turbo / n_max) ** 2) if n_max > 0 else 1.0
        pi_c_est = max(1.0, pi_c_est)
        t_comp_out = t_amb * (1.0 + (1.0 / max(0.1, eta_comp)) * ((pi_c_est ** 0.286) - 1.0))
        p_compressor = m_air * 1005.0 * max(0.0, t_comp_out - t_amb)

        # Error-based wastegate: close when MAP is below target, open when above it.
        current_map_est = min(map_ceiling, max(p_amb, pi_c_est * p_amb))
        map_error = requested_map - current_map_est
        wastegate_open = max(0.0, min(1.0, 0.50 - map_error / max(20000.0, 0.35 * target_map)))
        turbine_flow_fraction = 1.0 - wastegate_open
        p_turbine = p_exh * eta_turb * turbine_flow_fraction

        p_compressor = min(p_turbine * 1.2 + 50.0, p_compressor)
        w_min = 100.0
        w_eval = max(w_min, omega_turbo)
        t_turbine = p_turbine / w_eval
        t_compressor = p_compressor / w_eval
        t_friction = c_fric * omega_turbo

        alpha_turbo = (t_turbine - t_compressor - t_friction) / j_turbo
        omega_turbo_new = max(0.0, omega_turbo + alpha_turbo * dt)
        n_turbo_new = min(n_max, omega_turbo_new * (30.0 / math.pi))

        # First-order MAP response preserves the estimated 0.5–1.5 s turbo lag.
        pi_c_new = 1.0 + max(0.0, (map_ceiling / max(p_amb, 1.0)) - 1.0) * ((n_turbo_new / n_max) ** 2) if n_max > 0 else 1.0
        raw_map = min(map_ceiling, max(p_amb, pi_c_new * p_amb))
        tau_map = max(0.1, float(turbo_lag_tau_s))
        alpha_map = min(1.0, dt / tau_map)
        map_emergent = current_map_est + alpha_map * (raw_map - current_map_est)
        map_emergent = max(p_amb, min(map_ceiling, map_emergent))

        return (n_turbo_new, omega_turbo_new, p_turbine, p_compressor, t_turbine, t_compressor, map_emergent)

    @classmethod
    def step_engine_thermal_management(
        cls,
        current_cht_k: float,
        current_coolant_k: float,
        current_oil_k: float,
        current_egt_k: float,
        wall_heat_generation_w: float,
        exhaust_energy_rate_w: float,
        friction_heat_w: float,
        airspeed_m_s: float,
        ambient_temp_k: float,
        dt_seconds: float,
        exhaust_mass_flow_kg_s: float = 0.0,
        exhaust_specific_heat_j_kg_k: float = 1150.0,
        head_mass_kg: float = 12.0,
        head_cp_j_kg_k: float = 890.0,
        coolant_mass_kg: float = 8.0,
        coolant_cp_j_kg_k: float = 3800.0,
        oil_mass_kg: float = 4.0,
        oil_cp_j_kg_k: float = 2100.0,
        max_safe_cht_k: float = 523.15,
        max_safe_egt_k: float = 1123.15,
        max_safe_oil_k: float = 413.15
    ) -> Tuple[float, float, float, float, float]:
        """
        Integrates 1st-order dynamic thermal differential equations for CHT, Coolant, Oil, EGT,
        and computes thermal derating protection factor in [0.0, 1.0].
        Returns Tuple of (new_cht_k, new_coolant_k, new_oil_k, new_egt_k, thermal_derating_factor).
        """
        cht = max(ambient_temp_k, float(current_cht_k))
        coolant = max(ambient_temp_k, float(current_coolant_k))
        oil = max(ambient_temp_k, float(current_oil_k))
        egt = max(ambient_temp_k, float(current_egt_k))

        q_wall = max(0.0, float(wall_heat_generation_w))
        p_exh = max(0.0, float(exhaust_energy_rate_w))
        q_fric = max(0.0, float(friction_heat_w))
        v_inf = max(0.0, float(airspeed_m_s))
        t_amb = float(ambient_temp_k)
        dt = float(dt_seconds)

        # Convective cooling coefficients
        h_cool = 45.0 + 8.0 * (v_inf ** 0.8)  # Convective ram-air coefficient
        k_rad = 80.0                          # Radiator heat rejection coefficient (W/K)
        k_oil_cool = 35.0                     # Oil cooler heat rejection coefficient (W/K)

        # 1. CHT Integration: m_head * Cp_head * dCHT/dt = Q_wall - h_cool * S_cool * (CHT - Coolant)
        q_rej_cht = h_cool * 0.85 * max(0.0, cht - coolant)
        dcht_dt = (q_wall - q_rej_cht) / (head_mass_kg * head_cp_j_kg_k)
        new_cht = max(t_amb, cht + dcht_dt * dt)

        # 2. Coolant Integration: m_cool * Cp_cool * dT_cool/dt = Q_rej_cht - k_rad * (Coolant - T_amb)
        q_rej_rad = k_rad * max(0.0, coolant - t_amb)
        dcoolant_dt = (q_rej_cht - q_rej_rad) / (coolant_mass_kg * coolant_cp_j_kg_k)
        new_coolant = max(t_amb, coolant + dcoolant_dt * dt)

        # 3. Oil Integration: m_oil * Cp_oil * dT_oil/dt = Q_fric + 0.10*Q_wall - k_oil_cool * (Oil - T_amb)
        q_oil_in = q_fric + 0.10 * q_wall
        q_oil_out = k_oil_cool * max(0.0, oil - t_amb)
        doil_dt = (q_oil_in - q_oil_out) / (oil_mass_kg * oil_cp_j_kg_k)
        new_oil = max(t_amb, oil + doil_dt * dt)

        # 4. Dynamic EGT Target & Integration. The target follows the
        # exhaust energy balance rather than a direct throttle→temperature map.
        m_exh_input = float(exhaust_mass_flow_kg_s)
        cp_exh = max(1.0, float(exhaust_specific_heat_j_kg_k))
        if m_exh_input > 1e-6:
            exhaust_delta_t = p_exh / (m_exh_input * cp_exh)
            t_exh_target = t_amb + 1.35 * max(0.0, exhaust_delta_t)
            t_exh_target = min(1173.15, max(t_amb, t_exh_target))
        else:
            # Backward-compatible analytical fallback for direct unit tests /
            # standalone calls that do not provide exhaust mass flow.
            t_exh_target = t_amb + p_exh / max(1.0, 0.03 * cp_exh)
            t_exh_target = max(t_amb, t_exh_target)
        degt_dt = (t_exh_target - egt) / 0.5
        new_egt = max(t_amb, egt + degt_dt * dt)

        # 5. Thermal Derating Protection Factor (1.0 = normal, < 1.0 = derated)
        derate_cht = max(0.30, 1.0 - 0.02 * max(0.0, new_cht - max_safe_cht_k))
        derate_egt = max(0.30, 1.0 - 0.01 * max(0.0, new_egt - max_safe_egt_k))
        derate_oil = max(0.30, 1.0 - 0.02 * max(0.0, new_oil - max_safe_oil_k))

        thermal_derating_factor = min(derate_cht, min(derate_egt, derate_oil))

        return (new_cht, new_coolant, new_oil, new_egt, thermal_derating_factor)
