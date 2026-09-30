"""
SOL Diagnostics: Damping Spectrogram & Manifold Stability Monitor
File: sol/diagnostics/damping_spectrogram.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np


@dataclass
class DampingTelemetryFrame:
    timestamp_ms: float
    ricci_scalar: float
    velocity_norm_g: float
    damping_coefficient: float
    kinetic_energy: float
    dissipation_rate: float
    metric_eigenvalues: List[float]
    divergence_flag: bool


class AdaptiveDampingStabilizer:
    """
    Formulates the adaptive damping coefficient gamma(v, R):
    - Quenches kinetic blowup near singularities (R -> inf => gamma -> gamma_max)
    - Minimizes drag across flat semantic voids (R -> 0 => gamma -> gamma_min)
    """
    def __init__(
        self,
        gamma_min: float = 0.05,
        gamma_max: float = 50.0,
        r_crit: float = 12.0,
        tau: float = 2.5,
        velocity_coupling: float = 0.1,
        divergence_threshold: float = 25.0
    ):
        self.gamma_min = gamma_min
        self.gamma_max = gamma_max
        self.r_crit = r_crit
        self.tau = tau
        self.velocity_coupling = velocity_coupling
        self.divergence_threshold = divergence_threshold

    def compute_gamma(self, v: np.ndarray, g_ij: np.ndarray, ricci_scalar: float) -> Tuple[float, float, float]:
        """
        Calculates:
            gamma: Total dynamic friction
            v_norm_g: Kinetic velocity norm sqrt(v^T * g * v)
            kinetic_energy: E_k = 0.5 * v^T * g * v
        """
        # Inner product on Riemannian tangent space <v, v>_g = v^T g v
        v_col = np.asarray(v, dtype=np.float64).reshape(-1, 1)
        v_norm_sq = float((v_col.T @ g_ij @ v_col)[0, 0])
        v_norm_sq = max(v_norm_sq, 0.0)
        v_norm_g = float(np.sqrt(v_norm_sq))
        kinetic_energy = 0.5 * v_norm_sq

        # Sigmoidal response to curvature strain
        curvature_strain = (abs(ricci_scalar) - self.r_crit) / self.tau
        curvature_factor = 1.0 / (1.0 + np.exp(-np.clip(curvature_strain, -15.0, 15.0)))
        gamma_curvature = self.gamma_min + (self.gamma_max - self.gamma_min) * curvature_factor

        # Velocity-dependent hydrodynamic drag
        gamma_total = gamma_curvature + self.velocity_coupling * v_norm_sq
        return float(gamma_total), v_norm_g, kinetic_energy


class DampingSpectrogram:
    """
    Logs, tracks, and structures multi-scale damping telemetry for sol-lens streaming.
    """
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.frames: List[DampingTelemetryFrame] = []
        self.stabilizer = AdaptiveDampingStabilizer()

    def record_state(
        self,
        timestamp_ms: float,
        v: np.ndarray,
        g_ij: np.ndarray,
        ricci_scalar: float
    ) -> DampingTelemetryFrame:
        gamma, v_norm_g, e_k = self.stabilizer.compute_gamma(v, g_ij, ricci_scalar)
        dissipation_rate = gamma * (v_norm_g ** 2)

        eigenvalues = [float(x) for x in np.sort(np.linalg.eigvalsh(g_ij))]
        divergence = ricci_scalar > self.stabilizer.divergence_threshold or eigenvalues[0] <= 0

        frame = DampingTelemetryFrame(
            timestamp_ms=timestamp_ms,
            ricci_scalar=ricci_scalar,
            velocity_norm_g=v_norm_g,
            damping_coefficient=gamma,
            kinetic_energy=e_k,
            dissipation_rate=dissipation_rate,
            metric_eigenvalues=eigenvalues,
            divergence_flag=divergence
        )

        self.frames.append(frame)
        if len(self.frames) > self.buffer_size:
            self.frames.pop(0)

        return frame

    def get_spectrogram_matrix(self) -> Dict[str, np.ndarray]:
        """Exports vectorized telemetry channels for 3D sol-lens visualization."""
        if not self.frames:
            return {}
        return {
            "timestamps": np.array([f.timestamp_ms for f in self.frames]),
            "ricci_scalar": np.array([f.ricci_scalar for f in self.frames]),
            "gamma": np.array([f.damping_coefficient for f in self.frames]),
            "dissipation": np.array([f.dissipation_rate for f in self.frames]),
            "eigenvalue_min": np.array([f.metric_eigenvalues[0] for f in self.frames]),
        }
