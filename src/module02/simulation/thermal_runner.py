"""
Module 02 Dynamic CHT Thermal, EGT, Oil Viscosity & Friction Integration Runner (Phase 3.5 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Any, Dict, Optional, Tuple
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.models.states import EngineState, LubricationState, SimulationState, ThermalState
from src.module02.physics.thermal_lubrication import ThermalLubricationModel


class ThermalRunner:
    """
    Integration Runner for Phase 3.5 Dynamic CHT Thermal, EGT, Oil Sump Temperature,
    Vogel Dynamic Oil Viscosity, and Viscosity-Modified Friction Physics.
    Streams configuration values strictly from ConfigLoader without hardcoded Python defaults.
    """

    def __init__(self, clock: Optional[SimulationClock] = None, engine_config: Optional[Dict[str, Any]] = None) -> None:
        self.clock = clock if clock is not None else SimulationClock()
        self.state = SimulationState()
        self.engine_config = engine_config if engine_config is not None else ConfigLoader.load_engine_config()
        self._initialize_twin_engines()

    def _initialize_twin_engines(self) -> None:
        """Initializes independent EngineState, ThermalState, and LubricationState for Engine 1 and Engine 2."""
        self.state.engines[1] = EngineState(engine_index=1, engine_id="engine_left")
        self.state.engines[2] = EngineState(engine_index=2, engine_id="engine_right")
        self.state.thermals[1] = ThermalState()
        self.state.thermals[2] = ThermalState()
        self.state.lubrication[1] = LubricationState()
        self.state.lubrication[2] = LubricationState()

    def step_thermal(
        self,
        engine_index: int,
        fuel_energy_rate_w: float,
        indicated_power_w: float,
        exhaust_energy_rate_w: float,
        exhaust_temp_k: float,
        engine_rpm: float,
        engine_friction_torque_n_m: float,
        airspeed_m_s: float = 0.0,
        ambient_temp_k: float = 288.15,
        engine_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[EngineState, ThermalState, LubricationState]:
        """
        Executes one deterministic thermal and lubrication physics integration step for a specific engine instance.
        Modifying Engine 1 NEVER modifies Engine 2 state.
        """
        if engine_index not in self.state.engines:
            self.state.engines[engine_index] = EngineState(engine_index=engine_index, engine_id=f"engine_{engine_index}")
            self.state.thermals[engine_index] = ThermalState()
            self.state.lubrication[engine_index] = LubricationState()

        eng = self.state.engines[engine_index]
        therm = self.state.thermals[engine_index]
        lub = self.state.lubrication[engine_index]
        cfg = engine_config if engine_config is not None else self.engine_config

        # Extract configuration values strictly via ConfigLoader schema
        m_cyl = cfg["thermal"]["cylinder_thermal_mass_kg"]["value"]
        cp_cyl = cfg["thermal"]["cylinder_specific_heat_j_kg_k"]["value"]
        f_wall = cfg["thermal"]["wall_heat_fraction"]["value"]
        a_cyl = cfg["thermal"]["cooling_surface_area_m2"]["value"]
        h_base = cfg["thermal"]["cooling_coeff_base_w_m2_k"]["value"]
        tau_egt = cfg["thermal"]["egt_sensor_time_constant_sec"]["value"]

        m_oil = cfg["lubrication"]["oil_mass_kg"]["value"]
        cp_oil = cfg["lubrication"]["oil_specific_heat_j_kg_k"]["value"]
        t_ref_oil = cfg["lubrication"]["reference_oil_temperature_k"]["value"]
        mu_ref_oil = cfg["lubrication"]["reference_viscosity_pa_s"]["value"]
        b_visc = cfg["lubrication"]["viscosity_temperature_coeff_k"]["value"]
        h_oil_cooler = cfg["lubrication"]["oil_cooler_coeff_w_k"]["value"]

        f_stat = cfg["friction_and_mechanical"]["friction_static_n_m"]["value"]
        f_visc = cfg["friction_and_mechanical"]["friction_viscous_n_m_s_rad"]["value"]
        f_hydro = cfg["friction_and_mechanical"]["friction_hydrodynamic_n_m_s2_rad2"]["value"]

        # Initialize ambient temperature baseline on startup if uninitialized
        if therm.cht_k < ambient_temp_k and eng.operating_state == eng.operating_state.OFF:
            therm.cht_k = ambient_temp_k
            therm.egt_k = ambient_temp_k
            lub.oil_temperature_k = ambient_temp_k

        # 1. Heat Partitioning
        q_wall, q_loss = ThermalLubricationModel.compute_heat_partition(
            fuel_energy_rate_w=fuel_energy_rate_w,
            indicated_power_w=indicated_power_w,
            exhaust_energy_rate_w=exhaust_energy_rate_w,
            wall_heat_fraction=f_wall
        )

        # 2. CHT Dynamics Integration
        new_cht_k, q_cooling_w, _ = ThermalLubricationModel.step_cht_and_cooling(
            current_cht_k=therm.cht_k,
            wall_heat_generation_w=q_wall,
            ambient_temp_k=ambient_temp_k,
            airspeed_m_s=airspeed_m_s,
            engine_rpm=engine_rpm,
            cylinder_thermal_mass_kg=m_cyl,
            cylinder_specific_heat_j_kg_k=cp_cyl,
            cooling_surface_area_m2=a_cyl,
            cooling_coeff_base_w_m2_k=h_base,
            dt_seconds=self.clock.dt_seconds
        )

        # 3. Dynamic EGT Sensor First-Order Response
        new_egt_k = ThermalLubricationModel.compute_dynamic_egt(
            current_egt_k=therm.egt_k,
            exhaust_temp_k=exhaust_temp_k,
            egt_sensor_time_constant_sec=tau_egt,
            dt_seconds=self.clock.dt_seconds
        )

        # 4. Oil Sump Thermal Integration
        omega = engine_rpm * (3.141592653589793 / 30.0)
        p_friction_w = abs(engine_friction_torque_n_m) * omega

        new_oil_temp_k, q_oil_gen, q_oil_cool = ThermalLubricationModel.step_oil_temperature(
            current_oil_temp_k=lub.oil_temperature_k,
            current_cht_k=new_cht_k,
            friction_power_w=p_friction_w,
            ambient_temp_k=ambient_temp_k,
            oil_mass_kg=m_oil,
            oil_specific_heat_j_kg_k=cp_oil,
            oil_cooler_coeff_w_k=h_oil_cooler,
            dt_seconds=self.clock.dt_seconds
        )

        # 5. Vogel Viscosity-Temperature Physics
        new_oil_viscosity_pa_s = ThermalLubricationModel.compute_oil_viscosity(
            oil_temperature_k=new_oil_temp_k,
            reference_oil_temperature_k=t_ref_oil,
            reference_viscosity_pa_s=mu_ref_oil,
            viscosity_temperature_coeff_k=b_visc
        )

        # 6. Viscosity-Modified Engine Friction Torque
        total_fric_n_m, visc_contrib_n_m = ThermalLubricationModel.compute_viscosity_modified_friction_torque(
            engine_rpm=engine_rpm,
            oil_viscosity_pa_s=new_oil_viscosity_pa_s,
            friction_static_n_m=f_stat,
            friction_viscous_n_m_s_rad=f_visc,
            friction_hydrodynamic_n_m_s2_rad2=f_hydro,
            reference_viscosity_pa_s=mu_ref_oil
        )

        # Update Containers
        therm.cht_k = new_cht_k
        therm.egt_k = new_egt_k
        therm.wall_heat_generation_w = q_wall
        therm.cooling_heat_rejection_w = q_cooling_w

        lub.oil_temperature_k = new_oil_temp_k
        lub.oil_viscosity_pa_s = new_oil_viscosity_pa_s
        lub.oil_heat_generation_w = q_oil_gen
        lub.oil_heat_rejection_w = q_oil_cool
        lub.viscosity_friction_contribution_n_m = visc_contrib_n_m

        eng.friction_torque_n_m = total_fric_n_m

        return (eng, therm, lub)
