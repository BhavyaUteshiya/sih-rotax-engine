# Phase 2F: Health State Design

## Overview
Phase 2F implements the Health State assessment engine for the Digital Twin. The core responsibility of this module is to transform parameterized residual deviations into actionable system-level health classifications (HEALTHY, WARNING, CRITICAL, UNKNOWN) based on deterministic logical policies.

## 1. Authoritative Physical Parameters
The health assessment is driven exclusively by the 19 authoritative physical parameters calculated during the Residual Analysis phase:
- rpm, map_bar, turbo_rpm, airflow_kg_h, fuel_flow_kg_h, afr
- combustion_energy, combustion_efficiency, indicated_power_kw, torque_n_m
- egt_c, cht_c, coolant_temp_c, oil_temp_c, oil_pressure_bar
- turbo_boost_bar, gearbox_rpm, propeller_load_nm, thrust_n

Any parameter missing from this list is considered unmodeled and **must not** influence the final health classification or trigger fallback states.

## 2. Sufficient-Evidence Policy & UNKNOWN Semantics
The `UNKNOWN` health state is reserved strictly for situations where the Digital Twin lacks the sufficient evidence required to make a safe assessment.

### Policy Rules
1. **Valid Evidence Count**: We compute the number of authoritative parameters that have valid residuals (neither `MISSING` nor `INVALID_NAN`/`INVALID_INF`).
2. **Sufficient Evidence**: As long as `valid_evidence_count > 0`, the engine has sufficient evidence to attempt a classification.
3. **UNKNOWN Trigger**: The `UNKNOWN` state is ONLY triggered when `valid_evidence_count == 0`. 
4. **Resilience to Missing Data**: The engine will not drop to `UNKNOWN` simply because a subset of sensors failed or are missing. If even one authoritative parameter has valid data, the engine will synthesize a `WARNING` or `CRITICAL` state if applicable, or default to `HEALTHY`.

## 3. Classification Precedence
Health levels are evaluated with strict precedence:
1. **UNKNOWN**: Triggered if `valid_evidence_count == 0` or if the underlying data synchronization explicitly failed with `INSUFFICIENT_DATA`.
2. **CRITICAL**: Triggered if any valid residual exceeds its configured `critical_threshold`. Overrides all lower states.
3. **WARNING**: Triggered if any valid residual exceeds its configured `warning_threshold` (and no critical deviations exist).
4. **HEALTHY**: The default baseline if sufficient evidence exists and no thresholds are breached.

## 4. Confidence and Degraded Rules
While the health classification is resilient to partial data loss, the **confidence** of the assessment gracefully degrades.
- `missing_count`: The number of missing authoritative parameters.
- `invalid_count`: The number of mathematically invalid authoritative parameters (`inf`, `nan`).
- A high `missing_count` will lower the overall `model_confidence` output of the digital twin, signaling to operators that while the engine is currently assessed as `HEALTHY`, the assessment is based on a degraded evidence pool.

## 5. Separation of Concerns
The Health State assessment is strictly read-only relative to the Causal Analyzer. 
- It aggregates residual flags.
- It determines the worst-case severity.
- It identifies the dominant parameter (the one with the highest relative error).
It does **not** perform root-cause attribution, isolate faults, or overwrite causal markers (Phase 2G+ scope).
