"""
Expected Behavior Physics Model — Adapter/Interface Extracting Expected Physical States from Module 01.
SIH26054 — Module 03 Digital Twin Core.
"""

from typing import Any, Dict, Optional

from src.digital_twin.models.healthy_expected_state import HealthyExpectedState


class ExpectedBehaviorModel:
    """
    Adapter and interface layer extracting HealthyExpectedState parameters directly from Module 01 physics state.
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
        rpm_val = getattr(engine_dyn, "engine_rpm", 0.0)
        torque_val = getattr(engine_dyn, "indicated_torque_nm", 0.0)
        gearbox_val = getattr(engine_dyn, "propeller_rpm", rpm_val / 2.4286)

        # Turbo & Airflow
        map_pa = getattr(turbo, "manifold_pressure_pa", 101325.0)
        map_val = map_pa / 100000.0  # Convert Pa to bar
        
        # Turbo speed is in rad/s, map to RPM (rad/s * 60 / 2pi)
        turbo_rad_s = getattr(turbo, "turbo_speed_rad_s", 0.0)
        turbo_val = turbo_rad_s * 60.0 / (2.0 * 3.1415926535)

        air_val = getattr(airflow, "air_mass_flow_kg_s", 0.0) * 3600.0

        # Combustion
        fuel_val = getattr(combustion, "fuel_mass_flow_kg_s", 0.0) * 3600.0
        afr_val = getattr(combustion, "air_fuel_ratio", 14.7)
        comb_eff = getattr(combustion, "combustion_efficiency", 0.0)
        
        # Disambiguation:
        # combustion_energy in Joules is unavailable. heat_release_power_w is Watts.
        comb_energy_val = None

        ind_power = getattr(combustion, "indicated_power_w", 0.0) / 1000.0 # Convert W to kW
        
        egt_val = getattr(combustion, "exhaust_temperature_k", 288.15) - 273.15

        # Thermal
        cht_val = getattr(thermal, "cht_temperature_c", 15.0)
        oil_temp_val = getattr(thermal, "oil_temperature_c", 15.0)

        # Not provided by Phase 1 simulator; explicit contract as unmodeled
        oil_press_val = None
        coolant_temp_val = None

        # Environment / Derived
        amb_press_pa = getattr(atm, "pressure_pa", 101325.0)
        turbo_boost_val = max(0.0, map_val - (amb_press_pa / 100000.0))



        confidence_val = 1.0 if sim_state is not None else 0.0

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
