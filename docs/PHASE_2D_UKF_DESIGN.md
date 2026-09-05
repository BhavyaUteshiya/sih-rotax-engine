# Phase 2D: State Estimation (UKF) Design

## 1. Overview
The Phase 2D Unscented Kalman Filter (UKF) introduces deterministic state estimation to the Digital Twin. Rather than blindly copying noisy telemetry, the UKF estimates the true internal state of the engine by balancing physics predictions (from Phase 1) with synchronized telemetry (from Phase 2A/C).

## 2. Core Principles
- **No Physics Modification:** The UKF runs purely as an observer and never alters the Phase 1 Engine Dynamics or Thermal state directly.
- **Strict Synchronization:** Estimation only occurs if the input telemetry clears the Phase 2C `StateSynchronizer` gate. Invalid telemetry halts measurement updates.
- **Explicit 8-Parameter State Vector:** We define a focused 8-parameter subset to track the fundamental engine operating envelope. The rest of the 19 contract parameters are either algebraically constrained (like AFR) or treated as downstream derivations in Phase 2D.

## 3. The State Vector (8 Degrees of Freedom)
The filter tracks the following essential state variables (`dim_x = 8`):
1. `rpm`: Engine speed.
2. `map_bar`: Manifold absolute pressure.
3. `turbo_rpm`: Turbine rotational speed.
4. `airflow_kg_h`: Mass airflow rate.
5. `fuel_flow_kg_h`: Fuel flow rate.
6. `afr`: Air-Fuel Ratio.
7. `cht_c`: Cylinder head temperature.
8. `oil_temp_c`: Engine oil temperature.

## 4. Mathematical Implementation
- **Sigma Points:** We utilize Merwe Scaled Sigma Points (`alpha=1e-3`, `beta=2.0`, `kappa=0.0`) to handle moderate nonlinearities safely without requiring a Jacobian.
- **Process Model (Prediction):** We rely on the Phase 1 `HealthyExpectedState`. The UKF calculates the expected delta (`delta_x = expected_now - expected_previous`) and applies this offset to the current UKF state. This perfectly links the numerical UKF prediction to our verified analytical physics model.
- **Measurement Model (Update):** We utilize an identity mapping since sensors observe the state variables directly, but we support missing sensor channels (partial telemetry) by dynamically sizing the measurement matrix ($H$) based on `valid_sensors`.
- **Stabilization:** Cholesky decomposition is the default for sigma-point generation, falling back to a robust Eigenvalue decomposition (`np.linalg.eigh`) if numerical drift causes the covariance matrix $P$ to lose positive-semidefiniteness.

## 5. Lifecycle and Reset Policy
- **Healthy Operation:** Filter continuously predicts and updates based on `dt`.
- **Synchronization Failure:** If sequence numbers mismatch, timestamps exceed tolerance, or telemetry is marked `INVALID`/`INSUFFICIENT_DATA`:
  - The measurement update step is skipped completely.
  - The estimator runs purely in *Prediction-only* mode.
  - `estimation_confidence` is explicitly set to `0.0`.
- **Reset:** If an unrecoverable discontinuity is observed (e.g. engine restart), `StateEstimator.reset()` safely clears the filter to re-initialize on the next valid frame.
