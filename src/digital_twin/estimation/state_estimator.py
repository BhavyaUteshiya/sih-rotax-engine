import os
import yaml
import numpy as np
from typing import Optional, List, Dict, Any, Tuple

from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.estimated_actual_state import EstimatedActualState
from src.digital_twin.estimation.ukf import UnscentedKalmanFilter

class StateEstimator:
    """
    Phase 2D State Estimator.
    Maps between the 19-parameter Digital Twin contracts and the 8-parameter UKF representation.
    """
    
    # State Vector Mapping
    # [0] rpm
    # [1] map_bar
    # [2] turbo_rpm
    # [3] airflow_kg_h
    # [4] fuel_flow_kg_h
    # [5] afr
    # [6] cht_c
    # [7] oil_temp_c
    
    STATE_KEYS = [
        "rpm", 
        "map_bar", 
        "turbo_rpm", 
        "airflow_kg_h", 
        "fuel_flow_kg_h", 
        "afr", 
        "cht_c", 
        "oil_temp_c"
    ]

    def __init__(self, config_path: str = "configs/ukf_config.yaml"):
        self._load_config(config_path)
        self.ukf: Optional[UnscentedKalmanFilter] = None
        self.last_expected_state: Optional[np.ndarray] = None
        
    def _load_config(self, config_path: str):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"UKF config not found: {config_path}")
            
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            
        self.alpha = float(cfg.get("alpha", 1e-3))
        self.beta = float(cfg.get("beta", 2.0))
        self.kappa = float(cfg.get("kappa", 0.0))
        self.num_tol = float(cfg.get("numerical_tolerance", 1e-6))
        
        self.Q = np.diag(cfg.get("Q", [1.0] * 8))
        self.R = np.diag(cfg.get("R", [1.0] * 8))
        self.P0 = np.diag(cfg.get("P0", [1.0] * 8))

    def _state_to_array(self, expected: HealthyExpectedState, observed: ObservedState) -> np.ndarray:
        """Extracts the 8-dim state vector from a state object, throwing error if data is missing."""
        arr = np.zeros(8)
        for i, key in enumerate(self.STATE_KEYS):
            val = getattr(observed, key, None)
            if val is None or np.isnan(val) or np.isinf(val):
                val = getattr(expected, key, None)
            
            if val is None or np.isnan(val) or np.isinf(val):
                arr[i] = np.nan
            else:
                arr[i] = val
        return arr

    def _initialize_filter(self, expected: HealthyExpectedState, observed: ObservedState, dt: float) -> bool:
        """
        Initializes the UKF using the best available combination of expected and observed data.
        Returns True if successful, False if insufficient data.
        """
        exp_arr = self._state_to_array(expected, expected) # Safe extraction
        # For observed, we use expected as fallback for validation
        obs_arr = self._state_to_array(expected, observed)
        
        # Initialize with observed if valid, otherwise expected
        x0 = np.where(np.isnan(obs_arr), exp_arr, obs_arr)
        
        # Check if any required state is NaN
        if np.isnan(x0).any():
            return False

        
        self.ukf = UnscentedKalmanFilter(
            dim_x=8,
            dim_z=8,
            dt=dt,
            alpha=self.alpha,
            beta=self.beta,
            kappa=self.kappa,
            Q=self.Q,
            R=self.R,
            P0=self.P0,
            numerical_tolerance=self.num_tol
        )
        self.ukf.x = x0
        self.last_expected_state = np.nan_to_num(exp_arr, nan=0.0)
        return True

    def reset(self):
        """Forces a deterministic reset of the estimator."""
        self.ukf = None
        self.last_expected_state = None

    def estimate(self, expected: HealthyExpectedState, observed: ObservedState, dt: float, predict_only: bool = False) -> EstimatedActualState:
        """
        Runs the prediction and measurement update for one timestep.
        Must only be called if synchronization succeeded, unless predict_only=True.
        """
        if dt <= 0.0:
            dt = 0.1 # Minimum safe dt
            
        if self.ukf is None:
            success = self._initialize_filter(expected, observed, dt)
            if not success:
                # Cannot initialize, return pass-through with 0 confidence
                return self._build_uninitialized_state(expected)
        
        self.ukf.dt = dt
        
        # 1. Prediction (Process Model)
        # Explicit classification: healthy-reference-driven reduced-order process model
        # It propagates deviation around the healthy reference trajectory.
        # It does not reproduce the full nonlinear simulator inside UKF sigma points,
        # which is intentional to avoid duplicating Phase 1 physics.
        # x_k|k-1 = x_k-1|k-1 + (exp_k - exp_k-1)
        # For prediction, we just extract the expected state values (so we pass expected as both to avoid throwing on observed)
        curr_exp_arr = np.nan_to_num(self._state_to_array(expected, expected), nan=0.0)
        delta_exp = curr_exp_arr - self.last_expected_state
        
        def process_model(x: np.ndarray, dt_step: float) -> np.ndarray:
            return x + delta_exp
            
        self.ukf.predict(process_model)
        self.last_expected_state = curr_exp_arr
        
        # 2. Measurement Update (Measurement Model)
        obs_arr = self._state_to_array(expected, observed)
        
        valid_indices = []
        valid_measurements = []
        
        if not predict_only:
            # Filter available channels
            for i in range(8):
                if not np.isnan(obs_arr[i]):
                    valid_indices.append(i)
                    valid_measurements.append(obs_arr[i])
                    
        if valid_measurements:
            z = np.array(valid_measurements)
            mapping = np.array(valid_indices)
            
            # Select sub-matrix of R for active measurements
            R_active = self.R[np.ix_(mapping, mapping)]
            
            self.ukf.update(z, measurement_mapping=mapping, R_active=R_active)
            
        # 3. Populate EstimatedActualState
        est = self._build_estimated_state(expected, self.ukf.x, self.ukf.P)
        if predict_only:
            est.is_prediction_only = True
            est.estimation_confidence = 0.0
        return est

    def _build_uninitialized_state(self, expected: HealthyExpectedState) -> EstimatedActualState:
        """Builds a pass-through state when UKF cannot be initialized."""
        est = EstimatedActualState(
            timestamp=expected.timestamp,
            sequence_number=expected.sequence_number,
            engine_id=expected.engine_id,
            aircraft_id=expected.aircraft_id,
            estimation_confidence=0.0,
            is_prediction_only=True
        )
        # All available fields from expected are passed through
        for key in self.STATE_KEYS:
            val = getattr(expected, key, None)
            if val is not None:
                setattr(est, key, val)
                
        # Pass remaining 11 fields
        self._populate_passthrough_fields(expected, est)
        return est

    def _populate_passthrough_fields(self, expected: HealthyExpectedState, est: EstimatedActualState):
        if expected.combustion_energy is not None: est.combustion_energy = expected.combustion_energy
        if expected.combustion_efficiency is not None: est.combustion_efficiency = expected.combustion_efficiency
        if expected.indicated_power_kw is not None: est.indicated_power_kw = expected.indicated_power_kw
        if expected.torque_n_m is not None: est.torque_n_m = expected.torque_n_m
        if expected.coolant_temp_c is not None: est.coolant_temp_c = expected.coolant_temp_c
        if expected.oil_pressure_bar is not None: est.oil_pressure_bar = expected.oil_pressure_bar
        if expected.turbo_boost_bar is not None: est.turbo_boost_bar = expected.turbo_boost_bar
        if expected.gearbox_rpm is not None: est.gearbox_rpm = expected.gearbox_rpm
        if expected.propeller_load_nm is not None: est.propeller_load_nm = expected.propeller_load_nm
        if expected.thrust_n is not None: est.thrust_n = expected.thrust_n

    def _build_estimated_state(self, expected: HealthyExpectedState, x: np.ndarray, P: np.ndarray) -> EstimatedActualState:
        """
        Reconstructs the 19-parameter state using 8 estimated values and
        falling back to ExpectedState for unestimated fields.
        """
        est = EstimatedActualState(
            timestamp=expected.timestamp,
            sequence_number=expected.sequence_number,
            engine_id=expected.engine_id,
            aircraft_id=expected.aircraft_id,
            estimation_confidence=1.0,
        )
        
        # Map back the 8 estimated states
        for i, key in enumerate(self.STATE_KEYS):
            setattr(est, key, float(x[i]))
            
        # Extract diagonal elements as variance for uncertainty representation
        est.covariance = P.tolist()
        
        self._populate_passthrough_fields(expected, est)
        
        return est
