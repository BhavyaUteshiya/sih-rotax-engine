"""
Electrical Subsystem, Battery SOC, Starter Motor, and 3-DOF Aircraft Dynamics Simulation Runner (Phase 3.7 & Phase 3.8 Fuel Burn Coupling).
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Dict, Tuple

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.models.states import AircraftState, BatteryState, ElectricalState, SimulationState
from src.module02.physics.electrical_aircraft import ElectricalAircraftModel


class ElectricalAircraftRunner:
    """
    Simulation Runner managing Electrical Bus Loads, Alternator Shaft Reflections,
    Battery State of Charge Integration, Starter Motor Cranking, 3-DOF Aircraft Dynamics,
    and Causal Fuel Burn Weight Reduction Coupling.
    Supports twin-engine independent alternators and starters.
    """

    def __init__(self, clock: SimulationClock, engine_config: Dict) -> None:
        self.clock = clock
        self.config = engine_config
        self.state = SimulationState()

        # Extract Electrical Configs via ConfigLoader
        self.bus_voltage_nominal = ConfigLoader.get_config_value(engine_config, "electrical.nominal_bus_voltage_v", 28.0)
        self.avionics_load_w = ConfigLoader.get_config_value(engine_config, "electrical.baseline_avionics_load_w", 800.0)

        # Extract Alternator Configs
        self.alt_max_current_a = ConfigLoader.get_config_value(engine_config, "alternator.max_current_a", 75.0)
        self.alt_efficiency = ConfigLoader.get_config_value(engine_config, "alternator.efficiency", 0.85)
        self.alt_cutin_rpm = ConfigLoader.get_config_value(engine_config, "alternator.cutin_rpm", 1000.0)

        # Extract Battery Configs
        self.bat_nominal_voltage_v = ConfigLoader.get_config_value(engine_config, "battery.nominal_voltage_v", 24.0)
        self.bat_capacity_ah = ConfigLoader.get_config_value(engine_config, "battery.capacity_ah", 30.0)
        self.bat_nominal_energy_j = ConfigLoader.get_config_value(engine_config, "battery.nominal_energy_j", 2592000.0)
        self.bat_initial_soc = ConfigLoader.get_config_value(engine_config, "battery.initial_soc", 0.90)
        self.bat_min_starting_soc = ConfigLoader.get_config_value(engine_config, "battery.min_starting_soc", 0.20)
        self.bat_charge_efficiency = ConfigLoader.get_config_value(engine_config, "battery.charge_efficiency", 0.90)
        self.bat_discharge_efficiency = ConfigLoader.get_config_value(engine_config, "battery.discharge_efficiency", 0.95)

        # Extract Starter Configs
        self.starter_power_w = ConfigLoader.get_config_value(engine_config, "starter.starter_power_w", 1500.0)
        self.starter_efficiency = ConfigLoader.get_config_value(engine_config, "starter.starter_efficiency", 0.80)
        self.min_cranking_rad_s = ConfigLoader.get_config_value(engine_config, "starter.min_cranking_rad_s", 15.0)

        # Extract Aircraft & Aerodynamics Configs
        self.gross_mass_kg = ConfigLoader.get_config_value(engine_config, "aircraft.gross_takeoff_mass_kg", 1800.0)
        self.gravity_m_s2 = ConfigLoader.get_config_value(engine_config, "aircraft.gravity_m_s2", 9.80665)
        self.wing_area_m2 = ConfigLoader.get_config_value(engine_config, "aerodynamics.wing_area_m2", 22.5)
        self.cd0 = ConfigLoader.get_config_value(engine_config, "aerodynamics.zero_lift_drag_coefficient_cd0", 0.025)
        self.k_induced = ConfigLoader.get_config_value(engine_config, "aerodynamics.induced_drag_coefficient_k", 0.045)
        self.cl_trim = ConfigLoader.get_config_value(engine_config, "aerodynamics.trim_lift_coefficient_cl", 0.45)

        # Initialize Master States
        self.state.battery.battery_soc = self.bat_initial_soc
        self.state.battery.nominal_capacity_ah = self.bat_capacity_ah
        self.state.battery.nominal_energy_j = self.bat_nominal_energy_j
        self.state.battery.battery_voltage_v = self.bat_nominal_voltage_v
        self.state.electrical.bus_voltage_v = self.bus_voltage_nominal
        self.state.electrical.electrical_load_w = self.avionics_load_w

        self.state.aircraft.gross_mass_kg = self.gross_mass_kg
        self.state.aircraft.weight_force_n = self.gross_mass_kg * self.gravity_m_s2

    def step_electrical_and_aircraft(
        self,
        engine_rpms: Dict[int, float],
        starter_commands: Dict[int, bool],
        engine_thrusts: Dict[int, float],
        air_density_kg_m3: float,
        flight_path_angle_rad: float = 0.0,
        fuel_burn_step_kg: float = 0.0
    ) -> Tuple[ElectricalState, BatteryState, AircraftState, Dict[int, float], Dict[int, float]]:
        """
        Steps electrical power balance, alternator shaft reflections, battery SOC integration,
        starter cranking assistance, 3-DOF aircraft longitudinal flight dynamics, and causal fuel mass burn.
        Returns Tuple of (ElectricalState, BatteryState, AircraftState, alt_torques_n_m, starter_torques_n_m).
        """
        # Causal Fuel Burn Weight Reduction
        if fuel_burn_step_kg > 0.0:
            rem_fuel = max(0.0, self.state.aircraft.fuel_mass_remaining_kg - fuel_burn_step_kg)
            self.state.aircraft.fuel_mass_remaining_kg = rem_fuel
            self.gross_mass_kg = self.state.aircraft.dry_mass_kg + self.state.aircraft.payload_mass_kg + rem_fuel
            self.state.aircraft.gross_mass_kg = self.gross_mass_kg

        ElectricalAircraftModel.validate_inputs(
            bus_voltage_v=self.state.electrical.bus_voltage_v,
            dt_seconds=self.clock.dt_seconds,
            gross_mass_kg=self.gross_mass_kg,
            wing_area_m2=self.wing_area_m2,
            drag_coeff_cd0=self.cd0
        )

        total_alt_elec_power_w = 0.0
        total_starter_elec_power_w = 0.0
        alt_torques: Dict[int, float] = {}
        starter_torques: Dict[int, float] = {}

        # 1. Step Twin Engine Alternators & Starters
        for eng_idx in [1, 2]:
            rpm = engine_rpms.get(eng_idx, 0.0)
            starter_active = starter_commands.get(eng_idx, False)

            # Alternator output & mechanical shaft torque reflection
            i_alt, p_alt_elec, _, t_alt = ElectricalAircraftModel.compute_alternator_output_and_shaft_load(
                engine_rpm=rpm,
                bus_voltage_v=self.state.electrical.bus_voltage_v,
                electrical_load_w=self.avionics_load_w / 2.0,  # Each alternator covers half baseline demand
                max_current_a=self.alt_max_current_a,
                alternator_efficiency=self.alt_efficiency,
                cutin_rpm=self.alt_cutin_rpm
            )
            alt_torques[eng_idx] = t_alt
            total_alt_elec_power_w += p_alt_elec

            # Starter motor electrical draw & cranking torque
            _, p_starter_elec, t_starter = ElectricalAircraftModel.compute_starter_torque_and_power(
                starter_active=starter_active,
                engine_rpm=rpm,
                battery_soc=self.state.battery.battery_soc,
                min_starting_soc=self.bat_min_starting_soc,
                starter_power_w=self.starter_power_w,
                starter_efficiency=self.starter_efficiency,
                min_cranking_rad_s=self.min_cranking_rad_s,
                idle_rpm=self.alt_cutin_rpm
            )
            starter_torques[eng_idx] = t_starter
            total_starter_elec_power_w += p_starter_elec

        # 2. Electrical Net Power Demand Audit
        total_elec_demand_w = self.avionics_load_w + total_starter_elec_power_w
        net_elec_demand_w = total_elec_demand_w - total_alt_elec_power_w

        # 3. Step Battery SOC & Terminal Voltage
        new_soc, v_bat, i_batt, p_batt_chem = ElectricalAircraftModel.step_battery_soc(
            current_soc=self.state.battery.battery_soc,
            net_electrical_power_demand_w=net_elec_demand_w,
            dt_seconds=self.clock.dt_seconds,
            nominal_energy_j=self.bat_nominal_energy_j,
            nominal_voltage_v=self.bat_nominal_voltage_v,
            charge_efficiency=self.bat_charge_efficiency,
            discharge_efficiency=self.bat_discharge_efficiency
        )

        self.state.battery.battery_soc = new_soc
        self.state.battery.battery_voltage_v = v_bat
        self.state.battery.battery_current_a = i_batt
        self.state.battery.battery_power_w = p_batt_chem

        # Update Bus Electrical State
        self.state.electrical.bus_voltage_v = v_bat
        self.state.electrical.bus_current_a = (total_elec_demand_w / v_bat) if v_bat > 0 else 0.0
        self.state.electrical.alternator_power_w = total_alt_elec_power_w
        self.state.electrical.alternator_current_a = (total_alt_elec_power_w / v_bat) if v_bat > 0 else 0.0
        self.state.electrical.electrical_load_w = total_elec_demand_w
        self.state.electrical.alternator_torque_n_m = sum(alt_torques.values())
        self.state.electrical.starter_power_w = total_starter_elec_power_w
        self.state.electrical.starter_torque_n_m = sum(starter_torques.values())
        self.state.electrical.starter_active = any(starter_commands.values())

        # 4. Total Propulsive Thrust Balance
        total_thrust_n = sum(engine_thrusts.values())

        # 5. Step 3-DOF Longitudinal Aircraft Dynamics
        x_new, alt_new, v_new, accel, f_drag, f_weight, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(
            x_m=self.state.aircraft.x_m,
            altitude_m=self.state.aircraft.altitude_m,
            velocity_m_s=self.state.aircraft.velocity_m_s,
            flight_path_angle_rad=flight_path_angle_rad,
            total_thrust_n=total_thrust_n,
            air_density_kg_m3=air_density_kg_m3,
            dt_seconds=self.clock.dt_seconds,
            gross_mass_kg=self.gross_mass_kg,
            gravity_m_s2=self.gravity_m_s2,
            wing_area_m2=self.wing_area_m2,
            zero_lift_drag_cd0=self.cd0,
            induced_drag_k=self.k_induced,
            trim_lift_cl=self.cl_trim
        )

        self.state.aircraft.x_m = x_new
        self.state.aircraft.altitude_m = alt_new
        self.state.aircraft.velocity_m_s = v_new
        self.state.aircraft.flight_path_angle_rad = flight_path_angle_rad
        self.state.aircraft.longitudinal_accel_m_s2 = accel
        self.state.aircraft.drag_force_n = f_drag
        self.state.aircraft.weight_force_n = f_weight
        self.state.aircraft.total_thrust_n = total_thrust_n

        return (self.state.electrical, self.state.battery, self.state.aircraft, alt_torques, starter_torques)
