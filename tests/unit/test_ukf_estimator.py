import pytest
import numpy as np
from src.digital_twin.estimation.ukf import UnscentedKalmanFilter
from src.digital_twin.estimation.state_estimator import StateEstimator
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.digital_twin.models.operating_context import OperatingContext

def test_ukf_math_sanity():
    # A. UKF math sanity
    # Test sigma weights, Cholesky, and deterministic execution
    ukf = UnscentedKalmanFilter(dim_x=2, dim_z=2, dt=0.1, alpha=1e-3, beta=2.0, kappa=0.0,
                                Q=np.eye(2)*0.1, R=np.eye(2)*0.1, P0=np.eye(2))
    
    # Weights sum to 1 (Wm)
    assert np.isclose(np.sum(ukf.Wm), 1.0)
    
    # Symmetric positive definite P remains valid
    assert np.allclose(ukf.P, ukf.P.T)
    np.linalg.cholesky(ukf.P) # should not raise error

def test_initialization():
    # B. Initialization
    estimator = StateEstimator()
    exp = HealthyExpectedState(rpm=1000.0, map_bar=1.0)
    obs = ObservedState(rpm=1010.0, map_bar=None)
    
    estimator._initialize_filter(exp, obs, 0.1)
    
    # rpm should come from obs (1010), map_bar from exp (1.0)
    assert estimator.ukf.x[0] == 1010.0
    assert estimator.ukf.x[1] == 1.0
    assert estimator.ukf.P.shape == (8, 8)

def test_prediction():
    # C. Prediction
    estimator = StateEstimator()
    exp1 = HealthyExpectedState(rpm=1000.0)
    obs1 = ObservedState(rpm=1000.0)
    
    estimator._initialize_filter(exp1, obs1, 0.1)
    estimator.last_expected_state = np.nan_to_num(estimator._state_to_array(exp1), nan=0.0)
    
    # Process model predicts parallel movement
    exp2 = HealthyExpectedState(rpm=1100.0)
    est2 = estimator.estimate(exp2, ObservedState(), 0.1)
    
    # Expect UKF to track the +100 RPM increase purely from prediction
    assert np.isclose(estimator.ukf.x[0], 1100.0)
    
    # No NaNs
    assert not np.isnan(estimator.ukf.x).any()

def test_measurement_update():
    # D. Measurement update
    estimator = StateEstimator()
    exp = HealthyExpectedState(rpm=1000.0)
    obs = ObservedState(rpm=1000.0)
    
    estimator._initialize_filter(exp, obs, 0.1)
    estimator.last_expected_state = np.nan_to_num(estimator._state_to_array(exp), nan=0.0)
    
    # We observe 1200 RPM while expected says 1000. It should move towards 1200.
    est = estimator.estimate(exp, ObservedState(rpm=1200.0), 0.1)
    
    assert est.rpm > 1000.0
    assert est.rpm <= 1200.0

def test_partial_telemetry():
    # E. Partial telemetry
    estimator = StateEstimator()
    exp = HealthyExpectedState(rpm=1000.0, map_bar=1.0)
    obs = ObservedState(rpm=1000.0, map_bar=1.0)
    estimator._initialize_filter(exp, obs, 0.1)
    estimator.last_expected_state = np.nan_to_num(estimator._state_to_array(exp), nan=0.0)
    
    # Update with map_bar missing
    obs2 = ObservedState(rpm=1100.0, map_bar=None)
    est = estimator.estimate(exp, obs2, 0.1)
    
    # RPM updated
    assert est.rpm > 1000.0
    # Map bar stays where predicted (1.0)
    assert np.isclose(est.map_bar, 1.0)

def test_synchronization_boundary():
    # F. Synchronization boundary
    engine = DigitalTwinEngine()
    ctx = OperatingContext()
    
    # Feed an invalid observed state (wrong sequence)
    obs = ObservedState(sequence_number=999) # Will cause sync to fail
    
    state = engine.process_step(ctx, 0.1, obs)
    
    # Estimator confidence should be 0, no measurement contamination
    assert state.estimated_actual_state.estimation_confidence == 0.0

def test_healthy_baseline():
    # G. Healthy baseline
    estimator = StateEstimator()
    exp = HealthyExpectedState(rpm=2000.0, map_bar=1.0, turbo_rpm=50000.0)
    obs = ObservedState(rpm=2000.0, map_bar=1.0, turbo_rpm=50000.0)
    
    est = estimator.estimate(exp, obs, 0.1)
    assert np.isclose(est.rpm, 2000.0, atol=10.0)

def test_perturbed_telemetry():
    # H. Perturbed telemetry
    estimator = StateEstimator()
    exp = HealthyExpectedState(rpm=2000.0)
    obs = ObservedState(rpm=2000.0)
    estimator._initialize_filter(exp, obs, 0.1)
    estimator.last_expected_state = np.nan_to_num(estimator._state_to_array(exp), nan=0.0)
    
    # Perturb RPM observation
    est = estimator.estimate(exp, ObservedState(rpm=2500.0), 0.1)
    
    assert est.rpm > 2000.0

def test_reset():
    # I. Reset
    estimator = StateEstimator()
    estimator.reset()
    assert estimator.ukf is None
    assert estimator.last_expected_state is None

def test_integration():
    # J. Integration
    engine = DigitalTwinEngine()
    ctx = OperatingContext()
    
    state = engine.process_step(ctx, 0.1) # No telemetry provided initially -> INSUFFICIENT_DATA
    
    obs = ObservedState(
        sequence_number=2,
        timestamp=0.2,
        rpm=1500.0,
        map_bar=1.2,
        data_quality="GOOD"
    )
    
    state2 = engine.process_step(ctx, 0.1, obs, timestamp=0.2, sequence_number=2)
    
    assert state2.estimated_actual_state is not None
    assert state2.estimated_actual_state.covariance is not None
    assert state2.estimated_actual_state.estimation_confidence == 1.0
