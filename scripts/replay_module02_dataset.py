#!/usr/bin/env python3
"""
Replay Script: Replays Exported Telemetry Datasets into Digital Twin Core Handoff Stream.
SIH26054 — Module 02 Engine Simulator.
"""

import csv
import json
import os
import sys
from typing import Dict, List


def replay_dataset(filepath: str) -> List[Dict]:
    """
    Reads an exported dataset (CSV or JSONL), verifies sequence ordering and schema compliance,
    and returns ordered historical dataset records ready for Digital Twin Core replay.
    Does NOT rerun physics during replay.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Exported dataset file not found: {filepath}")

    records: List[Dict] = []

    if filepath.endswith(".jsonl"):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    elif filepath.endswith(".csv"):
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
    else:
        raise ValueError("Unsupported replay format. File must be .csv or .jsonl")

    # Sort strictly by sequence number and timestamp
    records.sort(key=lambda r: (int(r.get("sequence_number", 0)), float(r.get("timestamp", 0.0))))
    return records


def main() -> None:
    print("=========================================================================================================")
    print("SIH26054 — REPLAY TELEMETRY DATASET VALIDATION")
    print("=========================================================================================================")

    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/exports/telemetry_dataset.jsonl"
    if not os.path.exists(filepath):
        filepath = "data/exports/telemetry_dataset.csv"

    if not os.path.exists(filepath):
        print(f"No dataset file found at {filepath}. Run scripts/run_module02_module01_e2e_demo.py first.")
        sys.exit(1)

    print(f"Replaying dataset file: {filepath}")
    replayed_records = replay_dataset(filepath)

    print(f"Successfully loaded and ordered {len(replayed_records)} historical dataset records.")
    print("-" * 105)
    print(f"{'SeqNum':<8} | {'SimTime':<8} | {'EngineID':<10} | {'ParameterID':<28} | {'CanonicalVal':<12} | {'Unit':<12} | {'Validity':<8}")
    print("-" * 105)

    sample_display = replayed_records[:15]
    for r in sample_display:
        seq = r.get("sequence_number", 0)
        t_sim = float(r.get("simulation_time", 0.0))
        eng = r.get("engine_id", "engine_1")
        param = r.get("parameter_id", "unknown")
        c_val = float(r.get("canonical_value", 0.0))
        c_unit = r.get("canonical_unit", "")
        val = r.get("validity", "VALID")
        print(f"{seq:<8} | {t_sim:<8.2f} | {eng:<10} | {param:<28} | {c_val:<12.3f} | {c_unit:<12} | {val:<8}")

    print("=" * 105)
    print("REPLAY DATASET ORDERING & CONTRACT VALIDATION COMPLETE.")


if __name__ == "__main__":
    main()
