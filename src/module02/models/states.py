"""
Module 02 Core State Models & Dataclasses (Phase 3.8 Full Thermodynamic Combustion & Thermal Management).
SIH26054 — Module 02 Engine Simulator.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.module02.models.enums import (
    EngineOperatingState,
    FaultScenario,
    FlightPhase,
    PhysicalOrigin,
    ProcessingContext,
    StateCategory,
)


@dataclass
class FuelState:
    """Fuel Delivery Subsystem State Container (Canonical SI)."""
    fuel_mass_flow_kg_s: float = 0.0           # Fuel mass delivery flow rate (kg/s)
    fuel_mass_flow_kg_h: float = 0.0           # Fuel mass delivery flow rate (kg/h)
    fuel_energy_rate_w: float = 0.0            # Q_fuel_input = m_dot_fuel * LHV (W)
    lower_heating_value_j_kg: float = 43000000.0 # Fuel LHV (J/kg)
    fuel_consumed_total_kg: float = 0.0        # Cumulative metered fuel consumed (kg)


@dataclass
class CombustionState:
    """Combustion & Heat-Release Subsystem State Container (Canonical SI)."""
    air_fuel_ratio: float = 14.5               # Air-Fuel Ratio (AFR) = m_dot_air / m_dot_fuel
    equivalence_ratio: float = 1.0             # Equivalence ratio phi = AFR_stoich / AFR
    combustion_efficiency: float = 0.96        # Overall combustion efficiency eta_comb
    heat_release_rate_w: float = 0.0           # Heat release rate P_heat = m_dot_fuel * LHV * eta_comb (W)
    indicated_power_w: float = 0.0             # Useful indicated power P_ind (W)
    indicated_torque_n_m: float = 0.0          # Indicated combustion torque T_ind (N*m)
    combustion_temp_k: float = 288.15          # Mean combustion gas temperature (K)
    combustion_stability_index: float = 1.0    # Stability metric (1.0 = stable, < 0.8 = misfire)
    injection_timing_deg_btdc: float = 18.0    # Injection advance angle (°BTDC)
    combustion_duration_deg: float = 40.0      # Crank-angle duration of combustion (°)


@dataclass
class ExhaustState:
    """Exhaust Flow & Energy Subsystem State Container (Canonical SI)."""
    exhaust_mass_flow_kg_s: float = 0.0        # Total exhaust mass flow m_dot_exh (kg/s)
    exhaust_temp_k: float = 288.15             # Exhaust gas temperature T_exh (K)
    egt_k: float = 288.15                      # Dynamic Exhaust Gas Temperature EGT (K)
    exhaust_enthalpy_j_kg: float = 0.0         # Specific exhaust enthalpy (J/kg)
    exhaust_energy_rate_w: float = 0.0         # Exhaust thermal energy rate available to turbo (W)


@dataclass
class ThermodynamicState:
    """Full Engine Thermodynamic Subsystem State Container (Canonical SI - Phase 3.8)."""
    engine_index: int = 1
    air_fuel_ratio: float = 14.5               # AFR
    equivalence_ratio: float = 1.0             # phi
    fuel_mass_flow_kg_s: float = 0.0           # Fuel mass flow (kg/s)
    fuel_mass_flow_kg_h: float = 0.0           # Fuel mass flow (kg/h)
    fuel_energy_rate_w: float = 0.0            # P_fuel (W)
    combustion_efficiency: float = 0.96        # eta_comb
    heat_release_rate_w: float = 0.0           # P_heat (W)
    indicated_power_w: float = 0.0             # P_ind (W)
    indicated_torque_n_m: float = 0.0          # T_ind (N*m)
    exhaust_mass_flow_kg_s: float = 0.0        # m_dot_exh (kg/s)
    exhaust_temp_k: float = 288.15             # T_exh (K)
    egt_k: float = 288.15                      # EGT (K)
    cht_k: float = 288.15                      # CHT (K)
    coolant_temp_k: float = 288.15             # Coolant Temp (K)
    oil_temp_k: float = 288.15                 # Oil Temp (K)
    injection_timing_deg_btdc: float = 18.0    # Injection timing (°BTDC)
    thermal_derating_factor: float = 1.0       # Thermal derating multiplier in [0.0, 1.0]
    fuel_consumed_total_kg: float = 0.0        # Total fuel burn (kg)


@dataclass
class TurbochargerState:
    """Turbocharger Subsystem Dynamic State Container (Canonical SI)."""
    turbo_speed_rpm: float = 0.0               # Turbocharger shaft rotational speed N_turbo (RPM)
    turbo_omega_rad_per_sec: float = 0.0       # Turbocharger shaft angular velocity omega_turbo (rad/s)
    turbine_torque_n_m: float = 0.0            # Turbine aerodynamic driving torque tau_turbine (N*m)
    compressor_torque_n_m: float = 0.0         # Compressor load torque tau_compressor (N*m)
    turbo_friction_torque_n_m: float = 0.0     # Turbo shaft mechanical friction torque tau_friction (N*m)
    turbine_power_w: float = 0.0               # Turbine power output P_turbine (W)
    compressor_power_w: float = 0.0            # Compressor power requirement P_compressor (W)
    compressor_pressure_ratio: float = 1.0     # MAP / p_amb
    compressor_outlet_temp_k: float = 288.15   # Compressor discharge temperature T_comp_out (K)
    intercooler_effectiveness: float = 0.85    # Intercooler thermal effectiveness ratio
    max_manifold_absolute_pressure_pa: float = 220000.0 # MAP safety limit = 2.2 bar absolute
    compressor_efficiency: float = 0.78
    turbine_efficiency: float = 0.76
    wastegate_position_percent: float = 0.0    # 0 = closed (max boost), 100 = open

    def get_gauge_boost_pressure_pa(self, ambient_pressure_pa: float, actual_map_pa: Optional[float] = None) -> float:
        """P_boost_gauge = max(0.0, P_manifold_absolute - P_ambient)."""
        map_val = actual_map_pa if actual_map_pa is not None else self.max_manifold_absolute_pressure_pa
        return max(0.0, map_val - ambient_pressure_pa)


@dataclass
class GearboxState:
    """Gearbox & Shaft Speed Ratio Coupling Container (Canonical SI - Phase 3.6)."""
    engine_to_propeller_speed_ratio: float = 0.65 # N_prop = N_engine * speed_ratio
    gearbox_efficiency: float = 0.97             # Mechanical transmission efficiency
    propeller_torque_n_m: float = 0.0            # Output shaft torque (N*m)
    reflected_engine_load_n_m: float = 0.0       # Reflected load torque on engine shaft (N*m)

    @property
    def reduction_ratio(self) -> float:
        """Reduction ratio = N_engine / N_prop = 1 / speed_ratio."""
        return 1.0 / self.engine_to_propeller_speed_ratio if self.engine_to_propeller_speed_ratio > 0 else 0.0

    def compute_propeller_rpm(self, engine_rpm: float) -> float:
        """N_prop = N_engine * speed_ratio."""
        return float(engine_rpm) * self.engine_to_propeller_speed_ratio


@dataclass
class PropellerState:
    """Propeller Load & Thrust Dynamic State Container (Canonical SI - Phase 3.6)."""
    engine_index: int = 1
    propeller_rpm: float = 0.0                 # Propeller speed (RPM)
    propeller_omega_rad_per_sec: float = 0.0   # Propeller angular speed (rad/s)
    rev_per_sec: float = 0.0                   # Propeller rotational speed n_prop (rev/s)
    advance_ratio: float = 0.0                 # J_prop = V / (n * D)
    thrust_coefficient_ct: float = 0.085       # Aerodynamic thrust coefficient Ct
    torque_coefficient_cq: float = 0.014       # Aerodynamic torque coefficient Cq
    diameter_m: float = 1.70                   # Propeller diameter D_prop (m)
    load_torque_n_m: float = 0.0               # Aerodynamic load torque on propeller shaft T_prop (N*m)
    thrust_n: float = 0.0                      # Aerodynamic thrust F_thrust (N)
    reflected_engine_load_n_m: float = 0.0       # Reflected load torque on engine shaft (N*m)


@dataclass
class ElectricalState:
    """Electrical Bus, Alternator & Starter State Container (Canonical SI - Phase 3.7)."""
    bus_voltage_v: float = 28.0                # Bus Voltage V_bus (V)
    battery_voltage_v: float = 28.0            # Battery Voltage (alias for bus_voltage_v)
    bus_current_a: float = 0.0                 # Bus Load Current I_bus (A)
    alternator_power_w: float = 0.0            # Alternator output power P_alt (W)
    alternator_torque_n_m: float = 0.0         # Alternator mechanical shaft load torque T_alt (N*m)
    alternator_current_a: float = 0.0          # Alternator generation current I_alt (A)
    electrical_load_w: float = 800.0           # Total electrical load demand P_load (W)
    starter_active: bool = False               # Starter motor engagement command flag
    starter_torque_n_m: float = 0.0            # Starter cranking torque T_starter (N*m)
    starter_power_w: float = 0.0               # Starter electrical power draw P_starter (W)


@dataclass
class BatteryState:
    """Battery State-of-Charge & Power State Container (Canonical SI - Phase 3.7)."""
    battery_soc: float = 0.90                  # State of Charge SOC in [0.0, 1.0]
    battery_voltage_v: float = 24.0            # Terminal voltage V_bat (V)
    battery_current_a: float = 0.0             # Current I_batt (A) [+ = discharge, - = charge]
    battery_power_w: float = 0.0               # Chemical power P_batt (W)
    nominal_capacity_ah: float = 30.0          # Electrical capacity (Ah)
    nominal_energy_j: float = 2592000.0        # Rated total energy E_nominal (J)


@dataclass
class AircraftState:
    """3-DOF Aircraft Longitudinal Flight Dynamics State Container (Canonical SI - Phase 3.7)."""
    x_m: float = 0.0                           # Horizontal position x (m)
    altitude_m: float = 0.0                    # Altitude h (m)
    velocity_m_s: float = 0.0                  # True airspeed V (m/s)
    flight_path_angle_rad: float = 0.0         # Flight path angle gamma (rad)
    longitudinal_accel_m_s2: float = 0.0       # Longitudinal acceleration dV/dt (m/s^2)
    drag_force_n: float = 0.0                  # Aerodynamic drag force F_drag (N)
    weight_force_n: float = 17652.0            # Gravitational weight force W = m*g (N)
    total_thrust_n: float = 0.0                # Total propulsive thrust F_thrust,total (N)
    gross_mass_kg: float = 1800.0              # Aircraft gross takeoff mass m_ac (kg)
    fuel_mass_remaining_kg: float = 650.0      # Remaining Fuel mass (kg)
    dry_mass_kg: float = 800.0                 # Airframe dry mass (kg)
    payload_mass_kg: float = 350.0             # Payload mass (kg)


@dataclass
class EnvironmentState:
    """Atmosphere & Environmental State Container (All physical values in Canonical SI)."""
    altitude_m: float = 0.0                    # Altitude (m)
    ambient_temp_k: float = 288.15             # Ambient Temperature (K)
    relative_humidity_percent: float = 0.0     # Humidity (%)
    wind_speed_m_s: float = 0.0                # Wind Speed (m/s)
    ambient_pressure_pa: float = 101325.0      # Ambient Pressure (Pa)
    air_density_kg_m3: float = 1.225           # Moist Air Density (kg/m^3)
    vapor_pressure_pa: float = 0.0             # Water Vapor Pressure (Pa)
    oxygen_mass_fraction: float = 0.2315       # Oxygen Mass Fraction (ratio)


@dataclass
class FlightState:
    """Aircraft & Mission Flight Dynamics Container (Canonical SI - Twin Engine Supported)."""
    engine_count: int = 2                      # Twin Engine (e.g. TAPAS-BH-201)
    target_altitude_m: float = 9144.0          # Target Operating Altitude (30,000 ft)
    demonstrated_altitude_m: float = 8534.4    # Demonstrated Altitude (28,000 ft)
    target_endurance_hours: float = 24.0       # Target Endurance (24 h)
    demonstrated_endurance_hours: float = 18.0 # Demonstrated Endurance (18 h)

    dry_mass_kg: float = 1800.0                # Empty dry airframe mass (kg)
    payload_mass_kg: float = 350.0             # ISR Payload mass (kg)
    fuel_mass_remaining_kg: float = 650.0      # Remaining Fuel mass (kg)

    airspeed_m_s: float = 0.0                  # Forward Airspeed V_inf (m/s)
    vertical_speed_m_s: float = 0.0            # Rate of Climb V_z (m/s)
    altitude_m: float = 0.0                    # Actual Evolving Altitude (m)

    flight_phase: FlightPhase = FlightPhase.GROUND
    aerodynamic_drag_n: float = 0.0            # Drag Force (N)
    total_propeller_thrust_n: float = 0.0      # Total Thrust F_thrust,total = Sum(F_i)

    @property
    def current_mass_kg(self) -> float:
        """Current aircraft mass = dry_mass + payload_mass + remaining_fuel_mass."""
        return self.dry_mass_kg + self.payload_mass_kg + self.fuel_mass_remaining_kg


@dataclass
class CylinderState:
    """Single Cylinder Combustion & Thermal Mass Container (Canonical SI)."""
    cylinder_index: int                        # 1 to 4
    cht_k: float = 288.15                      # Cylinder Head Temperature (K)
    egt_k: float = 288.15                      # Exhaust Gas Temperature (K)
    egt_ss_k: float = 288.15                   # Steady-state EGT target (K)
    combustion_heat_release_w: float = 0.0     # Q_comb,i (W)
    indicated_torque_n_m: float = 0.0          # Indicated Torque T_ind,i (N*m)
    afr_cylinder: float = 14.5                 # Individual cylinder AFR
    misfire_active: bool = False               # Misfire flag


@dataclass
class ThermalState:
    """Engine Thermal Subsystem State Container (Canonical SI)."""
    cht_k: float = 288.15                      # Mean Cylinder Head Temperature T_CHT (K)
    coolant_temp_k: float = 288.15             # Engine Coolant Temperature (K)
    egt_k: float = 288.15                      # Dynamic Exhaust Gas Temperature (K)
    wall_heat_generation_w: float = 0.0        # Q_wall heat transfer rate to cylinder walls (W)
    cooling_heat_rejection_w: float = 0.0      # Q_cooling heat rejection rate to radiator (W)
    cylinders: Dict[int, CylinderState] = field(default_factory=dict)
    cooling_airflow_coeff: float = 12.0        # Convective cooling h_cool
    thermal_derating_factor: float = 1.0       # Thermal derating factor in [0.0, 1.0]


@dataclass
class LubricationState:
    """Lubrication & Oil Sump State Container (Canonical SI)."""
    oil_temperature_k: float = 288.15          # Oil Sump Temperature T_oil (K)
    oil_viscosity_pa_s: float = 0.08           # Dynamic Viscosity mu(T_oil) (Pa*s)
    oil_pressure_pa: float = 0.0               # Oil Pressure P_oil (Pa)
    oil_heat_generation_w: float = 0.0         # Q_oil_gen heat transfer rate to oil (W)
    oil_heat_rejection_w: float = 0.0          # Q_oil_cool heat rejection rate from oil cooler (W)
    viscosity_friction_contribution_n_m: float = 0.0 # Viscosity-dependent friction contribution (N*m)
    pump_relief_active: bool = False           # Relief valve bypass state


@dataclass
class VibrationState:
    """Structural Vibration Acceleration Synthesis Container (Canonical SI - Phase 3.6 1000 Hz)."""
    vibration_rms_m_s2: float = 0.0            # Overall structural acceleration RMS (m/s^2)
    dominant_frequency_hz: float = 0.0         # Dominant spectral peak frequency (Hz)
    rotational_order_freq_hz: float = 0.0      # Rotational 1x frequency (Hz)
    firing_order_freq_hz: float = 0.0          # Cylinder firing 2x frequency (Hz)
    propeller_order_freq_hz: float = 0.0       # Propeller blade pass 3x frequency (Hz)
    time_domain_buffer: List[float] = field(default_factory=list) # 1000 Hz synthesis buffer (1 sec window)


@dataclass
class DegradationState:
    """Evolving Cumulative Wear Degradation Container (Canonical SI - Phase 3.6)."""
    bearing_wear: float = 0.0                  # Bearing wear degradation state D_bearing [0.0 - 1.0]
    ring_wear: float = 0.0                     # Piston ring wear degradation state D_ring [0.0 - 1.0]
    injector_wear: float = 0.0                 # Injector wear degradation state D_injector [0.0 - 1.0]
    cumulative_operating_sec: float = 0.0      # Total operating exposure (s)


@dataclass
class EngineState:
    """Aero Piston Engine Thermodynamics & Dynamics State Container (Canonical SI)."""
    engine_index: int = 1                      # 1 for Engine 1, 2 for Engine 2
    engine_id: str = "engine_1"

    # Controls / Inputs
    throttle_percent: float = 0.0              # Throttle Command (0 - 100%)
    injection_timing_deg_btdc: float = 18.0    # Injection Advance (°BTDC)
    starter_active: bool = False               # Starter motor engagement flag
    takeoff_elapsed_s: float = 0.0              # Rotax 914 take-off power exposure timer
    takeoff_duration_limit_exceeded: bool = False

    # Engine Operating State
    operating_state: EngineOperatingState = EngineOperatingState.OFF

    # Dynamic States
    engine_speed_rad_per_sec: float = 0.0      # Angular Velocity omega (rad/s)
    manifold_pressure_pa: float = 101325.0     # Intake Manifold Pressure p_m (Pa)

    # Subsystem States
    fuel: FuelState = field(default_factory=FuelState)
    combustion: CombustionState = field(default_factory=CombustionState)
    exhaust: ExhaustState = field(default_factory=ExhaustState)
    turbocharger: TurbochargerState = field(default_factory=TurbochargerState)
    gearbox: GearboxState = field(default_factory=GearboxState)

    # Derived Outputs
    engine_rpm: float = 0.0                    # Display RPM (rev/min)
    air_mass_flow_kg_s: float = 0.0            # Intake Air Mass Flow (kg/s)
    fuel_mass_flow_kg_s: float = 0.0           # Fuel Delivery Flow (kg/s)
    air_fuel_ratio: float = 14.5               # Air-Fuel Ratio (AFR)
    indicated_torque_total_n_m: float = 0.0    # Total Indicated Torque T_ind,total (N*m)
    friction_torque_n_m: float = 0.0           # Friction Torque T_fric (N*m)
    pumping_loss_torque_n_m: float = 0.0       # Pumping Loss Torque T_pump (N*m)
    alternator_load_torque_n_m: float = 0.0    # Electrical Load Torque T_alt (N*m)
    indicated_power_w: float = 0.0             # Indicated Power (W)
    brake_power_w: float = 0.0                 # Net Shaft Brake Power (W)
    brake_thermal_efficiency_percent: float = 0.0 # BTE (%)


@dataclass
class SensorState:
    """Observation Layer State Container (True State vs Observed Telemetry)."""
    sensor_faults_active: Dict[str, str] = field(default_factory=dict)
    sensor_biases: Dict[str, float] = field(default_factory=dict)
    sensor_drifts: Dict[str, float] = field(default_factory=dict)


@dataclass
class SimulationState:
    """Master Simulation Composite State Container (Supports Independent Twin Engines & Aircraft)."""
    simulation_id: str = "sim_0000"
    scenario_id: FaultScenario = FaultScenario.NONE
    random_seed: int = 42
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    flight: FlightState = field(default_factory=FlightState)
    aircraft: AircraftState = field(default_factory=AircraftState)
    engines: Dict[int, EngineState] = field(default_factory=dict)
    propellers: Dict[int, PropellerState] = field(default_factory=dict)
    thermals: Dict[int, ThermalState] = field(default_factory=dict)
    lubrication: Dict[int, LubricationState] = field(default_factory=dict)
    electrical: ElectricalState = field(default_factory=ElectricalState)
    battery: BatteryState = field(default_factory=BatteryState)
    vibration: Dict[int, VibrationState] = field(default_factory=dict)
    degradation: Dict[int, DegradationState] = field(default_factory=dict)
    thermodynamics: Dict[int, ThermodynamicState] = field(default_factory=dict)
    sensors: SensorState = field(default_factory=SensorState)


@dataclass
class TelemetryState:
    """Exported Telemetry Container (Published & Logged)."""
    timestamp_utc: float
    simulation_time_sec: float
    mission_elapsed_sec: float
    mission_phase: str
    altitude_m: float
    ambient_temp_k: float
    ambient_pressure_pa: float
    air_density_kg_m3: float
    relative_humidity_percent: float
    wind_speed_m_s: float
    airspeed_m_s: float
    aircraft_mass_kg: float
    throttle_percent: float
    engine_rpm: float
    engine_rpm_rad_per_sec: float
    manifold_pressure_pa: float
    cht_cyl1_degc: float
    cht_cyl2_degc: float
    cht_cyl3_degc: float
    cht_cyl4_degc: float
    egt_cyl1_degc: float
    egt_cyl2_degc: float
    egt_cyl3_degc: float
    egt_cyl4_degc: float
    oil_pressure_bar: float
    oil_pressure_pa: float
    oil_temperature_degc: float
    oil_temperature_k: float
    fuel_flow_kg_h: float
    fuel_flow_kg_s: float
    air_fuel_ratio: float
    vibration_rms_m_s2: float
    battery_voltage_v: float
    alternator_current_a: float
    injection_timing_deg_btdc: float
    brake_thermal_efficiency_percent: float
    degradation_bearing: float
    degradation_injector: float
    degradation_ring: float
    simulation_id: str
    scenario_id: str
    random_seed: int
    fault_scenario_id: str
    physical_origin: str = PhysicalOrigin.SIMULATOR.value
    state_category: str = StateCategory.SIMULATED.value
    processing_context: str = ProcessingContext.SYNTHETIC_GENERATION.value
