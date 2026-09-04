"""
Expected Behavior Physics Model — Stateful Predictive Engine.
SIH26054 — Module 03 Digital Twin Core.
"""

import math
from typing import Any, Dict, Optional, Tuple

from src.digital_twin.models.expected_state import ExpectedState
from src.digital_twin.models.twin_internal_state import TwinInternalState


class ExpectedBehaviorModel:
    """
    Stateful prediction layer for the Digital Twin.
    Evolves the Twin's internal physical state forward over time (dt) using 
    engineering approximations and first-order lags to represent thermal/rotational inertia.
    """

    @classmethod
    def predict_state(
        cls,
        prev_internal: TwinInternalState,
        operating_context: Dict[str, Any],
        dt: float,
        engine_index: int = 1,
        sequence_number: int = 0
    ) -> Tuple[ExpectedState, TwinInternalState]:
        """
        Evolves the previous internal state over dt and generates the expected output measurements.
        """
        # Time constraints to prevent instability on long pauses
        dt = max(0.001, min(dt, 1.0))
        
        ctx = operating_context or {}
        throttle_pct = float(ctx.get(f"throttle_{engine_index}", 0.0))
        
        # Environmental conditions (can be pulled from context if available, or defaulted)
        amb_temp_val = float(ctx.get("ambient_temp_c", 15.0))
        amb_press_val = float(ctx.get("ambient_pressure_kpa", 101.325))
        amb_rho_val = float(ctx.get("ambient_density_kg_m3", 1.225))
        alt_val = float(ctx.get("altitude_m", 0.0))
        speed_val = float(ctx.get("airspeed_m_s", 0.0))

        # ---------------------------------------------------------
        # [ENGINEERING_APPROXIMATION] Stateful Digital Twin Empirical Models
        # ---------------------------------------------------------
        
        # 1. Target MAP (Manifold Absolute Pressure)
        idle_map = 0.35
        max_map = 1.15
        target_map = idle_map + (max_map - idle_map) * (throttle_pct / 100.0)
        
        # 2. Target RPM
        target_rpm = 1400.0 + (5800.0 - 1400.0) * ((target_map - idle_map) / (max_map - idle_map))
        target_rpm = max(0.0, target_rpm)

        # 3. Evolve states with physical inertia (First-order lag: val += (target - val) * (1 - exp(-dt/tau)))
        tau_map = 0.5   # 0.5s manifold filling lag
        tau_rpm = 1.5   # 1.5s rotational spool up
        
        next_map = prev_internal.map_bar + (target_map - prev_internal.map_bar) * (1.0 - math.exp(-dt / tau_map))
        next_rpm = prev_internal.rpm + (target_rpm - prev_internal.rpm) * (1.0 - math.exp(-dt / tau_rpm))
        
        # Turn off engine if throttle is 0 and RPM drops low
        if throttle_pct < 1.0 and next_rpm < 100:
            next_rpm = 0.0
            next_map = amb_press_val / 100.0  # open to atmosphere when dead

        # 4. Instantaneous / Algebraic constraints derived from state
        turbo_boost_val = max(0.0, next_map - (amb_press_val / 100.0))
        turbo_val = 100000.0 * (throttle_pct / 100.0)
        
        # Airflow and Fuel Flow
        air_val = 350.0 * (next_rpm / 5800.0) * (next_map / 1.15) if next_rpm > 500 else 0.0
        afr_val = 14.7 - 2.0 * (throttle_pct / 100.0)
        fuel_val = air_val / afr_val if afr_val > 0 else 0.0

        # Torque and Power
        torque_val = 135.0 * (next_map / max_map) if next_rpm >= 500 else 0.0
        ind_power = (torque_val * next_rpm * 2 * 3.14159 / 60) / 1000.0

        # 5. Thermal States (EGT, CHT, Oil)
        # EGT reacts fast, CHT/Oil react slowly
        tau_egt = 2.0
        tau_cht = 15.0
        tau_oil = 30.0

        target_egt = 400.0 + 400.0 * (fuel_val / 25.0) if fuel_val > 0 else amb_temp_val
        target_cht = 80.0 + 40.0 * (fuel_val / 25.0) if fuel_val > 0 else amb_temp_val
        target_oil = 80.0 + 30.0 * (fuel_val / 25.0) if fuel_val > 0 else amb_temp_val

        next_egt = prev_internal.egt_c + (target_egt - prev_internal.egt_c) * (1.0 - math.exp(-dt / tau_egt))
        next_cht = prev_internal.cht_c + (target_cht - prev_internal.cht_c) * (1.0 - math.exp(-dt / tau_cht))
        next_oil = prev_internal.oil_temp_c + (target_oil - prev_internal.oil_temp_c) * (1.0 - math.exp(-dt / tau_oil))

        coolant_temp_val = next_cht - 10.0

        # Mechanical Constraints
        if next_rpm > 2000:
            oil_press_val = 5.0
        elif next_rpm > 500:
            oil_press_val = 3.0
        else:
            oil_press_val = 0.0

        comb_eff = 0.95 if next_rpm > 500 else 0.0
        gear_ratio = 2.43
        gearbox_val = next_rpm / gear_ratio
        prop_load_val = torque_val / gear_ratio

        # 6. Create the next Internal State
        new_internal_state = TwinInternalState(
            timestamp=prev_internal.timestamp + dt,
            map_bar=next_map,
            rpm=next_rpm,
            egt_c=next_egt,
            cht_c=next_cht,
            oil_temp_c=next_oil
        )

        # 7. Create the Expected State Output
        expected_output = ExpectedState(
            timestamp=prev_internal.timestamp + dt,
            sequence_number=sequence_number,
            engine_id=f"engine_{engine_index}",
            aircraft_id="rotax_914_uav",
            rpm=next_rpm,
            map_bar=next_map,
            turbo_rpm=turbo_val,
            airflow_kg_h=air_val,
            fuel_flow_kg_h=fuel_val,
            afr=afr_val,
            combustion_energy=None,
            combustion_efficiency=comb_eff,
            indicated_power_kw=ind_power,
            torque_n_m=torque_val,
            egt_c=next_egt,
            cht_c=next_cht,
            coolant_temp_c=coolant_temp_val,
            oil_temp_c=next_oil,
            oil_pressure_bar=oil_press_val,
            turbo_boost_bar=turbo_boost_val,
            gearbox_rpm=gearbox_val,
            propeller_load_nm=prop_load_val,
            thrust_n=0.0,
            airspeed_m_s=speed_val,
            altitude_m=alt_val,
            ambient_temp_c=amb_temp_val,
            ambient_pressure_kpa=amb_press_val,
            ambient_density_kg_m3=amb_rho_val,
            wind_m_s=0.0,
            model_confidence=1.0
        )

        return expected_output, new_internal_state
