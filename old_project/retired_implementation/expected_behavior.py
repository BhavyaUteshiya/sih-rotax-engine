"""
Expected Behavior Physics Model — Adapter/Interface Extracting Expected Physical States from Module 01.
SIH26054 — Module 03 Digital Twin Core.
"""

from typing import Any, Dict, Optional

from src.digital_twin.models.expected_state import ExpectedState


class ExpectedBehaviorModel:
    """
    Adapter and interface layer extracting ExpectedState parameters directly from Module 01 physics state.
    MANDATE: Does NOT duplicate or re-implement independent physics equations. Reuses authoritative Rotax 914 physics.
    Supports complete 18 internal Category C parameters. Disambiguates combustion_energy, heat_release_rate_w, and combustion_efficiency.
    """

    @classmethod
    def from_simulation_state(
        cls,
        sim_state: Any,
        engine_index: int = 1,
        timestamp: float = 0.0,
        sequence_number: int = 0,
        propeller_state: Optional[Any] = None
    ) -> ExpectedState:
        """
        Maps current Module 01 SimulationState attributes for engine_index into a clean ExpectedState dataclass.
        """
        if sim_state is None:
            return ExpectedState(
                timestamp=timestamp,
                sequence_number=sequence_number,
                engine_id=f"engine_{engine_index}",
                aircraft_id="rotax_914_uav",
                model_confidence=0.0
            )

        e = sim_state.engines.get(engine_index) if hasattr(sim_state, "engines") else None
        t = sim_state.thermodynamics.get(engine_index) if hasattr(sim_state, "thermodynamics") else None
        th = sim_state.thermals.get(engine_index) if hasattr(sim_state, "thermals") else None
        lub = sim_state.lubrication.get(engine_index) if hasattr(sim_state, "lubrication") else None
        env = getattr(sim_state, "environment", None)
        ac = getattr(sim_state, "aircraft", None)

        # Handle Propeller load/thrust if supplied separately or attached
        thrust_val = 0.0
        prop_load_val = 0.0
        if propeller_state is not None:
            thrust_val = getattr(propeller_state, "thrust_n", 0.0)
            prop_load_val = getattr(propeller_state, "load_torque_nm", 0.0)
        elif hasattr(sim_state, "propulsion") and sim_state.propulsion is not None:
            p_map = getattr(sim_state.propulsion, "propellers", {})
            if engine_index in p_map:
                thrust_val = getattr(p_map[engine_index], "thrust_n", 0.0)
                prop_load_val = getattr(p_map[engine_index], "load_torque_nm", 0.0)

        rpm_val = e.engine_rpm if e else 0.0
        map_val = (e.manifold_pressure_pa / 100000.0) if e else 1.01325
        egt_val = (t.egt_k - 273.15) if t else 15.0
        cht_val = (t.cht_k - 273.15) if t else 15.0
        oil_temp_val = (t.oil_temp_k - 273.15) if t else 15.0
        
        # Oil pressure from lubrication runner or dynamic estimate if runner inactive
        oil_press_val = 0.0
        if lub and getattr(lub, "oil_pressure_pa", 0.0) > 0.0:
            oil_press_val = lub.oil_pressure_pa / 100000.0
        elif rpm_val > 2000:
            oil_press_val = 5.0
        elif rpm_val > 500:
            oil_press_val = 3.0

        coolant_temp_val = (t.coolant_temp_k - 273.15) if t else 15.0
        afr_val = e.air_fuel_ratio if e else 14.7
        fuel_val = (e.fuel_mass_flow_kg_s * 3600.0) if e else 0.0
        air_val = (e.air_mass_flow_kg_s * 3600.0) if e else 0.0
        torque_val = e.indicated_torque_total_n_m if e else 0.0
        turbo_val = e.turbocharger.turbo_speed_rpm if (e and hasattr(e, "turbocharger")) else 0.0

        # Disambiguation:
        # 1. combustion_efficiency (dimensionless ratio, 0.0 - 1.0)
        comb_eff = getattr(t, "combustion_efficiency", 0.95) if (t and rpm_val > 100) else 0.0
        # 2. combustion_energy (Joule). Module 01 calculates heat_release_rate_w (Watts / Rate of Energy).
        # heat_release_rate_w is energy release per unit time (Watts), NOT total combustion energy in Joules.
        # Therefore, combustion_energy in Joules is marked None (unavailable) to prevent unit/semantic mislabeling.
        comb_energy_val = None

        ind_power = (getattr(e, "indicated_power_total_w", 0.0) / 1000.0) if e else 0.0
        gear_ratio = getattr(e, "gearbox_ratio", 2.43) if e else 2.43
        gearbox_val = (rpm_val / gear_ratio) if gear_ratio else (rpm_val / 2.43)

        amb_temp_val = (env.ambient_temp_k - 273.15) if env else 15.0
        amb_press_val = (env.ambient_pressure_pa / 1000.0) if env else 101.325
        amb_rho_val = env.air_density_kg_m3 if env else 1.225
        wind_val = getattr(env, "wind_speed_m_s", 0.0) if env else 0.0
        alt_val = ac.altitude_m if ac else 0.0
        speed_val = ac.velocity_m_s if ac else 0.0

        turbo_boost_val = max(0.0, map_val - (amb_press_val / 100.0))
        if prop_load_val == 0.0 and torque_val > 0.0:
            prop_load_val = torque_val / gear_ratio if gear_ratio else torque_val

        return ExpectedState(
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
            airspeed_m_s=speed_val,
            altitude_m=alt_val,
            ambient_temp_c=amb_temp_val,
            ambient_pressure_kpa=amb_press_val,
            ambient_density_kg_m3=amb_rho_val,
            wind_m_s=wind_val,
            model_confidence=1.0
        )
