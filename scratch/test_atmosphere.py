"""
Validation tests for the Phase 1A Atmosphere Model.
"""
import sys
import os
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.digital_twin.physics.atmosphere import AtmosphereModel, EnvironmentInput


class TestAtmosphereModel(unittest.TestCase):
    
    def test_altitude_domain_validation(self):
        """Test that out-of-bounds altitudes raise explicit errors."""
        with self.assertRaises(ValueError):
            AtmosphereModel.calculate(EnvironmentInput(altitude_m=-100.0))
            
        with self.assertRaises(ValueError):
            AtmosphereModel.calculate(EnvironmentInput(altitude_m=12000.0))
            
        # Should not raise
        AtmosphereModel.calculate(EnvironmentInput(altitude_m=11000.0))

    def test_humidity_domain_validation(self):
        """Test that out-of-bounds relative humidity raises explicit errors."""
        with self.assertRaises(ValueError):
            AtmosphereModel.calculate(EnvironmentInput(relative_humidity_pct=-5.0))
            
        with self.assertRaises(ValueError):
            AtmosphereModel.calculate(EnvironmentInput(relative_humidity_pct=105.0))
            
        # Should not raise
        AtmosphereModel.calculate(EnvironmentInput(relative_humidity_pct=100.0))
        AtmosphereModel.calculate(EnvironmentInput(relative_humidity_pct=0.0))

    def test_temperature_domain_validation(self):
        """Test that nonphysical absolute temperature (<= 0K) raises explicit errors."""
        with self.assertRaises(ValueError):
            AtmosphereModel.calculate(EnvironmentInput(ambient_temp_c=-273.15))
            
        with self.assertRaises(ValueError):
            AtmosphereModel.calculate(EnvironmentInput(ambient_temp_c=-300.0))
            
        # Should not raise
        AtmosphereModel.calculate(EnvironmentInput(ambient_temp_c=-272.0))

    def test_sea_level_isa(self):
        """Test exact ISA sea level conditions (0 ft)."""
        env = EnvironmentInput(altitude_m=0.0)
        state = AtmosphereModel.calculate(env)
        
        self.assertAlmostEqual(state.temperature_c, 15.0, delta=0.01)
        self.assertAlmostEqual(state.pressure_pa, 101325.0, delta=0.1)
        self.assertAlmostEqual(state.density_kg_m3, 1.225, delta=0.001)

    def test_quantitative_altitude_profile(self):
        """Test quantitative reference points at specific altitudes against ISA."""
        # 5,000 ft (~1524 m)
        state_5k = AtmosphereModel.calculate(EnvironmentInput(altitude_m=1524.0))
        self.assertAlmostEqual(state_5k.temperature_c, 5.1, delta=0.1)
        self.assertAlmostEqual(state_5k.pressure_pa, 84307.0, delta=50.0)
        
        # 10,000 ft (~3048 m)
        state_10k = AtmosphereModel.calculate(EnvironmentInput(altitude_m=3048.0))
        self.assertAlmostEqual(state_10k.temperature_c, -4.8, delta=0.1)
        self.assertAlmostEqual(state_10k.pressure_pa, 69681.0, delta=50.0)
        
        # 16,000 ft (~4876.8 m)
        state_16k = AtmosphereModel.calculate(EnvironmentInput(altitude_m=4876.8))
        self.assertAlmostEqual(state_16k.temperature_c, -16.7, delta=0.1)
        self.assertAlmostEqual(state_16k.pressure_pa, 54915.0, delta=50.0)
        
        # 30,000 ft (~9144 m)
        state_30k = AtmosphereModel.calculate(EnvironmentInput(altitude_m=9144.0))
        self.assertAlmostEqual(state_30k.temperature_c, -44.4, delta=0.5)
        self.assertAlmostEqual(state_30k.pressure_pa, 30090.0, delta=100.0)

    def test_combinatorial_conditions(self):
        """Test specific quantitative permutations of temp and humidity."""
        
        # 1. Hot (+15K offset) at Sea Level
        env_hot = EnvironmentInput(altitude_m=0.0, temperature_offset_k=15.0)
        state_hot = AtmosphereModel.calculate(env_hot)
        self.assertAlmostEqual(state_hot.temperature_c, 30.0, delta=0.01)
        self.assertAlmostEqual(state_hot.pressure_pa, 101325.0, delta=0.1)
        self.assertLess(state_hot.density_kg_m3, 1.225) # Hotter air is less dense
        
        # 2. Cold (-15K offset) at Sea Level
        env_cold = EnvironmentInput(altitude_m=0.0, temperature_offset_k=-15.0)
        state_cold = AtmosphereModel.calculate(env_cold)
        self.assertAlmostEqual(state_cold.temperature_c, 0.0, delta=0.01)
        self.assertGreater(state_cold.density_kg_m3, 1.225) # Colder air is denser
        
        # 3. Hot and Humid (30 C, 100% RH)
        env_humid = EnvironmentInput(altitude_m=0.0, ambient_temp_c=30.0, relative_humidity_pct=100.0)
        state_humid = AtmosphereModel.calculate(env_humid)
        
        env_dry = EnvironmentInput(altitude_m=0.0, ambient_temp_c=30.0, relative_humidity_pct=0.0)
        state_dry = AtmosphereModel.calculate(env_dry)
        
        # Saturation vapor pressure of water at 30 C is ~42.4 hPa = 4240 Pa
        self.assertGreater(state_humid.vapor_pressure_pa, 4200.0)
        self.assertLess(state_humid.vapor_pressure_pa, 4300.0)
        
        # Humid air must be physically less dense than dry air at the same T and P
        self.assertLess(state_humid.density_kg_m3, state_dry.density_kg_m3)
        
    def test_geopotential_altitude_conversion(self):
        """Test that geometric altitude is correctly converted to geopotential altitude."""
        EARTH_RADIUS = 6356766.0
        
        # Test 10,000m geometric altitude
        h_geom = 10000.0
        h_gp = (EARTH_RADIUS * h_geom) / (EARTH_RADIUS + h_geom)
        
        # Calculate expected using geopotential altitude
        T0 = 288.15
        L = 0.0065
        t_expected_k = T0 - L * h_gp
        
        state = AtmosphereModel.calculate(EnvironmentInput(altitude_m=h_geom))
        
        # Verify the actual temperature exactly matches the geopotential expectation
        self.assertAlmostEqual(state.temperature_k, t_expected_k, places=4)
        
        # Verify it DOES NOT match the naive geometric calculation
        t_naive_k = T0 - L * h_geom
        self.assertNotAlmostEqual(state.temperature_k, t_naive_k, places=4)


if __name__ == "__main__":
    unittest.main()
