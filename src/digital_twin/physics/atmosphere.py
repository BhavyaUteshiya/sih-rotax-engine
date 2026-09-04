"""
Phase 1A: Atmosphere Model
SIH26054 — Digital Twin Core

Calculates physically consistent atmospheric state (Pressure, Temperature, Density)
using International Standard Atmosphere (ISA) equations for the Troposphere,
combined with the Magnus formula for water vapor partial pressure to yield
moist air density.
"""

import math
from dataclasses import dataclass

# Universal physical constants
G = 9.80665              # m/s^2 (Standard Gravity)
R_STAR = 8.3144598       # J/(mol K) (Universal gas constant)
M_D = 0.0289644          # kg/mol (Molar mass of dry air)
R_D = R_STAR / M_D       # ~287.0528 J/(kg K) (Specific gas constant for dry air)
R_V = 461.495            # J/(kg K) (Specific gas constant for water vapor)
GAMMA = 1.4              # Heat capacity ratio for dry air

# Standard Atmosphere (ISA) Constants at Sea Level (Troposphere layer)
T0 = 288.15              # K (15 C)
P0 = 101325.0            # Pa
L = 0.0065               # K/m (Temperature lapse rate)
MAX_ISA_ALTITUDE = 11000.0 # m (Top of Troposphere / Tropopause)
EARTH_RADIUS = 6356766.0 # m (Nominal Earth radius for ISA calculations, ICAO Doc 7488)

@dataclass
class EnvironmentInput:
    """Inputs to the Atmosphere Model."""
    altitude_m: float = 0.0
    ambient_temp_c: float = None # If None, ISA standard temperature is used
    temperature_offset_k: float = 0.0 # Used only if ambient_temp_c is None
    relative_humidity_pct: float = 0.0

@dataclass
class AtmosphericState:
    """Outputs of the Atmosphere Model."""
    altitude_m: float
    temperature_c: float
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    vapor_pressure_pa: float
    speed_of_sound_m_s: float

class AtmosphereModel:
    """
    Calculates atmospheric properties deterministically.
    """

    @classmethod
    def calculate(cls, env: EnvironmentInput) -> AtmosphericState:
        """
        Calculates the physical atmospheric state for a given environment input.
        """
        # Constrain altitude to Troposphere limits for standard lapse equations.
        # The Troposphere extends up to ~11000m. A 30,000 ft (~9,144 m) UAV envelope is fully supported.
        if env.altitude_m < 0.0 or env.altitude_m > MAX_ISA_ALTITUDE:
            raise ValueError(f"Altitude {env.altitude_m}m out of valid Troposphere domain (0 to {MAX_ISA_ALTITUDE}m).")
        # 0. Convert Geometric Altitude to Geopotential Altitude
        # Standard atmosphere equations use geopotential altitude to account for decreasing gravity.
        h_geom = env.altitude_m
        h_gp = (EARTH_RADIUS * h_geom) / (EARTH_RADIUS + h_geom)
        
        # 1. Standard Temperature at Altitude
        t_isa_k = T0 - (L * h_gp)
        
        # Determine actual thermodynamic temperature.
        # PRECEDENCE RULE: 
        # 1. If explicit ambient_temp_c is provided (e.g. from telemetry or explicit environment profile), it overrides.
        # 2. Otherwise, use the standard ISA temperature at altitude + offset.
        if env.ambient_temp_c is not None:
            t_actual_k = env.ambient_temp_c + 273.15
        else:
            t_actual_k = t_isa_k + env.temperature_offset_k
            
        # Prevent absolute zero or negative Kelvin (nonphysical condition)
        if t_actual_k <= 0.0:
            raise ValueError(f"Nonphysical absolute temperature: {t_actual_k} K. Must be > 0 K.")
            
        t_actual_c = t_actual_k - 273.15
        
        # 2. Standard Pressure at Altitude
        # P = P0 * (1 - (L * h_gp) / T0) ^ ((g * M) / (R * L))
        exponent = (G * M_D) / (R_STAR * L)
        base = 1.0 - (L * h_gp) / T0
        # Prevent negative base if altitude somehow exceeded constraints wildly
        base = max(1e-6, base)
        p_actual_pa = P0 * math.pow(base, exponent)
        
        # 3. Water Vapor Pressure (Magnus Formula)
        rh = env.relative_humidity_pct
        if rh < 0.0 or rh > 100.0:
            raise ValueError(f"Relative humidity {rh}% is out of valid physical range (0 to 100%).")
            
        if rh > 0.0:
            # Saturation vapor pressure in hPa (Alduchov & Eskridge, 1996)
            # es(T) = 6.1094 * exp(17.625 * T_c / (243.04 + T_c))
            p_sat_hpa = 6.1094 * math.exp((17.625 * t_actual_c) / (243.04 + t_actual_c))
            p_sat_pa = p_sat_hpa * 100.0
            p_v_pa = p_sat_pa * (rh / 100.0)
        else:
            p_v_pa = 0.0
            
        # Ensure vapor pressure doesn't physically exceed total pressure
        p_v_pa = min(p_v_pa, p_actual_pa)
            
        # 4. Moist Air Density
        # rho = (P_dry / (R_d * T)) + (P_v / (R_v * T))
        p_dry_pa = p_actual_pa - p_v_pa
        density_dry = p_dry_pa / (R_D * t_actual_k)
        density_vap = p_v_pa / (R_V * t_actual_k)
        density_total = density_dry + density_vap
        
        # 5. Speed of Sound (approx based on dry air constants for simplicity)
        # a = sqrt(gamma * R_d * T)
        speed_of_sound = math.sqrt(GAMMA * R_D * t_actual_k)
        
        return AtmosphericState(
            altitude_m=env.altitude_m,
            temperature_c=t_actual_c,
            temperature_k=t_actual_k,
            pressure_pa=p_actual_pa,
            density_kg_m3=density_total,
            vapor_pressure_pa=p_v_pa,
            speed_of_sound_m_s=speed_of_sound
        )
