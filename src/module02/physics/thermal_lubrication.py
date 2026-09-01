"""
Module 02 Dynamic CHT Thermal, EGT, Oil Sump & Temperature-Dependent Viscosity Subsystem (Phase 3.5 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Tuple


class ThermalLubricationPhysicsError(ValueError):
    """Raised when numerical safety or physical boundary violations occur in thermal or lubrication physics."""
    pass


class ThermalLubricationModel:
    """
    Physically Coupled Lumped Thermal Mass, Dynamic EGT, Oil Sump Energy Balance, Vogel Viscosity,
    and Viscosity-Modified Friction Physics Subsystem.
    All calculations strictly use Canonical SI Units (Kelvin, kg, J/(kg K), W, rad/s, N*m, Pa*s).
    """

    @classmethod
    def validate_inputs(
        cls,
        cylinder_thermal_mass_kg: float,
        cylinder_specific_heat_j_kg_k: float,
        oil_mass_kg: float,
        oil_specific_heat_j_kg_k: float,
        dt_seconds: float
    ) -> None:
        """Validates numerical safety and physical bounds for thermal and lubrication inputs."""
        if math.isnan(cylinder_thermal_mass_kg) or math.isinf(cylinder_thermal_mass_kg) or cylinder_thermal_mass_kg <= 0:
            raise ThermalLubricationPhysicsError(f"Invalid cylinder thermal mass: {cylinder_thermal_mass_kg} kg.")

        if math.isnan(cylinder_specific_heat_j_kg_k) or math.isinf(cylinder_specific_heat_j_kg_k) or cylinder_specific_heat_j_kg_k <= 0:
            raise ThermalLubricationPhysicsError(f"Invalid cylinder specific heat: {cylinder_specific_heat_j_kg_k} J/(kg K).")

        if math.isnan(oil_mass_kg) or math.isinf(oil_mass_kg) or oil_mass_kg <= 0:
            raise ThermalLubricationPhysicsError(f"Invalid oil mass: {oil_mass_kg} kg.")

        if math.isnan(oil_specific_heat_j_kg_k) or math.isinf(oil_specific_heat_j_kg_k) or oil_specific_heat_j_kg_k <= 0:
            raise ThermalLubricationPhysicsError(f"Invalid oil specific heat: {oil_specific_heat_j_kg_k} J/(kg K).")

        if math.isnan(dt_seconds) or math.isinf(dt_seconds) or dt_seconds <= 0:
            raise ThermalLubricationPhysicsError(f"Invalid simulation timestep dt: {dt_seconds} s.")

    @classmethod
    def compute_heat_partition(
        cls,
        fuel_energy_rate_w: float,
        indicated_power_w: float,
        exhaust_energy_rate_w: float,
        wall_heat_fraction: float = 0.25
    ) -> Tuple[float, float]:
        """
        Partitions fuel chemical heat release into cylinder wall heat transfer Q_wall and unburned/coolant losses:
        Q_fuel >= P_ind + Q_exhaust + Q_wall + Q_loss
        Returns Tuple of (wall_heat_generation_w, loss_heat_rate_w).
        """
        q_fuel = float(fuel_energy_rate_w)
        p_ind = float(indicated_power_w)
        q_exh = float(exhaust_energy_rate_w)
        f_wall = float(wall_heat_fraction)

        if q_fuel < 0 or p_ind < 0 or q_exh < 0:
            raise ThermalLubricationPhysicsError("Heat rates cannot be negative.")

        if q_fuel <= 1e-7:
            return (0.0, 0.0)

        # Cylinder Wall Heat Transfer Rate (W)
        q_avail = max(0.0, q_fuel - p_ind - q_exh)
        q_wall = min(q_avail, f_wall * q_fuel)

        # Remaining Unburned / Radiation Losses
        q_loss = max(0.0, q_avail - q_wall)

        return (q_wall, q_loss)

    @classmethod
    def step_cht_and_cooling(
        cls,
        current_cht_k: float,
        wall_heat_generation_w: float,
        ambient_temp_k: float,
        airspeed_m_s: float,
        engine_rpm: float,
        cylinder_thermal_mass_kg: float,
        cylinder_specific_heat_j_kg_k: float,
        cooling_surface_area_m2: float = 0.85,
        cooling_coeff_base_w_m2_k: float = 45.0,
        dt_seconds: float = 0.01
    ) -> Tuple[float, float, float]:
        """
        Integrates dynamic cylinder head thermal differential equation:
        m_cyl * Cp_cyl * d(T_CHT)/dt = Q_wall - Q_cooling
        Q_cooling = h_cool * A_cyl * max(0.0, T_CHT - T_amb)
        Returns Tuple of (new_cht_k, cooling_heat_rejection_w, dcht_dt).
        """
        cht = float(current_cht_k)
        q_wall = float(wall_heat_generation_w)
        t_amb = float(ambient_temp_k)
        v_inf = max(0.0, float(airspeed_m_s))
        rpm = max(0.0, float(engine_rpm))
        m_cyl = float(cylinder_thermal_mass_kg)
        cp_cyl = float(cylinder_specific_heat_j_kg_k)
        a_cyl = float(cooling_surface_area_m2)
        h_base = float(cooling_coeff_base_w_m2_k)
        dt = float(dt_seconds)

        if cht <= 0 or t_amb <= 0:
            raise ThermalLubricationPhysicsError("Temperatures must be positive Kelvin values.")

        # Convective Cooling Heat Transfer Coefficient (scales with airspeed and engine fan speed)
        h_cool = h_base * (1.0 + (0.05 * (v_inf / 10.0)) + (0.02 * (rpm / 1000.0)))

        # Cooling Heat Rejection Rate (W)
        q_cooling = max(0.0, h_cool * a_cyl * (cht - t_amb))

        # Net Thermal Energy Balance
        q_net = q_wall - q_cooling

        # Derivative dT_CHT/dt (K/s)
        dcht_dt = q_net / (m_cyl * cp_cyl)

        # Euler Integration step
        cht_new = max(t_amb, cht + (dcht_dt * dt))

        return (cht_new, q_cooling, dcht_dt)

    @classmethod
    def compute_dynamic_egt(
        cls,
        current_egt_k: float,
        exhaust_temp_k: float,
        egt_sensor_time_constant_sec: float = 0.5,
        dt_seconds: float = 0.01
    ) -> float:
        """
        Computes dynamic thermocouple Exhaust Gas Temperature (EGT) via first-order lag response:
        d(T_EGT)/dt = (T_exhaust - T_EGT) / tau_EGT
        """
        egt = float(current_egt_k)
        t_exh = float(exhaust_temp_k)
        tau = max(0.05, float(egt_sensor_time_constant_sec))
        dt = float(dt_seconds)

        degt_dt = (t_exh - egt) / tau
        egt_new = max(200.0, egt + (degt_dt * dt))

        return egt_new

    @classmethod
    def step_oil_temperature(
        cls,
        current_oil_temp_k: float,
        current_cht_k: float,
        friction_power_w: float,
        ambient_temp_k: float,
        oil_mass_kg: float,
        oil_specific_heat_j_kg_k: float,
        oil_cooler_coeff_w_k: float = 35.0,
        dt_seconds: float = 0.01
    ) -> Tuple[float, float, float]:
        """
        Integrates dynamic oil sump thermal differential equation:
        m_oil * Cp_oil * d(T_oil)/dt = Q_oil_gen - Q_oil_cool
        Q_oil_gen = (0.75 * P_friction) + 0.02 * max(0.0, T_CHT - T_oil)
        Q_oil_cool = h_oil_cooler * max(0.0, T_oil - T_amb)
        Returns Tuple of (new_oil_temp_k, oil_heat_generation_w, oil_heat_rejection_w).
        """
        t_oil = float(current_oil_temp_k)
        t_cht = float(current_cht_k)
        p_fric = max(0.0, float(friction_power_w))
        t_amb = float(ambient_temp_k)
        m_oil = float(oil_mass_kg)
        cp_oil = float(oil_specific_heat_j_kg_k)
        h_cooler = float(oil_cooler_coeff_w_k)
        dt = float(dt_seconds)

        if t_oil <= 0 or t_amb <= 0:
            raise ThermalLubricationPhysicsError("Oil and ambient temperatures must be positive Kelvin values.")

        # Oil Heat Generation Rate (W)
        q_oil_gen = (0.75 * p_fric) + (0.02 * max(0.0, t_cht - t_oil))

        # Oil Cooler Heat Rejection Rate (W)
        q_oil_cool = max(0.0, h_cooler * (t_oil - t_amb))

        # Net Energy Balance & Derivative dT_oil/dt (K/s)
        q_net_oil = q_oil_gen - q_oil_cool
        dtoil_dt = q_net_oil / (m_oil * cp_oil)

        # Integration Step
        t_oil_new = max(t_amb, t_oil + (dtoil_dt * dt))

        return (t_oil_new, q_oil_gen, q_oil_cool)

    @classmethod
    def compute_oil_viscosity(
        cls,
        oil_temperature_k: float,
        reference_oil_temperature_k: float = 373.15,
        reference_viscosity_pa_s: float = 0.012,
        viscosity_temperature_coeff_k: float = 3800.0
    ) -> float:
        """
        Computes dynamic oil viscosity mu(T_oil) via Vogel / Arrhenius viscosity-temperature relation:
        mu(T_oil) = mu_ref * exp( B_visc * [ (1 / T_oil) - (1 / T_ref) ] )  (Pa*s)
        Cold oil (low T) -> High viscosity mu.
        Hot oil (high T) -> Low viscosity mu.
        Returns oil_viscosity_pa_s.
        """
        t_oil = float(oil_temperature_k)
        t_ref = float(reference_oil_temperature_k)
        mu_ref = float(reference_viscosity_pa_s)
        b_visc = float(viscosity_temperature_coeff_k)

        if t_oil <= 0 or t_ref <= 0 or mu_ref <= 0:
            raise ThermalLubricationPhysicsError("Viscosity model parameters must be positive.")

        exponent = b_visc * ((1.0 / t_oil) - (1.0 / t_ref))
        mu_raw = mu_ref * math.exp(exponent)

        # Bounded between 0.003 Pa*s (hot oil floor) and 0.50 Pa*s (cold oil ceiling)
        return max(0.003, min(0.50, mu_raw))

    @classmethod
    def compute_viscosity_modified_friction_torque(
        cls,
        engine_rpm: float,
        oil_viscosity_pa_s: float,
        friction_static_n_m: float,
        friction_viscous_n_m_s_rad: float,
        friction_hydrodynamic_n_m_s2_rad2: float,
        reference_viscosity_pa_s: float = 0.012
    ) -> Tuple[float, float]:
        """
        Couples oil viscosity mu into viscous component of engine mechanical friction torque:
        k_mu = mu(T_oil) / mu_ref
        T_fric = T_static * tanh(10 * omega) + c_viscous * k_mu * omega + c_hydro * omega^2
        Returns Tuple of (total_friction_torque_n_m, viscosity_contribution_n_m).
        """
        rpm = max(0.0, float(engine_rpm))
        mu_oil = float(oil_viscosity_pa_s)
        t_stat = float(friction_static_n_m)
        c_visc = float(friction_viscous_n_m_s_rad)
        c_hydro = float(friction_hydrodynamic_n_m_s2_rad2)
        mu_ref = float(reference_viscosity_pa_s)

        omega = rpm * (math.pi / 30.0)
        if omega <= 1e-4:
            return (0.0, 0.0)

        # Viscosity Multiplier relative to 100°C Reference Viscosity
        k_mu = max(0.2, min(10.0, mu_oil / max(1e-4, mu_ref)))

        # Viscosity-Dependent Viscous Friction Component (N*m)
        t_fric_visc = c_visc * k_mu * omega

        # Static Coulomb Component (N*m)
        t_fric_stat = t_stat * math.tanh(10.0 * omega)

        # Hydrodynamic Quadratic Component (N*m)
        t_fric_hydro = c_hydro * omega * omega

        t_fric_total = t_fric_stat + t_fric_visc + t_fric_hydro
        return (t_fric_total, t_fric_visc)
