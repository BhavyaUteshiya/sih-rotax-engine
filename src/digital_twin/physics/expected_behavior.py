"""
Expected Behavior Physics Model — Adapter/Interface Extracting Expected Physical States from Phase 1 Simulator.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from typing import Any, Dict, Optional

from src.digital_twin.models.healthy_expected_state import HealthyExpectedState


class ExpectedBehaviorModel:
    """
    Adapter and interface layer extracting HealthyExpectedState parameters directly from Phase 1 Simulator physics state.
    MANDATE: Does NOT duplicate or re-implement independent physics equations. Reuses authoritative Rotax 914 physics.
    Supports complete 19 internal Category C parameters. Disambiguates combustion_energy, heat_release_rate_w, and combustion_efficiency.
    """
    @classmethod
    def from_simulation_state(
        cls,
        sim_state: Any,
        engine_index: int = 1,
        timestamp: float = 0.0,
        sequence_number: int = 0,
        propeller_state: Optional[Any] = None
    ) -> HealthyExpectedState:
        """
        Maps current SimulationState attributes for engine_index into a clean HealthyExpectedState dataclass.
        """
        if sim_state is None:
            return HealthyExpectedState(
                timestamp=timestamp,
                sequence_number=sequence_number,
                engine_id=f"engine_{engine_index}",
                aircraft_id="rotax_914_uav",
                model_confidence=0.0
            )

        atm = getattr(sim_state, "atmosphere", None)
        turbo = getattr(sim_state, "turbo", None)
        airflow = getattr(sim_state, "airflow", None)
        combustion = getattr(sim_state, "combustion", None)
        engine_dyn = getattr(sim_state, "engine_dynamics", None)
        thermal = getattr(sim_state, "thermal", None)

        # Propeller handling
        prop = propeller_state if propeller_state is not None else getattr(sim_state, "propeller", None)
        thrust_val = getattr(prop, "thrust_n", None)
        prop_load_val = getattr(prop, "aerodynamic_torque_nm", None)

        # Engine Dynamics & Basic params
        rpm_val = getattr(engine_dyn, "engine_rpm", None)
        torque_val = getattr(engine_dyn, "indicated_torque_nm", None)
        gearbox_val = getattr(engine_dyn, "propeller_rpm", None)

        # Turbo & Airflow
        map_pa = getattr(turbo, "manifold_pressure_pa", None)
        map_val = (map_pa / 100000.0) if map_pa is not None else None
        
        # Turbo speed is in rad/s, map to RPM (rad/s * 60 / 2pi)
        turbo_rad_s = getattr(turbo, "turbo_speed_rad_s", None)
        turbo_val = (turbo_rad_s * 60.0 / (2.0 * 3.1415926535)) if turbo_rad_s is not None else None

        air_val_kg_s = getattr(airflow, "air_mass_flow_kg_s", None)
        air_val = (air_val_kg_s * 3600.0) if air_val_kg_s is not None else None

        # Combustion
        fuel_val_kg_s = getattr(combustion, "fuel_mass_flow_kg_s", None)
        fuel_val = (fuel_val_kg_s * 3600.0) if fuel_val_kg_s is not None else None
        afr_val = getattr(combustion, "air_fuel_ratio", None)
        comb_eff = getattr(combustion, "combustion_efficiency", None)
        
        # Disambiguation:
        # combustion_energy in Joules is unavailable. heat_release_power_w is Watts.
        comb_energy_val = None

        ind_power_w = getattr(combustion, "indicated_power_w", None)
        ind_power = (ind_power_w / 1000.0) if ind_power_w is not None else None
        
        egt_k = getattr(combustion, "exhaust_temperature_k", None)
        egt_val = (egt_k - 273.15) if egt_k is not None else None

        # Thermal
        cht_val = getattr(thermal, "cht_temperature_c", None)
        oil_temp_val = getattr(thermal, "oil_temperature_c", None)

        # Not provided by Phase 1 simulator; explicit contract as unmodeled
        oil_press_val = None
        coolant_temp_val = None

        # Environment / Derived
        amb_press_pa = getattr(atm, "pressure_pa", None)
        if map_val is not None and amb_press_pa is not None:
            turbo_boost_val = max(0.0, map_val - (amb_press_pa / 100000.0))
        else:
            turbo_boost_val = None



        confidence_val = 0.8 if sim_state is not None else 0.0

        return HealthyExpectedState(
            timestamp=timestamp,
            sequence_number=sequence_number,
            engine_id=f"engine_{engine_index}",
            aircraft_id="rotax_914_uav",
            rpm=rpm_val,
            map_bar=map_val,
            turbo_rpm=turbo_val,
            airflow_kg_h=air_val,
            fuel_flow_kg_h=fuel_val,
            afr=afr_val,
            combustion_energy=comb_energy_val,
            combustion_efficiency=comb_eff,
            indicated_power_kw=ind_power,
            torque_n_m=torque_val,
            egt_c=egt_val,
            cht_c=cht_val,
            coolant_temp_c=coolant_temp_val,
            oil_temp_c=oil_temp_val,
            oil_pressure_bar=oil_press_val,
            turbo_boost_bar=turbo_boost_val,
            gearbox_rpm=gearbox_val,
            propeller_load_nm=prop_load_val,
            thrust_n=thrust_val,
            model_confidence=confidence_val
        )
