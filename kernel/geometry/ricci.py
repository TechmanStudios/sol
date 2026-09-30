"""
SOL Kernel: Non-Euclidean Geometry & Metric Deformation Engine
File: sol/kernel/geometry/ricci.py
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import scipy.linalg as la


@dataclass
class ExcitonTrajectory:
    """Represents active Exciton-MoA agent kinematics across the manifold."""
    agent_id: str
    node_id: int
    velocity: np.ndarray          # Tangent vector v in T_p M
    dwell_time: float             # Residence duration in seconds
    attention_weight: float       # Attention flux / heat injected


class EnergyMomentumTensor:
    """
    Formulates the semantic energy-momentum tensor T_ij:
        T_ij = rho * (v_i * v_j) + Theta_heat * g_ij
    where:
        rho: Normalized Exciton dwell density
        v: Exciton drift velocity in manifold coordinates
        Theta_heat: Attention entropy / thermal excitation
    Includes Fermi-Dirac soft saturation ceiling to prevent caustics:
        ||T|| <= t_max
    """
    def __init__(self, dim: int, kappa: float = 0.15, thermal_coupling: float = 0.05, t_max: float = 25.0):
        self.dim = dim
        self.kappa = kappa
        self.thermal_coupling = thermal_coupling
        self.t_max = t_max

    def compute(
        self,
        g_ij: np.ndarray,
        trajectories: List[ExcitonTrajectory],
        total_cluster_nodes: int = 1
    ) -> np.ndarray:
        T = np.zeros((self.dim, self.dim), dtype=np.float64)
        if not trajectories:
            return T

        total_dwell = sum(t.dwell_time for t in trajectories) + 1e-8
        for t in trajectories:
            v = np.asarray(t.velocity, dtype=np.float64).reshape(-1, 1)
            # Kinetic momentum flux: rho * (v (x) v)
            rho = t.dwell_time / total_dwell
            flux = rho * (v @ v.T)
            # Attention heat contribution
            heat = self.thermal_coupling * t.attention_weight * g_ij
            T += flux + heat

        T_scaled = self.kappa * T
        # Hardening 1: Fermi-Dirac soft saturation ceiling to prevent caustic blowup
        fro_norm = float(np.linalg.norm(T_scaled, 'fro'))
        if fro_norm > self.t_max:
            T_scaled = self.t_max * (T_scaled / fro_norm)

        return T_scaled


class DiscreteRicciFlowEngine:
    """
    Discrete Ricci deformation engine with Log-Euclidean Riemannian regularization.
    Guarantees strict positive-definiteness: det(g_ij) > 0, all lambda_k > 0.

    Equation:
        S = logm(g)
        d/dt S = -2 * R_ij + T_ij - mu * Tr(T_ij) * I
        g(t + dt) = expm(S_new)
    """
    def __init__(
        self,
        dim: int,
        dt: float = 0.015,
        kappa: float = 0.2,
        cosmological_mu: float = 0.01,
        min_eigenvalue: float = 1e-4,
        planck_volume_floor: float = 1e-6,
        max_condition_number: float = 100.0,
        t_max: float = 25.0
    ):
        self.dim = dim
        self.dt = dt
        self.kappa = kappa
        self.cosmological_mu = cosmological_mu
        self.min_eigenvalue = min_eigenvalue
        self.planck_volume_floor = planck_volume_floor
        self.max_condition_number = max_condition_number
        self.em_tensor = EnergyMomentumTensor(dim=dim, kappa=kappa, t_max=t_max)

    def compute_ricci_tensor(
        self,
        g_ij: np.ndarray,
        neighbor_metrics: List[np.ndarray],
        edge_weights: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """
        Computes discrete Ricci curvature using Ollivier-Forman finite-difference
        approximation over the local tangent bundle neighborhood.
        Avoids O(N^3) dense field inversion.
        """
        inv_g = la.pinvh(g_ij)
        laplacian_g = np.zeros_like(g_ij)
        total_w = float(np.sum(edge_weights)) + 1e-8

        # Vectorized weighted Laplace-Beltrami on localized metric chart
        for w, g_nbr in zip(edge_weights, neighbor_metrics):
            laplacian_g += (float(w) / total_w) * (g_nbr - g_ij)

        # Discrete Ricci curvature tensor: R_ij approx -0.5 * Delta_LB(g_ij)
        R_ij = -0.5 * laplacian_g
        # Ricci scalar R = Tr(g^{ik} R_kj)
        ricci_scalar = float(np.trace(inv_g @ R_ij))
        return R_ij, ricci_scalar

    def step(
        self,
        g_ij: np.ndarray,
        trajectories: List[ExcitonTrajectory],
        neighbor_metrics: List[np.ndarray],
        edge_weights: np.ndarray
    ) -> Tuple[np.ndarray, float, np.ndarray]:
        """
        Executes one discrete Ricci-backreaction step.
        Returns:
            g_new: Strictly positive-definite updated Riemannian metric tensor.
            ricci_scalar: Local Ricci scalar curvature R.
            T_ij: Active energy-momentum tensor.
        """
        # Ensure input symmetry
        g_sym = 0.5 * (g_ij + g_ij.T)

        # Eigen-projection to guard stability prior to matrix logarithm
        vals, vecs = la.eigh(g_sym)
        vals = np.clip(vals, self.min_eigenvalue, None)
        g_safe = vecs @ np.diag(vals) @ vecs.T

        # Transition to Log-Euclidean manifold S = log(g)
        S = la.logm(g_safe)
        if np.iscomplexobj(S):
            S = S.real

        # Compute Geometric Curvature & Energy-Momentum
        R_ij, R_scalar = self.compute_ricci_tensor(g_safe, neighbor_metrics, edge_weights)
        T_ij = self.em_tensor.compute(g_safe, trajectories, len(neighbor_metrics) + 1)

        # Metric Backreaction differential: dS/dt = -2 R_ij + T_ij - mu * Tr(T) * I
        trace_T = float(np.trace(T_ij))
        dS_dt = -2.0 * R_ij + T_ij - (self.cosmological_mu * trace_T * np.eye(self.dim))

        # Explicit geometric time-stepping in Lie algebra
        S_new = S + self.dt * dS_dt
        S_new = 0.5 * (S_new + S_new.T)

        # Hardening 1B: Enforce Planck volume form floor det(g) >= planck_volume_floor
        trace_S = float(np.trace(S_new))
        min_trace_S = float(np.log(self.planck_volume_floor))
        if trace_S < min_trace_S:
            S_new += ((min_trace_S - trace_S) / self.dim) * np.eye(self.dim)

        # Hardening 1C: Regularize condition number to prevent hyperbolic shear tearing
        s_vals, s_vecs = la.eigh(S_new)
        log_cond = s_vals[-1] - s_vals[0]
        max_log_cond = float(np.log(self.max_condition_number))
        if log_cond > max_log_cond:
            excess = log_cond - max_log_cond
            s_vals[0] += 0.5 * excess
            s_vals[-1] -= 0.5 * excess

        # Lie algebra spectral regularization: clamp log-stretches to prevent float64 overflow
        s_vals = np.clip(s_vals, np.log(self.min_eigenvalue), 10.0)
        S_new = s_vecs @ np.diag(s_vals) @ s_vecs.T

        # Exponential retraction back to the positive-definite Riemannian cone:
        # g_new = exp(S_new) guarantees lambda_k > 0 for all k
        g_new = la.expm(S_new)
        if np.iscomplexobj(g_new):
            g_new = g_new.real
        g_new = 0.5 * (g_new + g_new.T)

        # Enforce strict positive-definite floor
        vals_new, vecs_new = la.eigh(g_new)
        vals_clamped = np.clip(vals_new, self.min_eigenvalue, None)
        g_final = vecs_new @ np.diag(vals_clamped) @ vecs_new.T

        return g_final, R_scalar, T_ij
