"""
Validation tests for the Phase 1A Atmosphere Model.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.digital_twin.physics.atmosphere import AtmosphereModel, EnvironmentInput

def assert_approx(name, actual, expected, tolerance=0.01):
    diff = abs(actual - expected)
    if diff <= tolerance:
        print(f"[PASS] {name}: {actual:.4f} == {expected:.4f} (tol: {tolerance})")
    else:
        print(f"[FAIL] {name}: {actual:.4f} != {expected:.4f} (diff: {diff:.4f} > {tolerance})")

def test_sea_level_isa():
    print("\n--- Testing Sea Level ISA ---")
    env = EnvironmentInput(altitude_m=0.0)
    state = AtmosphereModel.calculate(env)
    
    assert_approx("Temperature (C)", state.temperature_c, 15.0)
    assert_approx("Pressure (Pa)", state.pressure_pa, 101325.0)
    assert_approx("Density (kg/m3)", state.density_kg_m3, 1.225)

def test_altitude_pressure_drop():
    print("\n--- Testing Altitude Pressure Drop (Monotonicity) ---")
    prev_pressure = 101325.0
    for alt in [1000, 3000, 5000, 9144]: # 9144m is approx 30,000 ft
        env = EnvironmentInput(altitude_m=alt)
        state = AtmosphereModel.calculate(env)
        if state.pressure_pa < prev_pressure:
            print(f"[PASS] Altitude {alt}m: Pressure {state.pressure_pa:.1f} Pa < {prev_pressure:.1f} Pa")
            prev_pressure = state.pressure_pa
        else:
            print(f"[FAIL] Altitude {alt}m: Pressure {state.pressure_pa:.1f} Pa >= {prev_pressure:.1f} Pa")

def test_temperature_density_relationship():
    print("\n--- Testing Temperature vs Density (Constant Pressure/Altitude) ---")
    # At Sea Level, identical pressure, varying temperature directly
    env_cold = EnvironmentInput(altitude_m=0.0, ambient_temp_c=0.0)
    env_hot = EnvironmentInput(altitude_m=0.0, ambient_temp_c=30.0)
    
    state_cold = AtmosphereModel.calculate(env_cold)
    state_hot = AtmosphereModel.calculate(env_hot)
    
    # Pressure should be identical since altitude is identical
    assert_approx("Pressure identical", state_cold.pressure_pa, state_hot.pressure_pa)
    
    if state_hot.density_kg_m3 < state_cold.density_kg_m3:
        print(f"[PASS] Hot density ({state_hot.density_kg_m3:.4f}) < Cold density ({state_cold.density_kg_m3:.4f})")
    else:
        print(f"[FAIL] Hot density >= Cold density")

def test_humidity_density_relationship():
    print("\n--- Testing Humidity vs Density (Constant Pressure/Temperature) ---")
    # Humid air is less dense than dry air!
    env_dry = EnvironmentInput(altitude_m=0.0, ambient_temp_c=30.0, relative_humidity_pct=0.0)
    env_humid = EnvironmentInput(altitude_m=0.0, ambient_temp_c=30.0, relative_humidity_pct=100.0)
    
    state_dry = AtmosphereModel.calculate(env_dry)
    state_humid = AtmosphereModel.calculate(env_humid)
    
    assert_approx("Vapor Pressure (Dry)", state_dry.vapor_pressure_pa, 0.0)
    if state_humid.vapor_pressure_pa > 0:
        print(f"[PASS] Vapor Pressure (Humid) > 0: {state_humid.vapor_pressure_pa:.1f} Pa")
    else:
        print(f"[FAIL] Vapor Pressure (Humid) is 0")
        
    if state_humid.density_kg_m3 < state_dry.density_kg_m3:
        print(f"[PASS] Humid density ({state_humid.density_kg_m3:.4f}) < Dry density ({state_dry.density_kg_m3:.4f})")
    else:
        print(f"[FAIL] Humid density >= Dry density")

if __name__ == "__main__":
    test_sea_level_isa()
    test_altitude_pressure_drop()
    test_temperature_density_relationship()
    test_humidity_density_relationship()
    print("\nAll physical validation tests completed.")
