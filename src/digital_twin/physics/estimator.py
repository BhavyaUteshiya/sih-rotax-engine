"""
Digital Twin State Estimator.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from typing import Dict, Any, Type
import logging

from src.digital_twin.models.estimated_actual_state import EstimatedActualState
from src.digital_twin.models.observed_state import ObservedState

logger = logging.getLogger(__name__)


class BaseEstimator:
    """
    Abstract interface for Digital Twin telemetry synchronization.
    Takes a predicted internal state and incoming telemetry (ObservedState),
    and produces a corrected internal state.
    """
    def synchronize(self, predicted: EstimatedActualState, observed: ObservedState) -> EstimatedActualState:
        raise NotImplementedError


class AlphaFilterEstimator(BaseEstimator):
    """
    Simple proportional gain (Alpha/Complementary filter) estimator.
    Corrects the predicted internal state toward the observed telemetry by a factor of alpha.
    Alpha = 0.0 -> Pure simulation prediction (ignores telemetry).
    Alpha = 1.0 -> Pure telemetry copying (overwrites internal state).
    """
    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha
        
        # We only synchronize variables that are both in the Internal State and Telemetry.
        self.state_to_obs_mapping = {
            "map_bar": "map_bar",
            "rpm": "rpm",
            "egt_c": "egt_c",
            "cht_c": "cht_c",
            "oil_temp_c": "oil_temp_c",
        }

    def synchronize(self, predicted: EstimatedActualState, observed: ObservedState) -> EstimatedActualState:
        corrected = EstimatedActualState(timestamp=predicted.timestamp)
        
        # Handle invalid telemetry: fallback to pure prediction
        if observed.data_quality in ["INSUFFICIENT_DATA", "INVALID"]:
            logger.debug("Estimator: Poor telemetry quality, falling back to pure prediction.")
            for attr in self.state_to_obs_mapping.keys():
                setattr(corrected, attr, getattr(predicted, attr))
            return corrected

        # Apply proportional gain to valid observations
        for state_attr, obs_attr in self.state_to_obs_mapping.items():
            pred_val = getattr(predicted, state_attr)
            obs_val = getattr(observed, obs_attr, None)
            
            if obs_val is not None:
                # Core estimator update: Corrected = Predicted + Alpha * (Observed - Predicted)
                corr_val = pred_val + self.alpha * (obs_val - pred_val)
                setattr(corrected, state_attr, corr_val)
            else:
                setattr(corrected, state_attr, pred_val)
                
        return corrected
