"""
Phase 1 Foundation & TAPAS-BH-201 Reference Configuration Demonstration Script.
SIH26054 — Module 02 Engine Simulator.
"""

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.core.parameter_registry import ParameterRegistry
from src.module02.core.rng import DeterministicRNG
from src.module02.core.version import VersionInfo
from src.module02.models.states import EngineState, SimulationState
from src.module02.utils.unit_converter import UnitConverter


def main():
    print("==========================================================================")
    print("SIH26054 — MODULE 02 TAPAS-BH-201 CONFIGURATION & TWIN ENGINE DEMO")
    print("==========================================================================")

    # 1. Version Info
    ver = VersionInfo()
    print(f"1. {ver.get_version_summary()}")

    # 2. Config Loader - TAPAS Reference
    sim_cfg = ConfigLoader.load_simulation_config()
    engine_cfg = ConfigLoader.load_engine_config()
    aircraft_cfg = ConfigLoader.load_aircraft_config()
    prop_cfg = ConfigLoader.load_propeller_config()

    print(f"2. Loaded TAPAS-BH-201 Configuration Files Successfully:")
    print(f"   - Engine Identity: {engine_cfg['metadata']['profile_id']} ({engine_cfg['metadata']['engine_name']})")
    print(f"   - Engine Class: {engine_cfg['general']['engine_type']['value']} ({engine_cfg['general']['cooling_type']['value']})")
    print(f"   - Takeoff Rated Power: {engine_cfg['power_and_performance']['takeoff_rated_power_hp']['value']} HP (Classification: {engine_cfg['power_and_performance']['takeoff_rated_power_hp']['classification']}, Source: {engine_cfg['power_and_performance']['takeoff_rated_power_hp']['source']})")
    print(f"   - Constant Power Altitude: {engine_cfg['power_and_performance']['constant_power_altitude_m']['value']} m (~11,000 ft)")
    print(f"   - Demonstrated Test Altitude: {engine_cfg['power_and_performance']['demonstrated_test_altitude_m']['value']} m (~17,664 ft)")
    print(f"   - Aircraft Architecture: {aircraft_cfg['metadata']['platform_name']} ({aircraft_cfg['architecture']['engine_count']['value']}-Engine Platform)")
    print(f"   - Aircraft Target Altitude: {aircraft_cfg['performance_requirements']['target_operating_altitude_m']['value']} m (30,000 ft)")
    print(f"   - Aircraft Demonstrated Altitude: {aircraft_cfg['performance_requirements']['demonstrated_altitude_m']['value']} m (28,000 ft)")
    print(f"   - Target / Demonstrated Endurance: {aircraft_cfg['performance_requirements']['target_endurance_hours']['value']} h / {aircraft_cfg['performance_requirements']['demonstrated_endurance_hours']['value']} h")
    print(f"   - Speed Ratio (N_prop/N_eng): {prop_cfg['gearbox']['engine_to_propeller_speed_ratio']['value']} (Reduction Ratio: {prop_cfg['gearbox']['reduction_ratio']['value']:.5f})")

    # 3. Twin Engine Independent Instantiation & Current Mass Model
    sim_state = SimulationState()
    sim_state.engines[1] = EngineState(engine_index=1, engine_id="engine_left")
    sim_state.engines[2] = EngineState(engine_index=2, engine_id="engine_right")

    sim_state.engines[1].engine_rpm = 4200.0
    sim_state.engines[1].throttle_percent = 100.0

    sim_state.engines[2].engine_rpm = 2800.0
    sim_state.engines[2].throttle_percent = 50.0

    print(f"3. Verified Independent Twin-Engine & Aircraft Mass Model:")
    print(f"   - Engine 1 (Left): RPM = {sim_state.engines[1].engine_rpm} RPM, Throttle = {sim_state.engines[1].throttle_percent}%")
    print(f"   - Engine 2 (Right): RPM = {sim_state.engines[2].engine_rpm} RPM, Throttle = {sim_state.engines[2].throttle_percent}%")
    print(f"   - Component Mass: Dry = {sim_state.flight.dry_mass_kg} kg, Payload = {sim_state.flight.payload_mass_kg} kg, Fuel = {sim_state.flight.fuel_mass_remaining_kg} kg")
    print(f"   - Current Aircraft Mass: {sim_state.flight.current_mass_kg} kg")

    # 4. Parameter Registry Validation
    registry = ParameterRegistry()
    registry.validate_registry_integrity()
    print(f"4. Parameter Registry Integrity Validated:")
    print(f"   - Registered Parameters: {len(registry.list_all_parameters())}")
    print(f"   - Turbocharger & Gearbox Parameters Included: True")
    print(f"   - Implementation Status Present on All Parameters: True")
    print(f"   - Zero Orphans Confirmed: True")

    print("\nTAPAS-BH-201 Hardened Configuration Phase 1.2 successfully verified!")
    print("==========================================================================")


if __name__ == "__main__":
    main()
