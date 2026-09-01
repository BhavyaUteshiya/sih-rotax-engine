"""
Module 02 Hardened Fuel Delivery, AFR, Combustion & Exhaust Energy Subsystem (Phase 3.3.1 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Optional, Tuple
from src.module02.models.enums import EngineOperatingState


class CombustionPhysicsError(ValueError):
    """Raised when numerical safety or physical boundary violations occur in combustion physics."""
    pass


class CombustionModel:
    """
    Fuel Delivery, Air-Fuel Ratio (AFR), Heat-Release Combustion, Indicated Torque, and Exhaust Energy Subsystem.
    All calculations strictly use Canonical SI Units (kg/s, W, rad/s, J/kg, Kelvin, N*m).
    Eliminates low-RPM torque singularities via 4-stroke cycle energy formulation W_cycle.
    """

    EXHAUST_SPECIFIC_HEAT_J_KG_K: float = 1150.0 # Cp_exh (J/(kg K)) for diesel exhaust gas

    @classmethod
    def validate_inputs(
        cls,
        throttle_percent: float,
        idle_fuel_flow_kg_h: float,
        max_fuel_flow_kg_h: float,
        lhv_j_kg: float
    ) -> None:
        """Validates numerical safety and physical bounds for fuel delivery inputs."""
        if math.isnan(throttle_percent) or math.isinf(throttle_percent):
            raise CombustionPhysicsError(f"Invalid throttle input: {throttle_percent}.")

        if math.isnan(idle_fuel_flow_kg_h) or math.isinf(idle_fuel_flow_kg_h) or idle_fuel_flow_kg_h < 0:
            raise CombustionPhysicsError(f"Invalid idle fuel flow: {idle_fuel_flow_kg_h} kg/h.")

        if math.isnan(max_fuel_flow_kg_h) or math.isinf(max_fuel_flow_kg_h) or max_fuel_flow_kg_h <= idle_fuel_flow_kg_h:
            raise CombustionPhysicsError(f"Invalid max fuel flow: {max_fuel_flow_kg_h} kg/h. Must exceed idle fuel flow.")

        if math.isnan(lhv_j_kg) or math.isinf(lhv_j_kg) or lhv_j_kg <= 0:
            raise CombustionPhysicsError(f"Invalid fuel LHV: {lhv_j_kg} J/kg.")

    @classmethod
    def determine_operating_state(
        cls,
        engine_rpm: float,
        throttle_percent: float,
        starter_active: bool = False,
        idle_rpm: float = 1400.0
    ) -> EngineOperatingState:
        """
        Determines deterministic engine operating state based on speed, starter, and throttle:
        - OFF: RPM < 50.0 and starter inactive
        - STARTING: starter active or 50 <= RPM < 600
        - IDLE: 600 <= RPM < idle_rpm + 200 and throttle <= 1.0%
        - RUNNING: RPM >= idle_rpm or self-sustaining running
        """
        rpm = max(0.0, float(engine_rpm))
        th = max(0.0, float(throttle_percent))

        if starter_active or (50.0 <= rpm < 600.0):
            return EngineOperatingState.STARTING
        elif rpm < 50.0 and th <= 0.0:
            return EngineOperatingState.OFF
        elif rpm < (idle_rpm + 200.0) and th <= 1.0:
            return EngineOperatingState.IDLE
        else:
            return EngineOperatingState.RUNNING

    @classmethod
    def compute_fuel_mass_flow(
        cls,
        throttle_percent: float,
        air_mass_flow_kg_s: float,
        engine_rpm: float,
        idle_fuel_flow_kg_h: float,
        max_fuel_flow_kg_h: float,
        lower_heating_value_j_kg: float,
        operating_state: EngineOperatingState = EngineOperatingState.RUNNING,
        stoichiometric_afr: float = 14.5,
        smoke_limit_phi: float = 1.05
    ) -> Tuple[float, float, float]:
        """
        Computes fuel mass delivery flow rate constrained by FADEC smoke limiter / air availability:
        m_dot_fuel_demand = idle_fuel_flow + (throttle / 100.0) * (max_fuel_flow - idle_fuel_flow)
        m_dot_fuel_max_air = (m_dot_air * smoke_limit_phi) / stoichiometric_afr
        m_dot_fuel_actual = min(m_dot_fuel_demand, m_dot_fuel_max_air)
        Q_fuel_w = m_dot_fuel_actual_kg_s * LHV
        Returns Tuple of (m_dot_fuel_kg_s, m_dot_fuel_kg_h, Q_fuel_energy_rate_w).
        """
        cls.validate_inputs(throttle_percent, idle_fuel_flow_kg_h, max_fuel_flow_kg_h, lower_heating_value_j_kg)

        th = max(0.0, min(100.0, float(throttle_percent)))
        f_idle = float(idle_fuel_flow_kg_h)
        f_max = float(max_fuel_flow_kg_h)
        lhv = float(lower_heating_value_j_kg)
        m_air = max(0.0, float(air_mass_flow_kg_s))
        rpm = max(0.0, float(engine_rpm))

        # 1. Engine OFF State => Zero Fuel
        if operating_state == EngineOperatingState.OFF or (rpm < 50.0 and th <= 0.0 and not (operating_state == EngineOperatingState.STARTING)):
            return (0.0, 0.0, 0.0)

        # 2. STARTING State => Cranking Fuel Schedule (Proportional to cranking RPM)
        if operating_state == EngineOperatingState.STARTING:
            if rpm < 50.0:
                return (0.0, 0.0, 0.0)
            f_starting_h = min(f_idle * 1.2, max(0.5, (rpm / 600.0) * f_idle))
            m_s = f_starting_h / 3600.0
            return (m_s, f_starting_h, m_s * lhv)

        # 3. RUNNING / IDLE State => Throttle Demand
        f_demand_h = f_idle + ((th / 100.0) * (f_max - f_idle))
        f_demand_s = f_demand_h / 3600.0

        # FADEC Air-Availability Smoke Limiter
        if m_air > 0:
            m_fuel_max_air_s = (m_air * float(smoke_limit_phi)) / float(stoichiometric_afr)
            m_actual_s = min(f_demand_s, max(f_idle / 3600.0, m_fuel_max_air_s))
        else:
            m_actual_s = min(f_demand_s, f_idle / 3600.0)

        m_actual_h = m_actual_s * 3600.0
        q_fuel_w = m_actual_s * lhv

        return (m_actual_s, m_actual_h, q_fuel_w)

    @classmethod
    def compute_air_fuel_ratio(
        cls,
        air_mass_flow_kg_s: float,
        fuel_mass_flow_kg_s: float,
        stoichiometric_afr: float = 14.5
    ) -> Tuple[Optional[float], float]:
        """
        Computes Air-Fuel Ratio (AFR) and Equivalence Ratio phi:
        AFR = m_dot_air / m_dot_fuel
        phi = stoichiometric_afr / AFR = (m_dot_fuel * stoichiometric_afr) / m_dot_air
        For zero fuel: AFR is float('nan') / None and phi = 0.0 (never fake 500.0).
        """
        m_air = float(air_mass_flow_kg_s)
        m_fuel = float(fuel_mass_flow_kg_s)
        afr_stoich = float(stoichiometric_afr)

        if math.isnan(m_air) or math.isinf(m_air) or m_air < 0:
            raise CombustionPhysicsError(f"Invalid air mass flow: {air_mass_flow_kg_s} kg/s.")

        if math.isnan(m_fuel) or math.isinf(m_fuel) or m_fuel < 0:
            raise CombustionPhysicsError(f"Invalid fuel mass flow: {fuel_mass_flow_kg_s} kg/s.")

        if afr_stoich <= 0:
            raise CombustionPhysicsError(f"Invalid stoichiometric AFR: {stoichiometric_afr}.")

        if m_fuel <= 1e-7:
            # Zero fuel condition: AFR is non-operating / None, phi = 0.0
            return (None, 0.0)

        if m_air <= 1e-7:
            # Zero air condition
            afr = 0.0
            phi = 99.0
            return (afr, phi)

        afr = m_air / m_fuel
        phi = afr_stoich / afr
        return (afr, phi)

    @classmethod
    def compute_combustion_efficiency(
        cls,
        equivalence_ratio_phi: float,
        injection_timing_deg_btdc: float,
        optimal_injection_timing_deg_btdc: float,
        peak_combustion_efficiency: float,
        injection_timing_sensitivity: float = 0.0005
    ) -> Tuple[float, float, float]:
        """
        Computes total combustion heat-release efficiency eta_comb:
        eta_comb = peak_combustion_efficiency * eta_phi * eta_timing
        Returns Tuple of (eta_comb, eta_phi, eta_timing).
        """
        phi = float(equivalence_ratio_phi)
        inj = float(injection_timing_deg_btdc)
        inj_opt = float(optimal_injection_timing_deg_btdc)
        eta_peak = float(peak_combustion_efficiency)
        sens = float(injection_timing_sensitivity)

        if math.isnan(phi) or math.isinf(phi) or phi < 0:
            raise CombustionPhysicsError(f"Invalid equivalence ratio phi: {equivalence_ratio_phi}.")

        if math.isnan(inj) or math.isinf(inj):
            raise CombustionPhysicsError(f"Invalid injection timing: {injection_timing_deg_btdc}.")

        if phi <= 0.0:
            # Fuel-off zero fuel condition
            return (0.0, 0.0, 1.0)

        # 1. Injection Timing Penalty
        timing_dev = inj - inj_opt
        eta_timing = max(0.70, min(1.0, 1.0 - (sens * (timing_dev * timing_dev))))

        # 2. Equivalence Ratio Combustion Efficiency (Diesel lean-burn characterization)
        if phi < 0.15:
            # Lean misfire limit region
            eta_phi = max(0.1, (phi / 0.15) * 0.80)
        elif phi <= 0.85:
            # Optimal diesel lean-burn operating region (phi ~ 0.2 to 0.7)
            eta_phi = 1.0 - 0.20 * math.pow(phi - 0.50, 2)
        else:
            # Air-deficient / soot limit rich region (phi > 0.85)
            eta_phi = max(0.40, 1.0 - 0.50 * (phi - 0.85))

        eta_comb = max(0.0, min(0.98, eta_peak * eta_phi * eta_timing))
        return (eta_comb, eta_phi, eta_timing)

    @classmethod
    def compute_indicated_power_and_torque(
        cls,
        fuel_mass_flow_kg_s: float,
        lower_heating_value_j_kg: float,
        combustion_efficiency: float,
        indicated_efficiency_peak: float,
        omega_rad_per_sec: float
    ) -> Tuple[float, float]:
        """
        Solves indicated thermodynamic combustion power P_ind and indicated crankshaft torque T_ind
        via 4-stroke cycle work formulation:
        P_ind = eta_comb * eta_ind_peak * m_dot_fuel * LHV  (Watts)
        W_cycle = P_ind / (RPM / 120.0)  (Joules/cycle)
        T_ind = W_cycle / (4 * pi)  (N*m)

        At any speed, T_ind is bounded by work per cycle W_cycle / (4*pi), cleanly eliminating low-RPM torque singularities!
        Returns Tuple of (p_indicated_w, t_indicated_n_m).
        """
        m_fuel = float(fuel_mass_flow_kg_s)
        lhv = float(lower_heating_value_j_kg)
        eta_comb = float(combustion_efficiency)
        eta_ind = float(indicated_efficiency_peak)
        omega = float(omega_rad_per_sec)

        if m_fuel < 0 or lhv <= 0 or eta_comb < 0 or eta_ind <= 0:
            raise CombustionPhysicsError("Physical parameters for power calculation must be positive.")

        if m_fuel <= 1e-7:
            return (0.0, 0.0)

        # Indicated Power (W)
        p_ind_w = eta_comb * eta_ind * m_fuel * lhv

        # Indicated Crankshaft Torque (N*m) via Cycle Work Formulation
        w_abs = abs(omega)
        rpm = w_abs * (30.0 / math.pi)

        if rpm < 50.0:
            # Standstill floor
            t_ind_n_m = 0.0
        else:
            # 4-stroke cycle frequency f_cycle = RPM / 120.0 (cycles/sec)
            cycles_per_sec = rpm / 120.0
            w_cycle = p_ind_w / cycles_per_sec
            t_ind_n_m = w_cycle / (4.0 * math.pi)

        return (p_ind_w, t_ind_n_m)

    @classmethod
    def compute_exhaust_flow_and_energy(
        cls,
        air_mass_flow_kg_s: float,
        fuel_mass_flow_kg_s: float,
        fuel_energy_rate_w: float,
        combustion_efficiency: float,
        intake_temp_k: float,
        ambient_temp_k: float,
        exhaust_heat_fraction: float = 0.40
    ) -> Tuple[float, float, float, float]:
        """
        Solves exhaust gas mass flow rate, temperature, specific enthalpy, and energy rate available for Phase 3.4 Turbocharger Turbine:
        m_dot_exh = m_dot_air + m_dot_fuel  (kg/s)
        Q_exh = exhaust_heat_fraction * eta_comb * Q_fuel  (W)
        T_exh = T_intake + Q_exh / (m_dot_exh * Cp_exh)  (K)
        h_exh = Cp_exh * (T_exh - T_ambient)  (J/kg)
        E_dot_exh = m_dot_exh * h_exh  (W)
        Returns Tuple of (m_dot_exh_kg_s, T_exh_k, h_exh_j_kg, E_dot_exh_w).
        """
        m_air = float(air_mass_flow_kg_s)
        m_fuel = float(fuel_mass_flow_kg_s)
        q_fuel = float(fuel_energy_rate_w)
        eta_comb = float(combustion_efficiency)
        t_in = float(intake_temp_k)
        t_amb = float(ambient_temp_k)
        f_exh = float(exhaust_heat_fraction)

        if m_air < 0 or m_fuel < 0 or t_in <= 0 or t_amb <= 0:
            raise CombustionPhysicsError("Invalid mass flow or temperature inputs for exhaust model.")

        # Exhaust Mass Flow Rate
        m_exh = m_air + m_fuel

        if m_exh <= 1e-7 or m_fuel <= 1e-7:
            # Standstill / fuel-off floor: Temperature equals intake temperature
            return (m_exh, t_in, 0.0, 0.0)

        # Thermal Energy Delivered to Exhaust Gas
        q_exh = max(0.0, f_exh * eta_comb * q_fuel)

        # Exhaust Temperature Rise
        delta_t = q_exh / (m_exh * cls.EXHAUST_SPECIFIC_HEAT_J_KG_K)
        t_exh = t_in + delta_t

        # Specific Exhaust Enthalpy relative to Ambient
        h_exh = cls.EXHAUST_SPECIFIC_HEAT_J_KG_K * max(0.0, t_exh - t_amb)

        # Exhaust Thermal Energy Rate
        e_exh_w = m_exh * h_exh

        return (m_exh, t_exh, h_exh, e_exh_w)
