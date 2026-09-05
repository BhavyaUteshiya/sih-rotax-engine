import pytest
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.services.state_synchronizer import StateSynchronizer
from src.digital_twin.models.synchronization_result import SynchronizationStatus

def test_exact_timestamp_alignment():
    synchronizer = StateSynchronizer()
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed = ObservedState(timestamp=10.0, sequence_number=10, engine_id="engine_1", data_quality="GOOD")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, observed, context, 9)
    assert result.is_synchronized
    assert result.status == SynchronizationStatus.SYNC_SUCCESS

def test_acceptable_timestamp_difference():
    synchronizer = StateSynchronizer(timestamp_tolerance_s=0.1)
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed = ObservedState(timestamp=10.05, sequence_number=10, engine_id="engine_1", data_quality="GOOD")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, observed, context, 9)
    assert result.is_synchronized
    assert result.status == SynchronizationStatus.SYNC_SUCCESS

def test_stale_observation():
    synchronizer = StateSynchronizer(timestamp_tolerance_s=0.1)
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed = ObservedState(timestamp=9.8, sequence_number=10, engine_id="engine_1", data_quality="GOOD")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, observed, context, 9)
    assert not result.is_synchronized
    assert result.status == SynchronizationStatus.STALE_OBSERVATION

def test_out_of_order_observation():
    synchronizer = StateSynchronizer()
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed = ObservedState(timestamp=10.0, sequence_number=8, engine_id="engine_1", data_quality="GOOD")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, observed, context, last_sequence_number=9)
    assert not result.is_synchronized
    assert result.status == SynchronizationStatus.OUT_OF_ORDER

def test_missing_observation():
    synchronizer = StateSynchronizer()
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, None, context, 9)
    assert not result.is_synchronized
    assert result.status == SynchronizationStatus.MISSING_OBSERVATION

def test_engine_identity_mismatch():
    synchronizer = StateSynchronizer()
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed = ObservedState(timestamp=10.0, sequence_number=10, engine_id="engine_2", data_quality="GOOD")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, observed, context, 9)
    assert not result.is_synchronized
    assert result.status == SynchronizationStatus.ENGINE_MISMATCH
    
def test_invalid_observation():
    synchronizer = StateSynchronizer()
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed = ObservedState(timestamp=10.0, sequence_number=10, engine_id="engine_1", data_quality="INVALID")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, observed, context, 9)
    assert not result.is_synchronized
    assert result.status == SynchronizationStatus.INVALID_OBSERVATION

def test_insufficient_data_observation():
    synchronizer = StateSynchronizer()
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed = ObservedState(timestamp=10.0, sequence_number=10, engine_id="engine_1", data_quality="INSUFFICIENT_DATA")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, observed, context, 9)
    assert not result.is_synchronized
    assert result.status == SynchronizationStatus.INSUFFICIENT_DATA

def test_degraded_observation():
    synchronizer = StateSynchronizer()
    expected = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed = ObservedState(timestamp=10.0, sequence_number=10, engine_id="engine_1", data_quality="DEGRADED")
    context = OperatingContext()
    
    result = synchronizer.synchronize(expected, observed, context, 9)
    assert result.is_synchronized
    assert result.status == SynchronizationStatus.DEGRADED_OBSERVATION
    assert result.quality_effect == "DEGRADED"

def test_e1_and_e2_independence():
    # Test that E1 passing and E2 failing doesn't cause crosstalk
    synchronizer = StateSynchronizer()
    context = OperatingContext()
    
    # E1 match
    expected_e1 = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_1")
    observed_e1 = ObservedState(timestamp=10.0, sequence_number=10, engine_id="engine_1", data_quality="GOOD")
    res_e1 = synchronizer.synchronize(expected_e1, observed_e1, context, 9)
    assert res_e1.is_synchronized
    
    # E2 mismatch
    expected_e2 = HealthyExpectedState(timestamp=10.0, sequence_number=10, engine_id="engine_2")
    observed_e2 = ObservedState(timestamp=9.0, sequence_number=10, engine_id="engine_2", data_quality="GOOD")
    res_e2 = synchronizer.synchronize(expected_e2, observed_e2, context, 9)
    assert not res_e2.is_synchronized
    assert res_e2.status == SynchronizationStatus.STALE_OBSERVATION
