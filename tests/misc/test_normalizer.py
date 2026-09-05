"""
Unit Tests for SI Unit Normalizer.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import math
import pytest
from src.module01.normalization.unit_normalizer import UnitConversionError, UnitNormalizer


def test_rpm_to_rad_per_sec():
    canonical, engineering, meta = UnitNormalizer.convert_to_si(5200.0, "RPM")
    assert engineering == 5200.0
    assert meta.canonical_si_unit == "RAD_PER_SEC"
    expected_si = 5200.0 * (math.pi / 30.0)
    assert abs(canonical - expected_si) < 1e-6


def test_celsius_to_kelvin():
    canonical, engineering, meta = UnitNormalizer.convert_to_si(145.0, "DEGC")
    assert engineering == 145.0
    assert meta.canonical_si_unit == "KELVIN"
    assert abs(canonical - 418.15) < 1e-6


def test_bar_to_pascal():
    canonical, engineering, meta = UnitNormalizer.convert_to_si(4.2, "BAR")
    assert engineering == 4.2
    assert meta.canonical_si_unit == "PASCAL"
    assert abs(canonical - 420000.0) < 1e-6


def test_roundtrip_conversion_fidelity():
    raw_in = 5200.0
    canonical, eng, meta = UnitNormalizer.convert_to_si(raw_in, "RPM")
    raw_out = UnitNormalizer.convert_si_to_raw(canonical, "RPM")
    assert abs(raw_in - raw_out) < 1e-6
