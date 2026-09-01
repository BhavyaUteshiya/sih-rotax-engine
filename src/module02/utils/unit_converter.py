"""
Module 02 Canonical SI Unit Conversion Utilities (Phase 1 Foundation).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Tuple


class UnitConversionError(Exception):
    """Raised when an unsupported unit conversion is attempted."""
    pass


class UnitConverter:
    """
    Explicit, bidirectional conversions between display units and canonical SI units.
    All internal physics equations MUST strictly use Canonical SI Units.
    """

    # Constants
    RPM_TO_RAD_PER_SEC = math.pi / 30.0
    RAD_PER_SEC_TO_RPM = 30.0 / math.pi

    CELSIUS_TO_KELVIN_OFFSET = 273.15
    BAR_TO_PASCAL = 100000.0
    PASCAL_TO_BAR = 1.0 / 100000.0

    KG_PER_HOUR_TO_KG_PER_SEC = 1.0 / 3600.0
    KG_PER_SEC_TO_KG_PER_HOUR = 3600.0

    HP_TO_WATTS = 745.699872
    WATTS_TO_HP = 1.0 / 745.699872

    @classmethod
    def rpm_to_rad_per_sec(cls, rpm: float) -> float:
        """Converts RPM (rev/min) to rad/s."""
        return float(rpm) * cls.RPM_TO_RAD_PER_SEC

    @classmethod
    def rad_per_sec_to_rpm(cls, rad_sec: float) -> float:
        """Converts rad/s to RPM (rev/min)."""
        return float(rad_sec) * cls.RAD_PER_SEC_TO_RPM

    @classmethod
    def celsius_to_kelvin(cls, celsius: float) -> float:
        """Converts °C to Kelvin."""
        return float(celsius) + cls.CELSIUS_TO_KELVIN_OFFSET

    @classmethod
    def kelvin_to_celsius(cls, kelvin: float) -> float:
        """Converts Kelvin to °C."""
        return float(kelvin) - cls.CELSIUS_TO_KELVIN_OFFSET

    @classmethod
    def bar_to_pascal(cls, bar: float) -> float:
        """Converts bar to Pascals (Pa)."""
        return float(bar) * cls.BAR_TO_PASCAL

    @classmethod
    def pascal_to_bar(cls, pascal: float) -> float:
        """Converts Pascals (Pa) to bar."""
        return float(pascal) * cls.PASCAL_TO_BAR

    @classmethod
    def kg_per_hour_to_kg_per_sec(cls, kg_h: float) -> float:
        """Converts kg/h to kg/s."""
        return float(kg_h) * cls.KG_PER_HOUR_TO_KG_PER_SEC

    @classmethod
    def kg_per_sec_to_kg_per_hour(cls, kg_s: float) -> float:
        """Converts kg/s to kg/h."""
        return float(kg_s) * cls.KG_PER_SEC_TO_KG_PER_HOUR

    @classmethod
    def hp_to_watts(cls, hp: float) -> float:
        """Converts Horsepower (HP) to Watts (W)."""
        return float(hp) * cls.HP_TO_WATTS

    @classmethod
    def watts_to_hp(cls, watts: float) -> float:
        """Converts Watts (W) to Horsepower (HP)."""
        return float(watts) * cls.WATTS_TO_HP
