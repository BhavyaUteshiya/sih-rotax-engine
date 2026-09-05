import pytest
from unittest.mock import patch, MagicMock
from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.twin_state import DigitalTwinStatus, DigitalTwinDataQuality
from src.digital_twin.models.synchronization_result import SynchronizationStatus

def test_engine_isolation_and_sequence_tracking():
    """Verify E1 and E2 sequence histories are isolated and rejected observations don't corrupt them."""
    engine = DigitalTwinEngine()
    context = OperatingContext(throttle_position=0.8)
    
    # 1. Initialize E1 sequence
    obs_e1_1 = ObservedState(engine_id="engine_1", timestamp=10.0, sequence_number=1, data_quality="GOOD")
    state_e1_1 = engine.process_step(context, 1.0, obs_e1_1, engine_index=1, timestamp=10.0)
    assert state_e1_1.status == DigitalTwinStatus.SYNCHRONIZED
    assert engine.last_sequence[1] == 1
    
    # 2. Try to update E1 with duplicate sequence (OUT_OF_ORDER)
    obs_e1_dup = ObservedState(engine_id="engine_1", timestamp=11.0, sequence_number=1, data_quality="GOOD")
    state_e1_dup = engine.process_step(context, 1.0, obs_e1_dup, engine_index=1, timestamp=11.0)
    assert state_e1_dup.status == DigitalTwinStatus.SYNC_FAILED
    assert state_e1_dup.synchronization_result.status == SynchronizationStatus.OUT_OF_ORDER
    # Ensure sequence was NOT advanced by the rejected duplicate
    assert engine.last_sequence[1] == 1
    
    # 3. Initialize E2 sequence (should be independent of E1)
    obs_e2_1 = ObservedState(engine_id="engine_2", timestamp=10.0, sequence_number=5, data_quality="GOOD")
    state_e2_1 = engine.process_step(context, 1.0, obs_e2_1, engine_index=2, timestamp=10.0)
    assert state_e2_1.status == DigitalTwinStatus.SYNCHRONIZED
    assert engine.last_sequence[2] == 5
    assert engine.last_sequence[1] == 1 # E1 untouched
    
    # 4. Inject engine mismatch (Observe E2, give to E1 processor)
    obs_mismatch = ObservedState(engine_id="engine_2", timestamp=12.0, sequence_number=2, data_quality="GOOD")
    state_mismatch = engine.process_step(context, 1.0, obs_mismatch, engine_index=1, timestamp=12.0)
    assert state_mismatch.status == DigitalTwinStatus.SYNC_FAILED
    assert state_mismatch.synchronization_result.status == SynchronizationStatus.ENGINE_MISMATCH
    assert engine.last_sequence[1] == 1 # E1 untouched

@patch('src.digital_twin.services.twin_engine.ResidualAnalyzer.analyze')
@patch('src.digital_twin.services.twin_engine.CausalAnalyzer.analyze_causal_chain')
def test_downstream_bypass_on_sync_failure(mock_causal, mock_residual):
    """Verify ResidualAnalyzer and CausalAnalyzer are bypassed on sync failure."""
    engine = DigitalTwinEngine()
    context = OperatingContext()
    
    # 1. Provide an explicitly invalid observation (timestamps misaligned by 2s)
    obs = ObservedState(engine_id="engine_1", timestamp=10.0, sequence_number=1, data_quality="GOOD")
    state = engine.process_step(context, 1.0, obs, engine_index=1, timestamp=12.0)
    
    # 2. Check sync failed
    assert state.synchronization_result.is_synchronized is False
    assert state.synchronization_result.status == SynchronizationStatus.STALE_OBSERVATION
    
    # 3. Check mocks to ensure downstream analysis was bypassed
    mock_residual.assert_not_called()
    mock_causal.assert_not_called()
    
    # 4. Check success path calls them
    obs_good = ObservedState(engine_id="engine_1", timestamp=13.0, sequence_number=2, data_quality="GOOD")
    
    mock_res_val = MagicMock()
    mock_res_val.warnings_count = 0
    mock_res_val.criticals_count = 0
    mock_residual.return_value = mock_res_val
    
    state_good = engine.process_step(context, 1.0, obs_good, engine_index=1, timestamp=13.0)
    assert state_good.synchronization_result.is_synchronized is True
    mock_residual.assert_called_once()
    mock_causal.assert_called_once()

def test_missing_and_invalid_data_semantics():
    engine = DigitalTwinEngine()
    context = OperatingContext()
    
    # MISSING
    state_missing = engine.process_step(context, 1.0, None, engine_index=1, timestamp=10.0)
    assert state_missing.status == DigitalTwinStatus.INSUFFICIENT_DATA
    assert state_missing.data_quality == DigitalTwinDataQuality.INSUFFICIENT_DATA
    
    # INSUFFICIENT
    obs_insuff = ObservedState(engine_id="engine_1", timestamp=11.0, sequence_number=1, data_quality="INSUFFICIENT_DATA")
    state_insuff = engine.process_step(context, 1.0, obs_insuff, engine_index=1, timestamp=11.0)
    assert state_insuff.status == DigitalTwinStatus.INSUFFICIENT_DATA
    assert state_insuff.data_quality == DigitalTwinDataQuality.INSUFFICIENT_DATA
    
    # INVALID
    obs_invalid = ObservedState(engine_id="engine_1", timestamp=12.0, sequence_number=2, data_quality="INVALID")
    state_invalid = engine.process_step(context, 1.0, obs_invalid, engine_index=1, timestamp=12.0)
    assert state_invalid.status == DigitalTwinStatus.SYNC_FAILED
    assert state_invalid.data_quality == DigitalTwinDataQuality.INVALID

def test_deterministic_repeated_execution():
    engine = DigitalTwinEngine()
    context = OperatingContext()
    
    # Identical inputs should produce identical outputs (including sync result)
    obs = ObservedState(engine_id="engine_1", timestamp=10.0, sequence_number=1, data_quality="GOOD")
    state1 = engine.process_step(context, 1.0, obs, engine_index=1, timestamp=10.0)
    
    engine2 = DigitalTwinEngine()
    state2 = engine2.process_step(context, 1.0, obs, engine_index=1, timestamp=10.0)
    
    assert state1.synchronization_result == state2.synchronization_result
