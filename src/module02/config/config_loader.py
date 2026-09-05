"""
Module 02 Generic Configuration Loader & Provenance Validator (Phase 1.2 Provenance Gate Pass).
SIH26054 — Module 02 Engine Simulator.
"""

import os
from typing import Any, Dict
import yaml

from src.module02.models.enums import ProvenanceClassification


class ConfigurationError(ValueError):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """Loads and validates Module 02 simulation, engine, aircraft, and propeller YAML configurations."""

    @classmethod
    def get_config_value(cls, config: Dict[str, Any], path: str, default: Any = None) -> Any:
        """
        Retrieves a nested configuration value by dot-separated path (e.g. 'electrical.nominal_bus_voltage_v').
        If the leaf object is a parameter dict containing 'value', extracts the 'value' field.
        """
        if not isinstance(config, dict) or not path:
            return default

        keys = path.split(".")
        curr = config
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return default

        if isinstance(curr, dict) and "value" in curr:
            return curr["value"]

        return curr

    @classmethod
    def load_simulation_config(cls, filepath: str = "configs/module02/simulation_config.yaml") -> Dict[str, Any]:
        """Loads and validates simulation_config.yaml."""
        if not os.path.exists(filepath):
            raise ConfigurationError(f"Simulation configuration file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        cls._validate_simulation_config(cfg)
        return cfg

    @classmethod
    def load_engine_config(cls, filepath: str = "configs/module02/engines/rotax_914.yaml") -> Dict[str, Any]:
        """Loads and validates engine profile YAML configuration with provenance checks."""
        if not os.path.exists(filepath):
            raise ConfigurationError(f"Engine profile file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        cls._validate_engine_config(cfg)
        return cfg

    @classmethod
    def load_aircraft_config(cls, filepath: str = "configs/module02/aircraft/tapas_bh201.yaml") -> Dict[str, Any]:
        """Loads and validates aircraft airframe YAML configuration."""
        if not os.path.exists(filepath):
            raise ConfigurationError(f"Aircraft profile file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        cls._validate_aircraft_config(cfg)
        return cfg

    @classmethod
    def load_propeller_config(cls, filepath: str = "configs/module02/propellers/tapas_bh201_reference_propeller.yaml") -> Dict[str, Any]:
        """Loads and validates propeller and gearbox YAML configuration."""
        if not os.path.exists(filepath):
            raise ConfigurationError(f"Propeller profile file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        cls._validate_propeller_config(cfg)
        return cfg

    @classmethod
    def _validate_simulation_config(cls, cfg: Dict[str, Any]) -> None:
        """Validates simulation configuration boundaries."""
        if not isinstance(cfg, dict):
            raise ConfigurationError("Simulation configuration must be a valid dictionary.")

        time_cfg = cfg.get("time", {})
        dt = time_cfg.get("default_dt_seconds")
        if dt is None or not isinstance(dt, (int, float)) or dt <= 0:
            raise ConfigurationError(f"Invalid physics timestep default_dt_seconds: {dt}. Must be > 0.")

        min_dt = time_cfg.get("min_dt_seconds", 0.0001)
        max_dt = time_cfg.get("max_dt_seconds", 1.0)
        if not (min_dt <= dt <= max_dt):
            raise ConfigurationError(f"Timestep {dt} out of valid bounds [{min_dt}, {max_dt}].")

        randomness_cfg = cfg.get("randomness", {})
        seed = randomness_cfg.get("default_seed")
        if seed is None or not isinstance(seed, int):
            raise ConfigurationError(f"Invalid default_seed: {seed}. Must be an integer.")

    @classmethod
    def _validate_engine_config(cls, cfg: Dict[str, Any]) -> None:
        """Validates engine profile parameters, displacement volume unit, and provenance rules."""
        if not isinstance(cfg, dict):
            raise ConfigurationError("Engine configuration must be a valid dictionary.")

        # Check cylinder count
        cyl_entry = cfg.get("general", {}).get("cylinder_count") or cfg.get("geometry_and_inertia", {}).get("cylinder_count")
        if isinstance(cyl_entry, dict):
            cyl_count = cyl_entry.get("value")
        else:
            cyl_count = cyl_entry

        if cyl_count != 4:
            raise ConfigurationError(f"Invalid cylinder count: {cyl_count}. Module 02 strictly requires 4 cylinders.")

        # Regression Check: Displacement MUST use canonical volume unit (METER3 or M3), NOT mass density (KG_PER_M3)
        disp_entry = cfg.get("geometry_and_inertia", {}).get("displacement_m3")
        if isinstance(disp_entry, dict):
            disp_unit = str(disp_entry.get("unit", "")).upper()
            if disp_unit in ["KG_PER_M3", "KG/M3", "DENSITY"]:
                raise ConfigurationError(
                    f"Dimensional mismatch error: engine displacement unit is set to density '{disp_unit}'. "
                    f"Must be a valid volume unit such as 'METER3' or 'M3'."
                )

        # Validate provenance fields across configuration sections
        cls._recursive_provenance_check(cfg)

    @classmethod
    def _validate_aircraft_config(cls, cfg: Dict[str, Any]) -> None:
        """Validates aircraft airframe parameters and twin-engine rules."""
        if not isinstance(cfg, dict):
            raise ConfigurationError("Aircraft configuration must be a valid dictionary.")

        arch = cfg.get("architecture", {})
        engine_count_entry = arch.get("engine_count")
        if isinstance(engine_count_entry, dict):
            engine_count = engine_count_entry.get("value")
        else:
            engine_count = engine_count_entry

        if engine_count is None or not isinstance(engine_count, int) or engine_count < 1:
            raise ConfigurationError(f"Invalid engine_count: {engine_count}. Must be >= 1.")

        # Validate separate target vs demonstrated metrics
        reqs = cfg.get("performance_requirements", {})
        if "target_operating_altitude_m" not in reqs or "demonstrated_altitude_m" not in reqs:
            raise ConfigurationError("Aircraft config must explicitly separate target vs demonstrated altitude.")

        if "target_endurance_hours" not in reqs or "demonstrated_endurance_hours" not in reqs:
            raise ConfigurationError("Aircraft config must explicitly separate target vs demonstrated endurance.")

        cls._recursive_provenance_check(cfg)

    @classmethod
    def _validate_propeller_config(cls, cfg: Dict[str, Any]) -> None:
        """Validates propeller and gearbox speed ratio configuration."""
        if not isinstance(cfg, dict):
            raise ConfigurationError("Propeller configuration must be a valid dictionary.")

        gb = cfg.get("gearbox", {})
        speed_ratio_entry = gb.get("engine_to_propeller_speed_ratio") or gb.get("gear_ratio")
        if isinstance(speed_ratio_entry, dict):
            speed_ratio = speed_ratio_entry.get("value")
        else:
            speed_ratio = speed_ratio_entry

        if speed_ratio is None or speed_ratio <= 0:
            raise ConfigurationError(f"Invalid engine_to_propeller_speed_ratio: {speed_ratio}. Must be > 0.")

        cls._recursive_provenance_check(cfg)

    @classmethod
    def _recursive_provenance_check(cls, data: Any, current_path: str = "") -> None:
        """Recursively checks that parameter dictionary entries contain valid provenance metadata."""
        if isinstance(data, dict):
            if "value" in data and "classification" in data:
                classification = data.get("classification")
                source = data.get("source")

                if classification not in ProvenanceClassification.__members__:
                    raise ConfigurationError(
                        f"Invalid classification '{classification}' at '{current_path}'. "
                        f"Must be one of {list(ProvenanceClassification.__members__.keys())}."
                    )

                # Strict Rule: Cannot mark OFFICIAL without a explicit non-empty source
                if classification == ProvenanceClassification.OFFICIAL.value:
                    if not source or source in ["GENERIC_DEFAULT", "ASSUMPTION", "ENGINEERING_ESTIMATE"]:
                        raise ConfigurationError(
                            f"Parameter at '{current_path}' marked OFFICIAL but lacks authoritative public source (got '{source}')."
                        )

            for key, val in data.items():
                new_path = f"{current_path}.{key}" if current_path else key
                cls._recursive_provenance_check(val, new_path)
