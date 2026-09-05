"""
Module 02 Deterministic Random Number Generator (Phase 1 Foundation).
SIH26054 — Module 02 Engine Simulator.
"""

import random
from typing import Any, List, Sequence
import numpy as np


class DeterministicRNG:
    """
    Central deterministic pseudo-random number generator for Module 02.
    Ensures 100% reproducible simulation streams given the master random seed.
    """

    def __init__(self, master_seed: int = 42) -> None:
        self._master_seed: int = int(master_seed)
        self._py_rng = random.Random(self._master_seed)
        self._np_rng = np.random.default_rng(self._master_seed)

    @property
    def master_seed(self) -> int:
        return self._master_seed

    def reseed(self, new_seed: int) -> None:
        """Reseeds both Python and NumPy RNGs deterministically."""
        self._master_seed = int(new_seed)
        self._py_rng = random.Random(self._master_seed)
        self._np_rng = np.random.default_rng(self._master_seed)

    def gauss(self, mean: float = 0.0, std: float = 1.0) -> float:
        """Returns Gaussian (normal) distributed float sample N(mean, std^2)."""
        return float(self._py_rng.gauss(mean, std))

    def uniform(self, low: float = 0.0, high: float = 1.0) -> float:
        """Returns uniformly distributed float sample in range [low, high)."""
        return float(self._py_rng.uniform(low, high))

    def choice(self, seq: Sequence[Any]) -> Any:
        """Selects a random element from a non-empty sequence."""
        return self._py_rng.choice(seq)

    def normal_array(self, loc: float = 0.0, scale: float = 1.0, size: int = 1) -> np.ndarray:
        """Returns array of Gaussian distributed float samples from NumPy generator."""
        return self._np_rng.normal(loc=loc, scale=scale, size=size)
