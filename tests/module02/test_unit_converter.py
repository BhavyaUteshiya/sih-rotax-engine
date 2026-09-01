"""
Phase 1 Unit Converter Validation Tests.
SIH26054 — Module 02 Engine Simulator.
"""

import math
import pytest
from src.module02.utils.unit_converter import UnitConverter


def test_rpm_to_rad_per_sec_conversion():
    """Verify RPM <-> rad/s conversions."""
    # 0 RPM = 0 rad/s
    assert UnitConverter.rpm_to_rad_per_sec(0.0) == pytest.approx(0.0)

    # 3000 RPM = 100 * pi rad/s = 314.159265 rad/s
    assert UnitConverter.rpm_to_rad_per_sec(3000.0) == pytest.approx(314.1592653589793)

    # 5800 RPM (Rated speed) = 607.37457 rad/s
    assert UnitConverter.rpm_to_rad_per_sec(5800.0) == pytest.approx(607.374579, rel=1e-5)

    # Roundtrip conversion
    assert UnitConverter.rad_per_sec_to_rpm(UnitConverter.rpm_to_rad_per_sec(5200.0)) == pytest.approx(5200.0)


def test_temperature_celsius_to_kelvin_conversion():
    """Verify °C <-> K conversions."""
    # 0 °C = 273.15 K
    assert UnitConverter.celsius_to_kelvin(0.0) == pytest.approx(273.15)

    # 15 °C (ISA Standard Sea Level) = 288.15 K
    assert UnitConverter.celsius_to_kelvin(15.0) == pytest.approx(288.15)

    # 145 °C (Normal CHT) = 418.15 K
    assert UnitConverter.celsius_to_kelvin(145.0) == pytest.approx(418.15)

    # Roundtrip conversion
    assert UnitConverter.kelvin_to_celsius(UnitConverter.celsius_to_kelvin(95.0)) == pytest.approx(95.0)


def test_pressure_bar_to_pascal_conversion():
    """Verify bar <-> Pa conversions."""
    # 0 bar = 0 Pa
    assert UnitConverter.bar_to_pascal(0.0) == pytest.approx(0.0)

    # 1.01325 bar = 101325 Pa (Standard Atmosphere)
    assert UnitConverter.bar_to_pascal(1.01325) == pytest.approx(101325.0)

    # 4.2 bar (Oil pressure) = 420000 Pa
    assert UnitConverter.bar_to_pascal(4.2) == pytest.approx(420000.0)

    # Roundtrip conversion
    assert UnitConverter.pascal_to_bar(UnitConverter.bar_to_pascal(3.5)) == pytest.approx(3.5)


def test_fuel_flow_kg_h_to_kg_s_conversion():
    """Verify kg/h <-> kg/s conversions."""
    # 0 kg/h = 0 kg/s
    assert UnitConverter.kg_per_hour_to_kg_per_sec(0.0) == pytest.approx(0.0)

    # 36.0 kg/h = 0.01 kg/s
    assert UnitConverter.kg_per_hour_to_kg_per_sec(36.0) == pytest.approx(0.01)

    # Roundtrip conversion
    assert UnitConverter.kg_per_sec_to_kg_per_hour(UnitConverter.kg_per_hour_to_kg_per_sec(25.5)) == pytest.approx(25.5)


def test_horsepower_to_watts_conversion():
    """Verify HP <-> Watts conversions."""
    # 115 HP (Rated Engine Power) = 85755.485 W
    assert UnitConverter.hp_to_watts(115.0) == pytest.approx(85755.485, rel=1e-4)

    # Roundtrip conversion
    assert UnitConverter.watts_to_hp(UnitConverter.hp_to_watts(100.0)) == pytest.approx(100.0)
