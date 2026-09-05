"""
Extensible Cylinder Data Structures.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, Optional

from src.module01.models.sensor_sample import SensorMeasurement


@dataclass(frozen=True)
class CylinderMeasurement:
    """Per-cylinder telemetry measurements."""
    cylinder_id: int                            # 1, 2, 3, ... N
    cht: Optional[SensorMeasurement] = None     # Cylinder Head Temperature
    egt: Optional[SensorMeasurement] = None     # Exhaust Gas Temperature
    knock: Optional[SensorMeasurement] = None   # Knock sensor (future extensible)
    cylinder_pressure: Optional[SensorMeasurement] = None # Cylinder pressure (future extensible)


@dataclass(frozen=True)
class CylinderBank:
    """Dynamic CylinderBank container supporting arbitrary cylinder count (e.g. 2, 4, 6, 8)."""
    cylinder_count: int                         # Set via configuration (e.g. 4 for representative engine)
    cylinders: MappingProxyType                 # Map: cylinder_id (int) -> CylinderMeasurement

    @classmethod
    def create(cls, cylinder_count: int, cylinders_dict: Dict[int, CylinderMeasurement]) -> "CylinderBank":
        return cls(
            cylinder_count=cylinder_count,
            cylinders=MappingProxyType(dict(cylinders_dict)),
        )
