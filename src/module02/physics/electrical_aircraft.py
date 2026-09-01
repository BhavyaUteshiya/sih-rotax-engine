"""
Module 02 Electrical Subsystem, Battery SOC, Starter Motor, and 3-DOF Aircraft Longitudinal Dynamics Physics (Phase 3.7 Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Dict, List, Tuple


class ElectricalAircraftError(ValueError):
    """Raised when numerical safety or physical boundary violations occur in electrical or aircraft physics."""
    pass


class ElectricalAircraftModel:
    """
    Electrical Power Balance, Alternator Mechanical Shaft Coupling, Battery SOC Integration,
    Starter Motor Dynamics, and 3-DOF Aircraft Longitudinal Flight Dynamics Subsystem.
    All calculations strictly use Canonical SI Units (m, kg/m^3, N, N*m, W, V, A, J, rad/s, m/s^2).
    """

    @classmethod
    def validate_inputs(
        cls,
        bus_voltage_v: float,
        dt_seconds: float,
        gross_mass_kg: float = 1800.0,
        wing_area_m2: float = 22.5,
        drag_coeff_cd0: float = 0.025
    ) -> None:
        """Validates numerical safety and physical bounds for electrical and aircraft inputs."""
        if math.isnan(bus_voltage_v) or math.isinf(bus_voltage_v) or bus_voltage_v <= 0:
            raise ElectricalAircraftError(f"Invalid electrical bus voltage: {bus_voltage_v} V.")

        if math.isnan(dt_seconds) or math.isinf(dt_seconds) or dt_seconds <= 0:
            raise ElectricalAircraftError(f"Invalid simulation timestep dt: {dt_seconds} s.")

        if math.isnan(gross_mass_kg) or math.isinf(gross_mass_kg) or gross_mass_kg <= 0:
            raise ElectricalAircraftError(f"Invalid aircraft mass: {gross_mass_kg} kg.")

        if math.isnan(wing_area_m2) or math.isinf(wing_area_m2) or wing_area_m2 <= 0:
            raise ElectricalAircraftError(f"Invalid wing area: {wing_area_m2} m^2.")

        if math.isnan(drag_coeff_cd0) or math.isinf(drag_coeff_cd0) or drag_coeff_cd0 < 0:
            raise ElectricalAircraftError(f"Invalid drag coefficient CD0: {drag_coeff_cd0}.")

    @classmethod
    def compute_alternator_output_and_shaft_load(
        cls,
        engine_rpm: float,
        bus_voltage_v: float = 28.0,
        electrical_load_w: float = 800.0,
        max_current_a: float = 75.0,
        alternator_efficiency: float = 0.85,
        cutin_rpm: float = 1000.0
    ) -> Tuple[float, float, float, float]:
        """
        Computes alternator electrical current generation, power output, and mechanical shaft load torque reflected to engine:
        If N_eng < cutin_rpm: I_alt = 0, P_alt = 0, T_alt = 0
        Else:
          I_alt = min(max_current_a, electrical_load_w / bus_voltage_v)
          P_alt_elec = bus_voltage_v * I_alt (W)
          P_alt_mech = P_alt_elec / alternator_efficiency (W)
          T_alt = P_alt_mech / omega_eng (N*m) (safely zero near zero RPM)
        Returns Tuple of (alternator_current_a, alternator_power_w, alternator_mech_power_w, alternator_torque_n_m).
        """
        rpm = max(0.0, float(engine_rpm))
        v_bus = float(bus_voltage_v)
        p_load = max(0.0, float(electrical_load_w))
        i_max = max(0.0, float(max_current_a))
        eta_alt = float(alternator_efficiency)
        rpm_cutin = float(cutin_rpm)

        if v_bus <= 0 or eta_alt <= 0:
            raise ElectricalAircraftError("Voltage and alternator efficiency must be positive.")

        if rpm < rpm_cutin:
            return (0.0, 0.0, 0.0, 0.0)

        # Desired Current Generation (A)
        i_demand = p_load / v_bus
        i_alt = min(i_max, i_demand)
        p_alt_elec = v_bus * i_alt
        p_alt_mech = p_alt_elec / eta_alt

        omega_eng = rpm * (math.pi / 30.0)
        if omega_eng <= 1.0:
            t_alt = 0.0
        else:
            t_alt = p_alt_mech / omega_eng

        return (i_alt, p_alt_elec, p_alt_mech, t_alt)

    @classmethod
    def compute_starter_torque_and_power(
        cls,
        starter_active: bool,
        engine_rpm: float,
        battery_soc: float,
        min_starting_soc: float = 0.20,
        starter_power_w: float = 1500.0,
        starter_efficiency: float = 0.80,
        min_cranking_rad_s: float = 15.0,
        idle_rpm: float = 1400.0
    ) -> Tuple[float, float, float]:
        """
        Computes starter motor electrical power draw and mechanical torque assistance:
        If not starter_active OR battery_soc < min_starting_soc OR engine_rpm >= idle_rpm:
          P_starter = 0, T_starter = 0
        Else:
          P_starter = starter_power_w (W)
          P_starter_mech = starter_power_w * starter_efficiency (W)
          T_starter = P_starter_mech / max(min_cranking_rad_s, omega_eng) (N*m)
        Returns Tuple of (starter_active_flag, starter_power_w, starter_torque_n_m).
        """
        rpm = max(0.0, float(engine_rpm))
        soc = float(battery_soc)
        min_soc = float(min_starting_soc)
        p_rating = max(0.0, float(starter_power_w))
        eta_starter = float(starter_efficiency)
        w_crank_min = float(min_cranking_rad_s)

        if not starter_active or soc < min_soc or rpm >= idle_rpm:
            return (0.0, 0.0, 0.0)

        omega_eng = rpm * (math.pi / 30.0)
        w_crank = max(w_crank_min, omega_eng)

        p_starter_elec = p_rating
        p_starter_mech = p_rating * eta_starter
        t_starter = p_starter_mech / w_crank

        return (1.0, p_starter_elec, t_starter)

    @classmethod
    def step_battery_soc(
        cls,
        current_soc: float,
        net_electrical_power_demand_w: float,
        dt_seconds: float,
        nominal_energy_j: float = 2592000.0,
        nominal_voltage_v: float = 24.0,
        charge_efficiency: float = 0.90,
        discharge_efficiency: float = 0.95
    ) -> Tuple[float, float, float, float]:
        """
        Integrates battery State of Charge (SOC) in [0.0, 1.0] and computes terminal voltage/current:
        SIGN CONVENTION:
          Positive battery current I_batt > 0 = DISCHARGE
          Negative battery current I_batt < 0 = CHARGE

        Net Demand P_net = P_load + P_starter - P_alt_total:
        If P_net > 0 (Discharging):
          P_batt_dis = P_net / discharge_efficiency (W)
          I_batt = P_batt_dis / nominal_voltage_v (A)
          dSOC/dt = -P_batt_dis / E_nominal (1/s)
        If P_net < 0 (Charging):
          P_batt_chg = -P_net * charge_efficiency (W)
          I_batt = -P_batt_chg / nominal_voltage_v (A)
          dSOC/dt = +P_batt_chg / E_nominal (1/s)

        Returns Tuple of (new_soc, battery_voltage_v, battery_current_a, battery_power_w).
        """
        soc = float(current_soc)
        p_net = float(net_electrical_power_demand_w)
        dt = float(dt_seconds)
        e_nom = float(nominal_energy_j)
        v_nom = float(nominal_voltage_v)
        eta_chg = float(charge_efficiency)
        eta_dis = float(discharge_efficiency)

        if e_nom <= 0 or v_nom <= 0 or eta_chg <= 0 or eta_dis <= 0:
            raise ElectricalAircraftError("Battery capacity, voltage, and efficiencies must be positive.")

        if p_net > 0:
            # DISCHARGING (Positive Current)
            p_batt_dis = p_net / eta_dis
            i_batt = p_batt_dis / v_nom
            dsoc = -(p_batt_dis * dt) / e_nom
            p_batt_chem = p_batt_dis
        elif p_net < 0 and soc < 1.0:
            # CHARGING (Negative Current)
            p_batt_chg = -p_net * eta_chg
            i_batt = -(p_batt_chg / v_nom)
            dsoc = (p_batt_chg * dt) / e_nom
            p_batt_chem = -p_batt_chg
        else:
            # NEUTRAL / FULL
            i_batt = 0.0
            dsoc = 0.0
            p_batt_chem = 0.0

        new_soc = max(0.0, min(1.0, soc + dsoc))
        v_batt_terminal = v_nom * (0.85 + 0.15 * new_soc)

        return (new_soc, v_batt_terminal, i_batt, p_batt_chem)

    @classmethod
    def compute_aircraft_longitudinal_dynamics(
        cls,
        x_m: float,
        altitude_m: float,
        velocity_m_s: float,
        flight_path_angle_rad: float,
        total_thrust_n: float,
        air_density_kg_m3: float,
        dt_seconds: float,
        gross_mass_kg: float = 1800.0,
        gravity_m_s2: float = 9.80665,
        wing_area_m2: float = 22.5,
        zero_lift_drag_cd0: float = 0.025,
        induced_drag_k: float = 0.045,
        trim_lift_cl: float = 0.45
    ) -> Tuple[float, float, float, float, float, float, float, float]:
        """
        Computes 3-DOF Longitudinal Aircraft Force Balance & Kinematic State Integration:
        C_D = CD0 + k * CL^2
        F_drag = 0.5 * rho * V^2 * S * C_D (N)
        Weight W = m_ac * g (N)
        dV/dt = (F_thrust_total - F_drag - W * sin(gamma)) / m_ac (m/s^2)
        dh/dt = V * sin(gamma) (m/s)
        dx/dt = V * cos(gamma) (m/s)

        Returns Tuple of (new_x_m, new_alt_m, new_velocity_m_s, accel_m_s2, drag_n, weight_n, total_thrust_n, flight_path_angle_rad).
        """
        x_curr = float(x_m)
        alt_curr = max(0.0, float(altitude_m))
        v_curr = max(0.0, float(velocity_m_s))
        gamma = float(flight_path_angle_rad)
        f_thrust = max(0.0, float(total_thrust_n))
        rho = float(air_density_kg_m3)
        dt = float(dt_seconds)
        m_ac = float(gross_mass_kg)
        g = float(gravity_m_s2)
        s_wing = float(wing_area_m2)
        cd0 = float(zero_lift_drag_cd0)
        k_ind = float(induced_drag_k)
        cl_trim = float(trim_lift_cl)

        if m_ac <= 0 or s_wing <= 0 or rho <= 0:
            raise ElectricalAircraftError("Aircraft mass, wing area, and air density must be positive.")

        # Drag Polar Coefficient C_D
        cd_total = cd0 + k_ind * (cl_trim ** 2)

        # Aerodynamic Drag Force (N)
        f_drag = 0.5 * rho * (v_curr ** 2) * s_wing * cd_total

        # Gravitational Weight Force (N)
        f_weight = m_ac * g

        # Longitudinal Acceleration dV/dt (m/s^2)
        accel = (f_thrust - f_drag - f_weight * math.sin(gamma)) / m_ac

        # Integrations
        v_new = max(0.0, v_curr + accel * dt)
        dh = v_new * math.sin(gamma) * dt
        dx = v_new * math.cos(gamma) * dt

        alt_new = max(0.0, alt_curr + dh)
        x_new = x_curr + dx

        return (x_new, alt_new, v_new, accel, f_drag, f_weight, f_thrust, gamma)
