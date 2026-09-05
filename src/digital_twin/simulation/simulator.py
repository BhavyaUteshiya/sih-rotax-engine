"""
Digital Twin Simulation Orchestrator
SIH26054 — Digital Twin Core

Orchestrates the execution of Phase 1A-1G physics models in the correct causal 
dependency order for a single explicit timestep.
"""

from .state import SimulationState, SimulationInput

from ..physics.atmosphere import AtmosphereModel, EnvironmentInput, AtmosphericState
from ..physics.turbo_intake import TurboIntakeModel, TurboState
from ..physics.airflow import AirflowModel, AirflowInput, AirflowState
from ..physics.combustion import CombustionModel, FuelCombustionInput, FuelCombustionState
from ..physics.propeller import PropellerModel, PropellerInput, PropellerState
from ..physics.engine_dynamics import EngineDynamicsModel, EngineDynamicsInput, EngineDynamicsState
from ..physics.thermal import ThermalModel, ThermalInput, ThermalState

class DigitalTwinSimulator:
    def __init__(self, initial_altitude_m: float = 0.0):
        self.time_s = 0.0
        
        # Initialize sub-states to sensible defaults (zero energy / stopped)
        env_input = EnvironmentInput(altitude_m=initial_altitude_m)
        self.state_atmosphere = AtmosphereModel.calculate(env_input)
        
        self.state_turbo = TurboState(
            turbo_speed_rad_s=0.0,
            manifold_pressure_pa=self.state_atmosphere.pressure_pa,
            manifold_temperature_k=self.state_atmosphere.temperature_k,
            wastegate_position=0.0,
            tcu_error_integral=0.0
        )
        
        self.state_airflow = AirflowState(
            air_mass_flow_kg_s=0.0,
            charge_density_kg_m3=self.state_atmosphere.density_kg_m3,
            volumetric_efficiency=0.0,
            effective_throttle_area_m2=0.0,
            intake_restriction_mass_flow_kg_s=0.0,
            cylinder_filling_mass_flow_kg_s=0.0,
            charge_pressure_pa=self.state_atmosphere.pressure_pa,
            charge_temperature_k=self.state_atmosphere.temperature_k
        )
        
        self.state_combustion = FuelCombustionState(
            fuel_mass_flow_kg_s=0.0, fuel_volume_flow_l_h=0.0, air_fuel_ratio=float('inf'),
            equivalence_ratio=0.0, fuel_pressure_delta_pa=0.0, fuel_pressure_status='NORMAL',
            combustion_efficiency=0.0, chemical_energy_power_w=0.0, heat_release_power_w=0.0,
            indicated_power_w=0.0, unreleased_power_w=0.0, exhaust_sensible_power_w=0.0,
            heat_loss_power_w=0.0, mass_fraction_burned=0.0, burn_duration_deg=0.0,
            exhaust_mass_flow_kg_s=0.0, exhaust_temperature_k=self.state_atmosphere.temperature_k,
            exhaust_pressure_pa=self.state_atmosphere.pressure_pa
        )
        
        self.state_propeller = PropellerState(
            advance_ratio=0.0, thrust_coefficient=0.0, torque_coefficient=0.0,
            thrust_n=0.0, aerodynamic_torque_nm=0.0, absorbed_power_w=0.0, efficiency=0.0
        )
        
        self.state_dynamics = EngineDynamicsState(
            engine_angular_speed_rad_s=0.0, engine_rpm=0.0, indicated_torque_nm=0.0,
            friction_torque_nm=0.0, starter_torque_nm=0.0, propeller_load_torque_nm=0.0,
            net_torque_nm=0.0, angular_acceleration_rad_s2=0.0, shaft_power_w=0.0, propeller_rpm=0.0
        )
        
        self.state_thermal = ThermalState(
            cht_temperature_k=self.state_atmosphere.temperature_k,
            oil_temperature_k=self.state_atmosphere.temperature_k,
            cht_temperature_c=self.state_atmosphere.temperature_c,
            oil_temperature_c=self.state_atmosphere.temperature_c,
            cht_heat_input_w=0.0, heat_cht_to_oil_w=0.0, cht_cooling_w=0.0,
            oil_cooling_w=0.0, dcht_dt_k_s=0.0, doil_dt_k_s=0.0
        )

    def get_state(self) -> SimulationState:
        return SimulationState(
            time_s=self.time_s,
            atmosphere=self.state_atmosphere,
            turbo=self.state_turbo,
            airflow=self.state_airflow,
            combustion=self.state_combustion,
            propeller=self.state_propeller,
            engine_dynamics=self.state_dynamics,
            thermal=self.state_thermal
        )

    def step(self, sim_input: SimulationInput) -> SimulationState:
        """
        Advances the entire Phase 1 digital twin physics by one timestep.
        """
        dt = sim_input.timestep_s
        if dt <= 0.0:
            raise ValueError("Timestep must be strictly positive (> 0).")
            
        # 1. ATMOSPHERE (1A)
        # Driven entirely by environmental inputs
        env_in = EnvironmentInput(
            altitude_m=sim_input.altitude_m,
            ambient_temp_c=sim_input.ambient_temp_c,
            temperature_offset_k=sim_input.temperature_offset_k,
            relative_humidity_pct=sim_input.relative_humidity_pct
        )
        self.state_atmosphere = AtmosphereModel.calculate(env_in)
        
        # 2. TURBO INTAKE (1B)
        # Driven by current atmosphere and previous exhaust state
        from ..physics.turbo_intake import ExhaustState
        
        exh = ExhaustState(
            pressure_pa=self.state_combustion.exhaust_pressure_pa,
            temperature_k=self.state_combustion.exhaust_temperature_k,
            mass_flow_kg_s=self.state_combustion.exhaust_mass_flow_kg_s
        )
        
        # Prototype calibration target; it is supplied at the simulation
        # boundary and is not an official engine specification.
        target_map = sim_input.target_map_at_full_throttle_pa * sim_input.throttle_position
        # Keep a physical minimum
        target_map = max(self.state_atmosphere.pressure_pa * 0.5, target_map)

        self.state_turbo = TurboIntakeModel.step(
            dt=dt,
            atm=self.state_atmosphere,
            exh=exh,
            engine_mass_flow_kg_s=self.state_airflow.air_mass_flow_kg_s,
            target_map_pa=target_map,
            current_state=self.state_turbo
        )
        
        # 3. AIRFLOW (1C)
        # Driven by current engine RPM and updated turbo manifold state
        airflow_in = AirflowInput(
            engine_rpm=self.state_dynamics.engine_rpm,
            manifold_pressure_pa=self.state_turbo.manifold_pressure_pa,
            manifold_temperature_k=self.state_turbo.manifold_temperature_k,
            throttle_position=sim_input.throttle_position
        )
        self.state_airflow = AirflowModel.calculate(airflow_in)
        
        # 4. COMBUSTION (1D)
        # Driven by airflow and current RPM
        combustion_in = FuelCombustionInput(
            engine_rpm=self.state_dynamics.engine_rpm,
            throttle_position=sim_input.throttle_position,
            manifold_pressure_pa=self.state_turbo.manifold_pressure_pa,
            manifold_temperature_k=self.state_turbo.manifold_temperature_k,
            air_mass_flow_kg_s=self.state_airflow.air_mass_flow_kg_s,
            ambient_pressure_pa=self.state_atmosphere.pressure_pa,
            fuel_pressure_pa=sim_input.fuel_pressure_pa,
            fuel_pressure_delta_pa=sim_input.fuel_pressure_delta_pa
        )
        self.state_combustion = CombustionModel.calculate(combustion_in)
        
        # 5. PROPELLER (1F)
        # Calculates current aerodynamic torque based on current propeller RPM and airspeed
        prop_in = PropellerInput(
            propeller_rpm=self.state_dynamics.propeller_rpm,
            airspeed_m_s=sim_input.airspeed_m_s,
            ambient_density_kg_m3=self.state_atmosphere.density_kg_m3,
            propeller_diameter_m=sim_input.propeller_diameter_m
        )
        self.state_propeller = PropellerModel.calculate(prop_in)
        
        # 6. ENGINE DYNAMICS (1E)
        # Consumes indicated power and propeller aerodynamic torque; integrates to find NEXT RPM.
        dynamics_in = EngineDynamicsInput(
            engine_angular_speed_rad_s=self.state_dynamics.engine_angular_speed_rad_s,
            indicated_power_w=self.state_combustion.indicated_power_w,
            starter_engaged=sim_input.starter_engaged,
            timestep_s=dt,
            propeller_load_torque_nm=self.state_propeller.aerodynamic_torque_nm
        )
        self.state_dynamics = EngineDynamicsModel.calculate(dynamics_in)
        
        # 7. THERMAL (1G)
        # Integrates temperatures based on combustion heat loss and airflow
        thermal_in = ThermalInput(
            cht_temperature_k=self.state_thermal.cht_temperature_k,
            oil_temperature_k=self.state_thermal.oil_temperature_k,
            heat_loss_power_w=self.state_combustion.heat_loss_power_w,
            ambient_temperature_k=self.state_atmosphere.temperature_k,
            ambient_density_kg_m3=self.state_atmosphere.density_kg_m3,
            airspeed_m_s=sim_input.airspeed_m_s,
            engine_rpm=self.state_dynamics.engine_rpm,
            timestep_s=dt
        )
        self.state_thermal = ThermalModel.calculate(thermal_in)
        
        # Advance clock
        self.time_s += dt
        
        return self.get_state()
