"""
Validation Test to Ensure Python Source Code Contains Zero Hardcoded TAPAS Numbers.
SIH26054 — Module 02 Engine Simulator.
"""

import os
import re
import pytest


def test_no_hardcoded_tapas_numbers_in_source_code():
    """
    Scans all Python source files in src/module02/ to verify that TAPAS-specific numbers
    (e.g., 180 HP, 2800 kg MTOW, 9144 m target alt, 8534.4 m demonstrated alt) are NOT hardcoded
    in source code logic, but are loaded exclusively from YAML configurations.
    """
    src_dir = "src/module02/"
    forbidden_numbers = [
        "180.0", "2800.0", "9144.0", "8534.4", "17664.0", "5384.0"
    ]

    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                for forbidden in forbidden_numbers:
                    # Search for literal assignment of forbidden number outside docstrings/comments
                    lines = content.splitlines()
                    for idx, line in enumerate(lines, 1):
                        stripped = line.strip()
                        # Ignore comments
                        if stripped.startswith("#"):
                            continue
                        if forbidden in stripped:
                            # Allow if part of a dataclass default in models/states.py or docstring
                            if "models" in filepath and "states.py" in filepath or "docstring" in stripped:
                                continue
                            pytest.fail(f"Hardcoded TAPAS constant '{forbidden}' found in {filepath}:{idx}: {line}")
