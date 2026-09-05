from typing import List
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.faults.fault_scenario import FaultScenario

class FaultInjector:
    """
    Phase 4: Fault & Degradation Injection Layer.
    Translates HealthyExpectedState into a degraded ObservedState based on configured FaultScenarios.
    """

    def inject(self, expected: HealthyExpectedState, scenarios: List[FaultScenario], timestamp: float) -> ObservedState:
        """
        Creates an ObservedState from a HealthyExpectedState, applying configured phenomenological faults.
        
        Args:
            expected: The physics-based baseline healthy state (Phase 1).
            scenarios: List of active FaultScenarios.
            timestamp: The current simulation timestamp.
            
        Returns:
            ObservedState: The fault-injected telemetry data.
        """
        # 1. Base initialization from expected state
        obs = ObservedState(
            timestamp=timestamp,
            sequence_number=expected.sequence_number,
            engine_id=expected.engine_id,
            aircraft_id=expected.aircraft_id,
            data_quality="GOOD"
        )
        
        # Populate all parameters from expected
        obs.rpm = expected.rpm
        obs.map_bar = expected.map_bar
        obs.turbo_rpm = expected.turbo_rpm
        obs.airflow_kg_h = expected.airflow_kg_h
        obs.fuel_flow_kg_h = expected.fuel_flow_kg_h
        obs.afr = expected.afr
        obs.combustion_energy = expected.combustion_energy
        obs.combustion_efficiency = expected.combustion_efficiency
        obs.indicated_power_kw = expected.indicated_power_kw
        obs.torque_n_m = expected.torque_n_m
        obs.egt_c = expected.egt_c
        obs.cht_c = expected.cht_c
        obs.coolant_temp_c = expected.coolant_temp_c
        obs.oil_temp_c = expected.oil_temp_c
        obs.oil_pressure_bar = expected.oil_pressure_bar
        obs.turbo_boost_bar = expected.turbo_boost_bar
        obs.gearbox_rpm = expected.gearbox_rpm
        obs.propeller_load_nm = expected.propeller_load_nm
        obs.thrust_n = expected.thrust_n

        # Environmental parameters are generally passed via OperatingContext, so we leave them None
        # or they can be manually merged later if necessary.

        
        # Determine valid sensors count for baseline
        valid_count = 0
        for param in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                      "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                      "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                      "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
            if getattr(obs, param) is not None:
                valid_count += 1
        obs.valid_sensors_count = valid_count

        # 2. Apply active faults
        for scenario in scenarios:
            eff_sev = self._calculate_effective_severity(scenario, timestamp)
            if eff_sev <= 0.0:
                continue

            # Phenomenological deviation constants (Simulation Assumptions)
            if scenario.fault_type == "COOLING_DEGRADATION":
                # Elevate CHT by up to 50 deg C
                if obs.cht_c is not None:
                    obs.cht_c += (eff_sev * 50.0)
                # Correlated oil temp increase by up to 20 deg C
                if obs.oil_temp_c is not None:
                    obs.oil_temp_c += (eff_sev * 20.0)

            elif scenario.fault_type == "LUBRICATION_DEGRADATION":
                # Reduce oil pressure by up to 2.0 bar (clip at 0.0)
                if obs.oil_pressure_bar is not None:
                    obs.oil_pressure_bar = max(0.0, obs.oil_pressure_bar - (eff_sev * 2.0))
                # Increase oil temp by up to 15 deg C
                if obs.oil_temp_c is not None:
                    obs.oil_temp_c += (eff_sev * 15.0)

            elif scenario.fault_type == "AIRFLOW_RESTRICTION":
                # Reduce airflow up to 50%
                if obs.airflow_kg_h is not None:
                    obs.airflow_kg_h *= (1.0 - (eff_sev * 0.5))
                # Corresponding MAP drop up to 40%
                if obs.map_bar is not None:
                    obs.map_bar *= (1.0 - (eff_sev * 0.4))
                # Corresponding power drop up to 40%
                if obs.indicated_power_kw is not None:
                    obs.indicated_power_kw *= (1.0 - (eff_sev * 0.4))

            elif scenario.fault_type == "TORQUE_DEGRADATION":
                # Reduce torque up to 30%
                if obs.torque_n_m is not None:
                    obs.torque_n_m *= (1.0 - (eff_sev * 0.3))
                # Resulting thrust reduction up to 30%
                if obs.thrust_n is not None:
                    obs.thrust_n *= (1.0 - (eff_sev * 0.3))

        return obs

    def _calculate_effective_severity(self, scenario: FaultScenario, timestamp: float) -> float:
        """Calculates the linearly interpolated severity based on start_time and ramp_duration."""
        if not scenario.enabled or timestamp < scenario.start_time:
            return 0.0
            
        # Limit severity between 0.0 and 1.0
        target_sev = max(0.0, min(1.0, scenario.severity))

        if scenario.ramp_duration <= 0.0:
            return target_sev
            
        elapsed = timestamp - scenario.start_time
        progress = min(1.0, elapsed / scenario.ramp_duration)
        return target_sev * progress
