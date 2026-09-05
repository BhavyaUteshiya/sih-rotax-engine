"""
Configuration Loader Module.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigError(Exception):
    """Configuration loading or validation exception."""
    pass


class ConfigLoader:
    """
    Strongly-typed, safe configuration loader for Module 01 YAML files.
    Enforces safe_load and path validation.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).resolve().parent.parent.parent.parent / "configs"
        self.config_dir = Path(config_dir).resolve()

    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        resolved = Path(file_path).resolve()
        if not resolved.exists():
            raise ConfigError(f"Configuration file not found: {file_path}")
        
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    raise ConfigError(f"YAML content in {file_path} must be a dictionary")
                return data
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML parsing error in {file_path}: {e}")
        except Exception as e:
            raise ConfigError(f"Error reading configuration file {file_path}: {e}")

    def load_acquisition_config(self) -> Dict[str, Any]:
        return self._load_yaml(self.config_dir / "acquisition_config.yaml")

    def load_engine_profile(self) -> Dict[str, Any]:
        return self._load_yaml(self.config_dir / "engine_profiles" / "representative_4stroke_piston.yaml")

    def load_sensor_definitions(self) -> Dict[str, Any]:
        return self._load_yaml(self.config_dir / "sensors" / "sensor_definitions.yaml")

    def load_validity_limits(self) -> Dict[str, Any]:
        return self._load_yaml(self.config_dir / "limits" / "sensor_validity_limits.yaml")

    def load_operational_metadata(self) -> Dict[str, Any]:
        return self._load_yaml(self.config_dir / "limits" / "operational_metadata.yaml")

    def load_can_mappings(self) -> Dict[str, Any]:
        return self._load_yaml(self.config_dir / "demonstration_can_mappings.yaml")
