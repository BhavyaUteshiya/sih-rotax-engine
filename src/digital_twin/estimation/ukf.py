import numpy as np
from typing import Callable, Tuple, Optional

class UnscentedKalmanFilter:
    """
    Deterministic Unscented Kalman Filter (UKF) for Phase 2D State Estimation.
    Uses numerical safety checks and explicit sigma-point generation.
    """
    def __init__(self, 
                 dim_x: int, 
                 dim_z: int, 
                 dt: float, 
                 alpha: float, 
                 beta: float, 
                 kappa: float,
                 Q: np.ndarray,
                 R: np.ndarray,
                 P0: np.ndarray,
                 numerical_tolerance: float = 1e-6):
        self.dim_x = dim_x
        self.dim_z = dim_z
        self.dt = dt
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa
        
        self.Q = Q
        self.R = R
        self.P = P0.copy()
        self.x = np.zeros(dim_x)
        self.numerical_tolerance = numerical_tolerance
        
        # Sigma point weights
        self._compute_weights()

    def _compute_weights(self):
        """Computes sigma point weights for mean and covariance."""
        lambda_ = self.alpha**2 * (self.dim_x + self.kappa) - self.dim_x
        self.c = self.dim_x + lambda_
        
        self.Wc = np.full(2 * self.dim_x + 1, 1.0 / (2 * self.c))
        self.Wm = np.full(2 * self.dim_x + 1, 1.0 / (2 * self.c))
        
        self.Wc[0] = lambda_ / self.c + (1 - self.alpha**2 + self.beta)
        self.Wm[0] = lambda_ / self.c

    def _generate_sigma_points(self, x: np.ndarray, P: np.ndarray) -> np.ndarray:
        """Generates 2*dim_x + 1 sigma points safely."""
        sigma_points = np.zeros((2 * self.dim_x + 1, self.dim_x))
        sigma_points[0] = x
        
        # Protect against non-positive-semidefinite P
        # Enforce symmetry
        P = (P + P.T) / 2.0
        
        # Check for NaN/Inf in state and covariance
        if not np.isfinite(x).all():
            raise ValueError("State vector contains NaN/Inf values.")
        if not np.isfinite(P).all():
            raise ValueError("Covariance matrix contains NaN/Inf values.")
            
        try:
            L = np.linalg.cholesky(self.c * P)
        except np.linalg.LinAlgError:
            # Fallback to eigenvalue decomposition if Cholesky fails due to numerical noise
            eigenvalues, eigenvectors = np.linalg.eigh(P)
            eigenvalues = np.maximum(eigenvalues, self.numerical_tolerance) # prevent negative/zero eigenvalues
            P_safe = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
            L = np.linalg.cholesky(self.c * P_safe)

        for i in range(self.dim_x):
            sigma_points[i + 1] = x + L[:, i]
            sigma_points[self.dim_x + i + 1] = x - L[:, i]
            
        return sigma_points

    def _unscented_transform(self, sigmas: np.ndarray, Wm: np.ndarray, Wc: np.ndarray, noise_cov: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Calculates mean and covariance from sigma points."""
        x = np.dot(Wm, sigmas)
        
        y = sigmas - x[np.newaxis, :]
        P = np.dot(y.T, np.dot(np.diag(Wc), y)) + noise_cov
        
        # Enforce symmetry
        P = (P + P.T) / 2.0
        return x, P

    def predict(self, fx: Callable[[np.ndarray, float], np.ndarray]) -> None:
        """
        Prediction step.
        fx is the state transition function f(x, dt).
        """
        sigmas = self._generate_sigma_points(self.x, self.P)
        
        # Pass each sigma point through the process model
        sigmas_f = np.zeros_like(sigmas)
        for i in range(len(sigmas)):
            sigmas_f[i] = fx(sigmas[i], self.dt)
            
        self.x, self.P = self._unscented_transform(sigmas_f, self.Wm, self.Wc, self.Q)

    def update(self, z: np.ndarray, measurement_mapping: np.ndarray, R_active: np.ndarray) -> None:
        """
        Measurement update step.
        z is the vector of available measurements.
        measurement_mapping is a boolean array or index array mapping the active measurements to the state vector.
        We assume h(x) is linear selection of states for Phase 2D (we only observe states directly).
        If h(x) is nonlinear, we would need to pass hx function and transform sigmas.
        For Phase 2D, we extract the corresponding sigma points.
        """
        if len(z) == 0:
            # No valid measurements, skip update
            return
            
        # Re-generate sigma points around predicted mean
        sigmas = self._generate_sigma_points(self.x, self.P)
        
        # Map state sigma points to measurement space (linear selection)
        # Assuming measurement_mapping contains indices of the state vector being measured
        sigmas_h = sigmas[:, measurement_mapping]
        
        # Mean and covariance of predicted measurement
        zp, Pz = self._unscented_transform(sigmas_h, self.Wm, self.Wc, R_active)
        
        # Cross covariance
        Pxz = np.zeros((self.dim_x, len(z)))
        for i in range(len(self.Wm)):
            dx = sigmas[i] - self.x
            dz = sigmas_h[i] - zp
            Pxz += self.Wc[i] * np.outer(dx, dz)
            
        # Kalman Gain
        # We use a linear solve instead of explicit inversion for numerical stability: K @ Pz = Pxz  => K = Pxz @ inv(Pz) => solve(Pz.T, Pxz.T).T
        try:
            K = np.linalg.solve(Pz.T, Pxz.T).T
        except np.linalg.LinAlgError:
            # Singular measurement covariance, add numerical tolerance
            Pz_safe = Pz + np.eye(len(z)) * self.numerical_tolerance
            K = np.linalg.solve(Pz_safe.T, Pxz.T).T
            
        # Innovation
        y = z - zp
        
        # State Update
        self.x = self.x + np.dot(K, y)
        self.P = self.P - np.dot(K, np.dot(Pz, K.T))
        
        # Enforce symmetry
        self.P = (self.P + self.P.T) / 2.0
        
        # Verify PSD (Eigenvalue clipping)
        eigenvalues, eigenvectors = np.linalg.eigh(self.P)
        if (eigenvalues < 0).any():
            eigenvalues = np.maximum(eigenvalues, self.numerical_tolerance)
            self.P = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
