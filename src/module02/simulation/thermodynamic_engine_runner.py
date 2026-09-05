"""
Full Closed-Loop Thermodynamic Engine, Turbo Closure, Dynamic Thermal & 3-DOF Aircraft Flight Runner (Phase 3.8 Engine).
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Dict, Optional, Tuple

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.models.enums import EngineOperatingState
from src.module02.models.states import (
    AircraftState,
    BatteryState,
    ElectricalState,
    EngineState,
    LubricationState,
    PropellerState,
    SimulationState,
    ThermalState,
    ThermodynamicState,
    TurbochargerState,
)
from src.module02.physics.atmosphere import AtmosphereModel
from src.module02.physics.thermodynamics_combustion import ThermodynamicsCombustionModel
from src.module02.simulation.electrical_aircraft_runner import ElectricalAircraftRunner
from src.module02.simulation.engine_runner import EngineRunner
from src.module02.simulation.intake_runner import IntakeRunner
from src.module02.simulation.propulsion_runner import PropulsionRunner


class ThermodynamicEngineRunner:
    """
    Master Closed-Loop Thermodynamic Simulation Runner.
    Physically couples:
    Intake Airflow -> Fuel Metering -> AFR -> Equivalence Ratio -> Bounded Combustion Efficiency -> Heat Release ->
    Indicated Power/Torque -> Rotational Crankshaft Dynamics -> Exhaust Enthalpy -> Turbine Power ->
    Turbo Shaft Acceleration -> Compressor Power/Ratio -> Emerging MAP -> Convective/Radiant 1st-Order Thermal Management ->
    Thermal Derating -> Propeller Load/Thrust -> 1000 Hz Vibration -> Cumulative Wear -> Electrical Bus Balance ->
    Battery SOC -> Starter Motor Cranking -> Total Propulsive Thrust -> 3-DOF Aircraft Flight Dynamics -> Fuel Burn Weight Subtraction.
    """

    def __init__(self, clock: Optional[SimulationClock] = None, engine_config: Optional[Dict] = None) -> None:
        self.clock = clock if clock is not None else SimulationClock()
        self.engine_config = engine_config if engine_config is not None else ConfigLoader.load_engine_config()
        self.state = SimulationState()
        self.environment_inputs = {"altitude_m": None, "temp_offset_k": 0.0, "relative_humidity_percent": 0.0, "wind_speed_m_s": 0.0}

        # Initialize Subsystem Runners
        self.engine_runner = EngineRunner(self.clock, self.engine_config)
        self.intake_runner = IntakeRunner(self.clock, self.engine_config)
        self.propulsion_runner = PropulsionRunner(self.clock, self.engine_config)
        self.electrical_aircraft_runner = ElectricalAircraftRunner(self.clock, self.engine_config)

        # Extract Fuel System Configs
        self.max_fuel_flow_kg_h = ConfigLoader.get_config_value(self.engine_config, "fuel_system.max_fuel_flow_kg_h", 36.0)
        self.lhv_j_kg = ConfigLoader.get_config_value(self.engine_config, "fuel_system.lower_heating_value_lhv_j_kg", 43000000.0)
        self.stoich_afr = ConfigLoader.get_config_value(self.engine_config, "fuel_system.stoichiometric_afr", 14.5)
        self.idle_fuel_flow_kg_h = ConfigLoader.get_config_value(self.engine_config, "fuel_system.idle_fuel_flow_kg_h", 2.5)

        # Extract Combustion Configs
        self.peak_eta_comb = ConfigLoader.get_config_value(self.engine_config, "combustion.peak_combustion_efficiency", 0.96)
        self.f_work = ConfigLoader.get_config_value(self.engine_config, "combustion.useful_indicated_work_fraction", 0.42)
        self.f_exh = ConfigLoader.get_config_value(self.engine_config, "combustion.exhaust_energy_fraction", 0.35)
        self.f_wall = ConfigLoader.get_config_value(self.engine_config, "combustion.wall_heat_transfer_fraction", 0.20)
        self.max_indicated_torque = ConfigLoader.get_config_value(self.engine_config, "power_and_performance.max_indicated_torque_n_m", 165.0)
        self.takeoff_duration_s = ConfigLoader.get_config_value(self.engine_config, "rotax_limits.takeoff_duration_s", 300.0)
        self.takeoff_reset_throttle_ratio = ConfigLoader.get_config_value(self.engine_config, "rotax_limits.takeoff_reset_throttle_ratio", 1.08)
        self.takeoff_elapsed_s = {1: 0.0, 2: 0.0}

        # Extract Turbocharger Dynamic Configs
        self.turbo_inertia = ConfigLoader.get_config_value(self.engine_config, "turbocharger_dynamic.turbo_rotational_inertia_kg_m2", 0.00015)
        self.eta_turbine = ConfigLoader.get_config_value(self.engine_config, "turbocharger_dynamic.turbine_efficiency", 0.76)
        self.eta_compressor = ConfigLoader.get_config_value(self.engine_config, "turbocharger_dynamic.compressor_efficiency", 0.78)
        self.turbo_fric_coeff = ConfigLoader.get_config_value(self.engine_config, "turbocharger_dynamic.turbo_friction_coeff_n_m_s_rad", 0.00005)
        self.max_turbo_rpm = ConfigLoader.get_config_value(self.engine_config, "turbocharger_dynamic.max_turbo_speed_rpm", 140000.0)
        self.max_map_pa = ConfigLoader.get_config_value(self.engine_config, "turbocharger.max_manifold_absolute_pressure_pa", 132000.0)
        self.cp_exh = ConfigLoader.get_config_value(self.engine_config, "thermodynamics.exhaust_specific_heat_cp_j_kg_k", 1150.0)
        self.turbo_lag_tau_s = ConfigLoader.get_config_value(self.engine_config, "turbocharger.lag_tau_s", 0.8)
        self.takeoff_target_map_pa = ConfigLoader.get_config_value(self.engine_config, "turbocharger.takeoff_target_map_pa", self.max_map_pa)

        # Extract Thermal Limits & Mass Configs
        self.head_mass_kg = ConfigLoader.get_config_value(self.engine_config, "thermal.cylinder_head_mass_kg", 12.0)
        self.head_cp = ConfigLoader.get_config_value(self.engine_config, "thermal.cylinder_head_specific_heat_j_kg_k", 890.0)
        self.coolant_mass_kg = ConfigLoader.get_config_value(self.engine_config, "cooling.coolant_mass_kg", 8.0)
        self.coolant_cp = ConfigLoader.get_config_value(self.engine_config, "cooling.coolant_specific_heat_j_kg_k", 3800.0)
        self.oil_mass_kg = ConfigLoader.get_config_value(self.engine_config, "lubrication.oil_mass_kg", 4.0)
        self.oil_cp = ConfigLoader.get_config_value(self.engine_config, "lubrication.oil_specific_heat_j_kg_k", 2100.0)
        self.max_safe_cht_k = ConfigLoader.get_config_value(self.engine_config, "thermal.max_safe_cht_k", 523.15)
        self.max_safe_egt_k = ConfigLoader.get_config_value(self.engine_config, "thermal.max_safe_egt_k", 1123.15)
        self.max_safe_oil_k = ConfigLoader.get_config_value(self.engine_config, "thermal.max_safe_oil_temp_k", 413.15)

        # Initialize Master Twin Engine States
        self._initialize_states()

    def _initialize_states(self) -> None:
        """Initializes per-engine state containers."""
        for eng_idx in [1, 2]:
            self.state.engines[eng_idx] = EngineState(engine_index=eng_idx, engine_id=f"engine_{eng_idx}")
            self.state.thermodynamics[eng_idx] = ThermodynamicState(engine_index=eng_idx)
            self.state.thermals[eng_idx] = ThermalState()
            self.state.lubrication[eng_idx] = LubricationState()

    def set_environment_inputs(
        self,
        altitude_m: Optional[float] = None,
        temp_offset_k: float = 0.0,
        relative_humidity_percent: float = 0.0,
        wind_speed_m_s: float = 0.0,
    ) -> None:
        """Set operator-controlled environmental inputs for simulation.

        These are simulation controls, not internal engine-state overrides.
        None altitude means the aircraft's evolving altitude is used.
        """
        self.environment_inputs = {
            "altitude_m": altitude_m,
            "temp_offset_k": float(temp_offset_k),
            "relative_humidity_percent": float(relative_humidity_percent),
            "wind_speed_m_s": float(wind_speed_m_s),
        }

    def step_thermodynamic_cycle(
        self,
        throttles: Dict[int, float],
        starter_commands: Dict[int, bool],
        flight_path_angle_rad: float = 0.0
    ) -> SimulationState:
        """
        Executes one fully coupled closed-loop thermodynamic simulation step across both engines and aircraft.
        Returns master SimulationState.
        """
        dt = self.clock.dt_seconds

        # 1. Atmospheric Environment based on Aircraft Position
        alt_curr = self.environment_inputs["altitude_m"]
        if alt_curr is None:
            alt_curr = self.electrical_aircraft_runner.state.aircraft.altitude_m
        alt_curr = float(alt_curr)
        v_curr = self.electrical_aircraft_runner.state.aircraft.velocity_m_s
        t_std = AtmosphereModel.compute_standard_temperature(alt_curr)
        t_amb = AtmosphereModel.compute_actual_temperature(alt_curr, self.environment_inputs["temp_offset_k"])
        p_amb = AtmosphereModel.compute_ambient_pressure(alt_curr)
        rho_air, _, _ = AtmosphereModel.compute_moist_air_density(
            p_amb, t_amb, self.environment_inputs["relative_humidity_percent"]
        )

        self.state.environment.altitude_m = alt_curr
        self.state.environment.ambient_temp_k = t_amb
        self.state.environment.ambient_pressure_pa = p_amb
        self.state.environment.air_density_kg_m3 = rho_air
        self.state.environment.relative_humidity_percent = self.environment_inputs["relative_humidity_percent"]
        self.state.environment.wind_speed_m_s = self.environment_inputs["wind_speed_m_s"]

        total_step_fuel_burn_kg = 0.0
        engine_rpms: Dict[int, float] = {}
        engine_thrusts: Dict[int, float] = {}

        # First Pass: Compute Electrical Shaft Torques & Starter Cranking Torques
        for eng_idx in [1, 2]:
            engine_rpms[eng_idx] = self.state.engines[eng_idx].engine_rpm
            engine_thrusts[eng_idx] = self.propulsion_runner.state.propellers[eng_idx].thrust_n

        elec_state, batt_state, ac_state, alt_torques, starter_torques = self.electrical_aircraft_runner.step_electrical_and_aircraft(
            engine_rpms=engine_rpms,
            starter_commands=starter_commands,
            engine_thrusts=engine_thrusts,
            air_density_kg_m3=rho_air,
            flight_path_angle_rad=flight_path_angle_rad,
            fuel_burn_step_kg=0.0
        )

        # Second Pass: Step Closed Thermodynamics & Physical Acceleration for Engine 1 and Engine 2
        for eng_idx in [1, 2]:
            # The existing dashboard exposes a 0–100% lever. For the Rotax 914
            # model that lever is normalized to the physical 0–115% take-off
            # command without changing the dashboard itself.
            ui_th = max(0.0, min(100.0, float(throttles.get(eng_idx, 0.0))))
            physical_th = ui_th * 1.15
            th = ui_th  # Preserve the dashboard/API throttle value exactly.
            starter_cmd = bool(starter_commands.get(eng_idx, False))

            eng = self.state.engines[eng_idx]
            thermo = self.state.thermodynamics[eng_idx]
            therm = self.state.thermals[eng_idx]
            lub = self.state.lubrication[eng_idx]

            # Rotax start logic: throttle alone cannot start the engine. The
            # starter must first spin the crankshaft; combustion then becomes
            # self-sustaining and the starter can be released.
            if eng.engine_rpm < 900.0 and starter_cmd:
                eng.operating_state = EngineOperatingState.STARTING
            elif eng.engine_rpm >= 900.0 and th <= 5.0:
                eng.operating_state = EngineOperatingState.IDLE
            elif eng.engine_rpm >= 900.0 and th > 5.0:
                eng.operating_state = EngineOperatingState.RUNNING
            elif not starter_cmd and th <= 0.0 and eng.engine_rpm < 400.0:
                eng.operating_state = EngineOperatingState.OFF

            eng.starter_active = starter_cmd

            # Rotax take-off limit tracking. The UI remains unchanged; 100%
            # dashboard lever corresponds to the modeled 115% take-off command.
            if physical_th >= 115.0 and eng.operating_state in (EngineOperatingState.IDLE, EngineOperatingState.RUNNING):
                self.takeoff_elapsed_s[eng_idx] += dt
            elif physical_th < (100.0 * self.takeoff_reset_throttle_ratio / 1.15):
                self.takeoff_elapsed_s[eng_idx] = 0.0
            eng.takeoff_elapsed_s = self.takeoff_elapsed_s[eng_idx]
            eng.takeoff_duration_limit_exceeded = self.takeoff_elapsed_s[eng_idx] >= self.takeoff_duration_s

            # A. Intake Airflow Rate m_dot_air
            current_map = eng.manifold_pressure_pa
            intake_state = self.intake_runner.step_intake(eng_idx, eng.engine_rpm, physical_th, p_amb, t_amb, current_map)
            m_dot_air = intake_state.air_mass_flow_kg_s

            # B. Metered Fuel Flow Rate
            m_dot_fuel_s, m_dot_fuel_h, p_fuel_w = ThermodynamicsCombustionModel.compute_metered_fuel_flow(
                throttle_percent=physical_th,
                engine_speed_rpm=eng.engine_rpm,
                air_mass_flow_kg_s=m_dot_air,
                operating_state_str=eng.operating_state.value,
                max_fuel_flow_kg_h=self.max_fuel_flow_kg_h,
                idle_fuel_flow_kg_h=self.idle_fuel_flow_kg_h,
                stoichiometric_afr=self.stoich_afr,
                thermal_derating_factor=therm.thermal_derating_factor,
                lower_heating_value_j_kg=self.lhv_j_kg
            )
            step_fuel_burn = m_dot_fuel_s * dt
            thermo.fuel_consumed_total_kg += step_fuel_burn
            total_step_fuel_burn_kg += step_fuel_burn

            # C. AFR & Equivalence Ratio phi
            afr_actual, phi = ThermodynamicsCombustionModel.compute_afr_and_equivalence_ratio(
                air_mass_flow_kg_s=m_dot_air,
                fuel_mass_flow_kg_s=m_dot_fuel_s,
                stoichiometric_afr=self.stoich_afr
            )

            # D. Bounded Combustion Efficiency
            deg = self.propulsion_runner.state.degradation.get(eng_idx)
            r_wear = deg.ring_wear if deg else 0.0
            i_wear = deg.injector_wear if deg else 0.0
            ignition_timing = ThermodynamicsCombustionModel.ignition_timing_from_rpm(
                eng.engine_rpm,
                idle_rpm=ConfigLoader.get_config_value(self.engine_config, "power_and_performance.idle_rpm", 1400.0),
                advance_rpm=ConfigLoader.get_config_value(self.engine_config, "power_and_performance.torque_peak_rpm", ConfigLoader.get_config_value(self.engine_config, "rotax_limits.torque_peak_rpm", 4900.0))
            )
            eta_comb = ThermodynamicsCombustionModel.compute_combustion_efficiency(
                equivalence_ratio=phi,
                engine_speed_rpm=eng.engine_rpm,
                ring_wear=r_wear,
                injector_wear=i_wear,
                peak_combustion_efficiency=self.peak_eta_comb,
                ignition_timing_deg_btdc=ignition_timing,
                active_cdi_circuits=2
            )
            eng.injection_timing_deg_btdc = ignition_timing

            # E. Heat Release & Explicit Energy Audit
            p_heat, p_ind, p_exh, q_wall, p_residual = ThermodynamicsCombustionModel.compute_heat_release_and_energy_audit(
                fuel_energy_rate_w=p_fuel_w,
                combustion_efficiency=eta_comb,
                useful_indicated_work_fraction=self.f_work,
                exhaust_energy_fraction=self.f_exh,
                wall_heat_transfer_fraction=self.f_wall
            )

            # F. Bounded Indicated Combustion Torque T_ind
            t_ind = ThermodynamicsCombustionModel.compute_indicated_torque(
                indicated_power_w=p_ind,
                engine_speed_rpm=eng.engine_rpm,
                min_cranking_rad_s=15.0,
                max_indicated_torque_n_m=self.max_indicated_torque
            )

            # G. Dynamic Turbocharger Shaft Acceleration & Emerging MAP
            m_dot_exh = m_dot_air + m_dot_fuel_s
            n_turbo_new, w_turbo_new, p_turb, p_comp, t_turb, t_comp, map_emergent = ThermodynamicsCombustionModel.step_turbocharger_dynamics_and_map(
                current_turbo_speed_rpm=eng.turbocharger.turbo_speed_rpm,
                exhaust_mass_flow_kg_s=m_dot_exh,
                exhaust_energy_rate_w=p_exh,
                air_mass_flow_kg_s=m_dot_air,
                ambient_pressure_pa=p_amb,
                ambient_temp_k=t_amb,
                dt_seconds=dt,
                turbo_inertia_kg_m2=self.turbo_inertia,
                turbine_efficiency=self.eta_turbine,
                compressor_efficiency=self.eta_compressor,
                turbo_friction_coeff=self.turbo_fric_coeff,
                max_turbo_speed_rpm=self.max_turbo_rpm,
                max_map_pa=self.max_map_pa,
                cp_exh_j_kg_k=self.cp_exh,
                throttle_percent=physical_th,
                target_map_pa=self.takeoff_target_map_pa,
                turbo_lag_tau_s=self.turbo_lag_tau_s
            )

            eng.turbocharger.turbo_speed_rpm = n_turbo_new
            eng.turbocharger.turbo_omega_rad_per_sec = w_turbo_new
            eng.turbocharger.turbine_power_w = p_turb
            eng.turbocharger.compressor_power_w = p_comp
            eng.turbocharger.turbine_torque_n_m = t_turb
            eng.turbocharger.compressor_torque_n_m = t_comp
            eng.turbocharger.max_manifold_absolute_pressure_pa = map_emergent
            eng.manifold_pressure_pa = map_emergent

            # H. Dynamic 1st-Order Thermal Management & Protection Derating
            new_cht, new_coolant, new_oil, new_egt, derate_factor = ThermodynamicsCombustionModel.step_engine_thermal_management(
                current_cht_k=therm.cht_k,
                current_coolant_k=therm.coolant_temp_k,
                current_oil_k=lub.oil_temperature_k,
                current_egt_k=therm.egt_k,
                wall_heat_generation_w=q_wall,
                exhaust_energy_rate_w=p_exh,
                friction_heat_w=eng.friction_torque_n_m * (eng.engine_speed_rad_per_sec),
                airspeed_m_s=v_curr,
                exhaust_mass_flow_kg_s=m_dot_exh,
                exhaust_specific_heat_j_kg_k=self.cp_exh,
                ambient_temp_k=t_amb,
                dt_seconds=dt,
                head_mass_kg=self.head_mass_kg,
                head_cp_j_kg_k=self.head_cp,
                coolant_mass_kg=self.coolant_mass_kg,
                coolant_cp_j_kg_k=self.coolant_cp,
                oil_mass_kg=self.oil_mass_kg,
                oil_cp_j_kg_k=self.oil_cp,
                max_safe_cht_k=self.max_safe_cht_k,
                max_safe_egt_k=self.max_safe_egt_k,
                max_safe_oil_k=self.max_safe_oil_k
            )

            therm.cht_k = new_cht
            therm.coolant_temp_k = new_coolant
            therm.egt_k = new_egt
            therm.thermal_derating_factor = derate_factor
            lub.oil_temperature_k = new_oil

            # I. Propulsion, Load & Wear
            eng_state, prop_state, deg_state, vib_state = self.propulsion_runner.step_propulsion(
                engine_index=eng_idx,
                engine_rpm=eng.engine_rpm,
                air_density_kg_m3=rho_air,
                indicated_torque_n_m=t_ind,
                fuel_mass_flow_kg_s=m_dot_fuel_s,
                cht_k=new_cht,
                oil_temp_k=new_oil,
                oil_viscosity_pa_s=lub.oil_viscosity_pa_s
            )

            # J. Engine Crankshaft Dynamics Integration
            # EngineRunner owns the crankshaft integrator but must operate on
            # the same physical EngineState object so turbo/fuel/thermal state
            # is not discarded at the module boundary.
            self.engine_runner.state.engines[eng_idx] = eng
            t_starter_val = starter_torques.get(eng_idx, 0.0)
            t_alt_val = alt_torques.get(eng_idx, 0.0)
            t_prop_reflected = prop_state.reflected_engine_load_n_m

            eng_updated = self.engine_runner.step_engine(
                engine_index=eng_idx,
                throttle_percent=th,
                load_torque_n_m=t_prop_reflected,
                indicated_torque_n_m=t_ind,
                alternator_torque_n_m=t_alt_val,
                starter_torque_n_m=t_starter_val
            )

            # Update Thermodynamic Output State
            thermo.air_fuel_ratio = afr_actual
            thermo.equivalence_ratio = phi
            thermo.fuel_mass_flow_kg_s = m_dot_fuel_s
            thermo.fuel_mass_flow_kg_h = m_dot_fuel_h
            thermo.fuel_energy_rate_w = p_fuel_w
            thermo.combustion_efficiency = eta_comb
            thermo.heat_release_rate_w = p_heat
            thermo.indicated_power_w = p_ind
            thermo.indicated_torque_n_m = t_ind
            thermo.exhaust_mass_flow_kg_s = m_dot_exh
            thermo.exhaust_temp_k = new_egt
            thermo.egt_k = new_egt
            thermo.cht_k = new_cht
            thermo.coolant_temp_k = new_coolant
            thermo.oil_temp_k = new_oil
            thermo.thermal_derating_factor = derate_factor

            eng_updated.air_mass_flow_kg_s = m_dot_air
            eng_updated.fuel_mass_flow_kg_s = m_dot_fuel_s
            eng_updated.air_fuel_ratio = afr_actual
            eng_updated.indicated_power_w = p_ind
            eng_updated.manifold_pressure_pa = map_emergent
            self.state.engines[eng_idx] = eng_updated

        # Third Pass: Step Aircraft Kinematics & Causal Weight Reduction from Fuel Burn
        elec_state, batt_state, ac_state, _, _ = self.electrical_aircraft_runner.step_electrical_and_aircraft(
            engine_rpms={1: self.state.engines[1].engine_rpm, 2: self.state.engines[2].engine_rpm},
            starter_commands=starter_commands,
            engine_thrusts={1: self.propulsion_runner.state.propellers[1].thrust_n, 2: self.propulsion_runner.state.propellers[2].thrust_n},
            air_density_kg_m3=rho_air,
            flight_path_angle_rad=flight_path_angle_rad,
            fuel_burn_step_kg=total_step_fuel_burn_kg
        )

        self.state.electrical = elec_state
        self.state.battery = batt_state
        self.state.aircraft = ac_state
        self.state.propulsion = self.propulsion_runner.state
        self.state.propellers = self.propulsion_runner.state.propellers

        self.clock.step()
        return self.state
