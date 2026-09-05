"""
Module 02 Model & Configuration Versioning (Phase 1 Foundation).
SIH26054 — Module 02 Engine Simulator.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VersionInfo:
    """Model & Configuration Versioning Container."""
    simulation_model_version: str = "1.3.0"
    configuration_schema_version: str = "1.0.0"
    physics_specification: str = "SIH26054_MODULE02_V1.3_HARDENED"
    provenance_tag: str = "SIMULATOR"

    def get_version_summary(self) -> str:
        return f"Module02 v{self.simulation_model_version} (Config v{self.configuration_schema_version}, Spec: {self.physics_specification})"
