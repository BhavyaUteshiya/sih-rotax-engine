"""
SI Unit Normalizer Module (Phase 7).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import math
from typing import Any, Dict, Optional, Tuple

from src.module01.models.metadata import UnitMetadata


class UnitConversionError(Exception):
    """Exception raised when unit conversion fails due to unknown or incompatible units."""
    pass


class UnitNormalizer:
    """
    Normalizes raw sensor units into canonical SI units and human-facing engineering display units.
    Operates strictly on explicit unit metadata and conversion formulas.
    """

    # Dictionary mapping raw unit strings to (engineering_unit, canonical_si_unit, scale_factor, offset)
    # Canonical SI units: K (Kelvin), Pa (Pascal), rad/s (RAD_PER_SEC), kg/s (KG_PER_SEC), m/s² (M_PER_SEC2), V, A, deg, N, N·m
    UNIT_TABLE: Dict[str, Tuple[str, str, float, float]] = {
        "RPM": ("RPM", "RAD_PER_SEC", math.pi / 30.0, 0.0),
        "DEGC": ("°C", "KELVIN", 1.0, 273.15),
        "CELSIUS": ("°C", "KELVIN", 1.0, 273.15),
        "BAR": ("bar", "PASCAL", 100000.0, 0.0),
        "PSI": ("psi", "PASCAL", 6894.75729, 0.0),
        "KG_PER_HOUR": ("kg/h", "KG_PER_SEC", 1.0 / 3600.0, 0.0),
        "KG_PER_SEC": ("kg/s", "KG_PER_SEC", 1.0, 0.0),
        "M_PER_SEC2": ("m/s²", "M_PER_SEC2", 1.0, 0.0),
        "MPS2": ("m/s²", "M_PER_SEC2", 1.0, 0.0),
        "VOLT": ("V", "VOLT", 1.0, 0.0),
        "AMPERE": ("A", "AMPERE", 1.0, 0.0),
        "DEG_BTDC": ("°BTDC", "DEGREE", 1.0, 0.0),
        "DEGREE": ("deg", "DEGREE", 1.0, 0.0),
        "KG_PER_M3": ("kg/m³", "KG_PER_M3", 1.0, 0.0),
        "NM": ("N·m", "NEWTON_METER", 1.0, 0.0),
        "NEWTON": ("N", "NEWTON", 1.0, 0.0),
        "RATIO": ("ratio", "RATIO", 1.0, 0.0),
        "METER": ("m", "METER", 1.0, 0.0),
        "MPS": ("m/s", "MPS", 1.0, 0.0),
        "KG": ("kg", "KG", 1.0, 0.0),
    }

    @classmethod
    def get_unit_metadata(cls, raw_unit: str) -> UnitMetadata:
        """
        Retrieves UnitMetadata for a given raw unit string.
        Raises UnitConversionError if raw_unit is unknown.
        """
        key = raw_unit.upper().strip()
        if key not in cls.UNIT_TABLE:
            raise UnitConversionError(f"Unknown or unsupported raw unit: '{raw_unit}'")

        eng_unit, si_unit, scale, offset = cls.UNIT_TABLE[key]
        return UnitMetadata(
            raw_unit=raw_unit,
            engineering_unit=eng_unit,
            canonical_si_unit=si_unit,
            scale_factor=scale,
            offset=offset,
        )

    @classmethod
    def convert_to_si(cls, raw_value: float, raw_unit: str) -> Tuple[float, float, UnitMetadata]:
        """
        Converts a raw value to (canonical_si_value, engineering_display_value, unit_metadata).
        """
        unit_meta = cls.get_unit_metadata(raw_unit)
        key = raw_unit.upper().strip()

        if key in ("DEGC", "CELSIUS"):
            engineering_val = float(raw_value)
            canonical_si_val = float(raw_value) + 273.15
        else:
            engineering_val = float(raw_value)
            canonical_si_val = (float(raw_value) * unit_meta.scale_factor) + unit_meta.offset

        return canonical_si_val, engineering_val, unit_meta

    @classmethod
    def convert_si_to_raw(cls, si_value: float, raw_unit: str) -> float:
        """
        Reverses canonical SI value back to raw unit value for round-trip testing.
        """
        unit_meta = cls.get_unit_metadata(raw_unit)
        key = raw_unit.upper().strip()

        if key in ("DEGC", "CELSIUS"):
            return si_value - 273.15
        else:
            return (si_value - unit_meta.offset) / unit_meta.scale_factor
