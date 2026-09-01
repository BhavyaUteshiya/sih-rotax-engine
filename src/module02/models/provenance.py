"""
Module 02 Parameter Provenance Container (Phase 1 Correction).
SIH26054 — Module 02 Engine Simulator.
"""

from dataclasses import dataclass
from typing import Any
from src.module02.models.enums import ProvenanceClassification


@dataclass(frozen=True)
class ProvenanceMetadata:
    """Explicit Provenance Container for physical parameters."""
    value: Any
    unit: str
    classification: ProvenanceClassification
    source: str
    confidence: str                       # HIGH, MEDIUM, LOW
    calibration_required: bool

    def is_official(self) -> bool:
        return self.classification == ProvenanceClassification.OFFICIAL
