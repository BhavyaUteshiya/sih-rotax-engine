"""
Module 02 Standard ISA Atmosphere & Moist Air Physics Subsystem (Phase 2 Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Tuple
from src.module02.models.states import EnvironmentState


class AtmospherePhysicsError(ValueError):
    """Raised when numerical instability or physically invalid atmospheric inputs occur."""
    pass


class AtmosphereModel:
    """
    Standard International Atmosphere (ISA) & Moist Air Thermodynamics Subsystem.
    All calculations strictly use Canonical SI Units (Meters, Kelvin, Pascals, kg/m^3, m/s).
    """

    # Physical Constants (Universal / Standards)
    SEA_LEVEL_TEMP_K: float = 288.15           # 15 °C ISA Sea Level
    SEA_LEVEL_PRESS_PA: float = 101325.0       # 1.01325 bar ISA Sea Level
    SEA_LEVEL_DENSITY_KG_M3: float = 1.225     # ISA Sea Level Density
    LAPSE_RATE_K_PER_M: float = 0.0065         # Troposphere Temperature Lapse Rate (K/m)
    GAS_CONSTANT_DRY_AIR: float = 287.058      # Rd (J/(kg K))
    GAS_CONSTANT_WATER_VAPOR: float = 461.495  # Rv (J/(kg K))
    GAMMA_AIR: float = 1.4                     # Ratio of Specific Heats (Cp/Cv)
    GRAVITY_M_S2: float = 9.80665              # Standard Gravity Acceleration (m/s^2)

    # Physical Safety Floors & Validity Bounds
    MIN_ALTITUDE_M: float = -1000.0
    MAX_ALTITUDE_M: float = 20000.0            # Troposphere / Tropopause boundary
    MIN_TEMP_K: float = 150.0                  # Physical absolute floor
    MIN_PRESS_PA: float = 100.0                # Pressure safety floor
    MIN_DENSITY_KG_M3: float = 0.001           # Density safety floor

    @classmethod
    def validate_inputs(cls, altitude_m: float, temp_offset_k: float = 0.0, relative_humidity_percent: float = 0.0) -> None:
        """Validates numerical safety and physical input boundaries."""
        if math.isnan(altitude_m) or math.isinf(altitude_m):
            raise AtmospherePhysicsError(f"Invalid altitude: {altitude_m}. Cannot be NaN or Inf.")
        if math.isnan(temp_offset_k) or math.isinf(temp_offset_k):
            raise AtmospherePhysicsError(f"Invalid temperature offset: {temp_offset_k}. Cannot be NaN or Inf.")
        if math.isnan(relative_humidity_percent) or math.isinf(relative_humidity_percent):
            raise AtmospherePhysicsError(f"Invalid relative humidity: {relative_humidity_percent}. Cannot be NaN or Inf.")

        if not (cls.MIN_ALTITUDE_M <= altitude_m <= cls.MAX_ALTITUDE_M):
            raise AtmospherePhysicsError(f"Altitude {altitude_m} m out of valid range [{cls.MIN_ALTITUDE_M}, {cls.MAX_ALTITUDE_M}].")

        if not (0.0 <= relative_humidity_percent <= 100.0):
            raise AtmospherePhysicsError(f"Relative humidity {relative_humidity_percent}% out of valid range [0.0, 100.0].")

    @classmethod
    def compute_standard_temperature(cls, altitude_m: float) -> float:
        """Computes ISA Troposphere standard temperature T_standard(h) in Kelvin."""
        h = max(0.0, float(altitude_m))
        if h <= 11000.0:
            # Troposphere lapse rate
            return cls.SEA_LEVEL_TEMP_K - (cls.LAPSE_RATE_K_PER_M * h)
        else:
            # Tropopause isothermal layer (11 km to 20 km)
            t_11km = cls.SEA_LEVEL_TEMP_K - (cls.LAPSE_RATE_K_PER_M * 11000.0)
            return t_11km

    @classmethod
    def compute_actual_temperature(cls, altitude_m: float, temp_offset_k: float = 0.0) -> float:
        """Computes actual ambient temperature T_actual(h) = T_standard(h) + T_offset in Kelvin."""
        t_std = cls.compute_standard_temperature(altitude_m)
        t_act = t_std + float(temp_offset_k)
        if t_act < cls.MIN_TEMP_K:
            raise AtmospherePhysicsError(f"Computed actual temperature {t_act} K below physical safety floor {cls.MIN_TEMP_K} K.")
        return t_act

    @classmethod
    def compute_ambient_pressure(cls, altitude_m: float) -> float:
        """
        Computes static ambient pressure p_amb(h) in Pascals using barometric formula.
        P(h) = P0 * (T(h)/T0)^(g/(R*L)) in Troposphere.
        """
        h = max(0.0, float(altitude_m))
        if h <= 11000.0:
            t_std = cls.compute_standard_temperature(h)
            exponent = cls.GRAVITY_M_S2 / (cls.GAS_CONSTANT_DRY_AIR * cls.LAPSE_RATE_K_PER_M) # ~5.25588
            p_amb = cls.SEA_LEVEL_PRESS_PA * math.pow(t_std / cls.SEA_LEVEL_TEMP_K, exponent)
        else:
            # Tropopause exponential pressure decay
            t_11km = cls.compute_standard_temperature(11000.0)
            exponent_11km = cls.GRAVITY_M_S2 / (cls.GAS_CONSTANT_DRY_AIR * cls.LAPSE_RATE_K_PER_M)
            p_11km = cls.SEA_LEVEL_PRESS_PA * math.pow(t_11km / cls.SEA_LEVEL_TEMP_K, exponent_11km)
            dh = h - 11000.0
            p_amb = p_11km * math.exp(- (cls.GRAVITY_M_S2 * dh) / (cls.GAS_CONSTANT_DRY_AIR * t_11km))

        if p_amb < cls.MIN_PRESS_PA:
            p_amb = cls.MIN_PRESS_PA
        return p_amb

    @classmethod
    def compute_saturation_vapor_pressure(cls, temperature_k: float) -> float:
        """Computes saturation vapor pressure p_sat(T) in Pascals using Magnus-Tetens formula."""
        temp_c = temperature_k - 273.15
        p_sat = 610.78 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        return max(0.0, p_sat)

    @classmethod
    def compute_vapor_pressure(cls, temperature_k: float, relative_humidity_percent: float) -> float:
        """Computes water vapor partial pressure p_v in Pascals."""
        rh = max(0.0, min(100.0, float(relative_humidity_percent)))
        p_sat = cls.compute_saturation_vapor_pressure(temperature_k)
        return (rh / 100.0) * p_sat

    @classmethod
    def compute_moist_air_density(cls, ambient_pressure_pa: float, temperature_k: float, relative_humidity_percent: float = 0.0) -> Tuple[float, float, float]:
        """
        Computes moist air density rho_moist in kg/m^3 via ideal gas mixture law:
        rho = (p_d / (R_d * T)) + (p_v / (R_v * T))
        Returns Tuple of (rho_moist, p_d, p_v).
        """
        p_v = cls.compute_vapor_pressure(temperature_k, relative_humidity_percent)
        p_d = max(0.0, ambient_pressure_pa - p_v)

        rho_dry = p_d / (cls.GAS_CONSTANT_DRY_AIR * temperature_k)
        rho_vapor = p_v / (cls.GAS_CONSTANT_WATER_VAPOR * temperature_k)
        rho_moist = rho_dry + rho_vapor

        if rho_moist < cls.MIN_DENSITY_KG_M3:
            rho_moist = cls.MIN_DENSITY_KG_M3

        return (rho_moist, p_d, p_v)

    @classmethod
    def compute_speed_of_sound(cls, temperature_k: float) -> float:
        """Computes speed of sound a = sqrt(gamma * R_d * T) in m/s."""
        if temperature_k <= 0:
            raise AtmospherePhysicsError(f"Invalid temperature for speed of sound: {temperature_k} K.")
        return math.sqrt(cls.GAMMA_AIR * cls.GAS_CONSTANT_DRY_AIR * temperature_k)

    @classmethod
    def compute_dynamic_pressure(cls, air_density_kg_m3: float, airspeed_m_s: float) -> float:
        """Computes dynamic pressure q = 0.5 * rho * V^2 in Pascals."""
        if air_density_kg_m3 < 0:
            raise AtmospherePhysicsError(f"Negative air density for dynamic pressure: {air_density_kg_m3}.")
        v = abs(float(airspeed_m_s))
        return 0.5 * float(air_density_kg_m3) * (v * v)

    @classmethod
    def compute_environment_snapshot(
        cls,
        altitude_m: float,
        temp_offset_k: float = 0.0,
        relative_humidity_percent: float = 0.0,
        wind_speed_m_s: float = 0.0
    ) -> EnvironmentState:
        """Computes complete, physically consistent EnvironmentState snapshot."""
        cls.validate_inputs(altitude_m, temp_offset_k, relative_humidity_percent)

        t_amb = cls.compute_actual_temperature(altitude_m, temp_offset_k)
        p_amb = cls.compute_ambient_pressure(altitude_m)
        rho_moist, p_d, p_v = cls.compute_moist_air_density(p_amb, t_amb, relative_humidity_percent)
        o2_fraction = 0.2315 * (p_d / p_amb) if p_amb > 0 else 0.2315

        return EnvironmentState(
            altitude_m=float(altitude_m),
            ambient_temp_k=t_amb,
            relative_humidity_percent=float(relative_humidity_percent),
            wind_speed_m_s=float(wind_speed_m_s),
            ambient_pressure_pa=p_amb,
            air_density_kg_m3=rho_moist,
            vapor_pressure_pa=p_v,
            oxygen_mass_fraction=o2_fraction,
        )
