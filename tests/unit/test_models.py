"""
Unit Tests for Data Models & Enums.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import pytest
from src.module01.models.enums import PhysicalOrigin, StateCategory, ValidityStatus
from src.module01.models.metadata import UnitMetadata
from src.module01.models.cylinder_data import CylinderBank, CylinderMeasurement


def test_unit_metadata_creation():
    meta = UnitMetadata(
        raw_unit="RPM",
        engineering_unit="RPM",
        canonical_si_unit="RAD_PER_SEC",
        scale_factor=0.104719755,
        offset=0.0,
    )
    assert meta.raw_unit == "RPM"
    assert meta.canonical_si_unit == "RAD_PER_SEC"


def test_cylinder_bank_dynamic_count():
    cyl1 = CylinderMeasurement(cylinder_id=1)
    cyl2 = CylinderMeasurement(cylinder_id=2)
    bank = CylinderBank.create(cylinder_count=2, cylinders_dict={1: cyl1, 2: cyl2})
    assert bank.cylinder_count == 2
    assert bank.cylinders[1].cylinder_id == 1
