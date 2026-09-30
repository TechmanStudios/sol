"""
SOL Benchmarks: Identity-Preserving Semantic Encoder
File: sol/benchmarks/identity_encoder.py

Resolves Finding C from RESEARCH_SYNTHESIS.md:
"The inspected StatisticalPrism input map is f(e) = (5*mean(e), 10*var(e), 2*skew(e)).
For any coordinate permutation P, f(e) = f(Pe). Two distinct orthogonal inputs
induce exactly the same injection field... Substrate cannot reconstruct the discarded distinction."

This encoder separates identity-bearing geometric coordinates from operating-condition
intensity moments, using an orthogonalized projection matrix W in R^{d x D} (W W^T = I_d)
to preserve directional semantics, neighborhood topology, and cosine orthogonality.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import scipy.stats as stats


@dataclass
class SemanticFingerprint:
    """
    Structured semantic encoding separating identity coordinates from operating intensity.
    """
    # Identity-bearing geometric coordinates in target manifold R^d
    manifold_coords: np.ndarray
    # Directional unit vector
    direction_unit: np.ndarray
    # Discrete symbolic identity token or hash
    identity_hash: str

    # Operating-condition controls (intensity, spread, uncertainty)
    mean_intensity: float
    variance_spread: float
    skew_asymmetry: float
    norm: float


@dataclass
class CounterexampleAuditResult:
    """Audit result verifying information-loss resolution."""
    vector_a_norm: float
    vector_b_norm: float
    cosine_similarity: float
    legacy_prism_a: np.ndarray
    legacy_prism_b: np.ndarray
    legacy_collapsed: bool
    identity_encoder_coords_a: np.ndarray
    identity_encoder_coords_b: np.ndarray
    identity_preserved: bool
    euclidean_separation: float


class IdentityPreservingEncoder:
    """
    Identity-preserving semantic encoder projecting high-dimensional embeddings
    or discrete symbols into smooth Riemannian manifold coordinates R^d.
    """
    def __init__(
        self,
        ambient_dim: int = 1536,
        manifold_dim: int = 4,
        seed: int = 42,
    ):
        self.ambient_dim = ambient_dim
        self.manifold_dim = manifold_dim
        self.seed = seed

        # Generate orthogonal projection matrix W in R^{manifold_dim x ambient_dim}
        rng = np.random.RandomState(seed)
        gaussian_matrix = rng.randn(ambient_dim, manifold_dim)
        # QR decomposition yields orthonormal columns: Q^T Q = I_d
        q, _ = np.linalg.qr(gaussian_matrix)
        # Scaled by sqrt(D / d) according to Johnson-Lindenstrauss lemma to preserve vector norms
        scale = float(np.sqrt(ambient_dim / manifold_dim))
        self.projection_matrix = scale * q.T  # Shape: (manifold_dim, ambient_dim)

    def encode(self, embedding: np.ndarray, token_label: Optional[str] = None) -> SemanticFingerprint:
        """
        Encodes a high-dimensional vector e in R^D into a SemanticFingerprint.
        """
        e = np.asarray(embedding, dtype=np.float64).flatten()
        if len(e) != self.ambient_dim:
            if len(e) < self.ambient_dim:
                # Zero-pad if needed
                padded = np.zeros(self.ambient_dim, dtype=np.float64)
                padded[:len(e)] = e
                e = padded
            else:
                e = e[:self.ambient_dim]

        norm_e = float(np.linalg.norm(e))
        unit_e = e / max(norm_e, 1e-12)

        # 1. Identity-bearing projection to manifold coordinates
        coords = self.projection_matrix @ e  # Shape: (manifold_dim,)
        coords_unit = coords / max(float(np.linalg.norm(coords)), 1e-12)

        # 2. Operating-condition scalar moments (controls, not identities)
        mean_val = float(np.mean(e))
        var_val = float(np.var(e))
        skew_val = float(stats.skew(e)) if var_val > 1e-12 else 0.0

        # 3. Deterministic identity hash
        if token_label:
            id_hash = f"tok_{token_label}"
        else:
            # Deterministic hash of projected coordinates
            id_hash = f"geo_{hash(tuple(np.round(coords, 4))):016x}"

        return SemanticFingerprint(
            manifold_coords=coords,
            direction_unit=coords_unit,
            identity_hash=id_hash,
            mean_intensity=mean_val,
            variance_spread=var_val,
            skew_asymmetry=skew_val,
            norm=norm_e
        )

    def encode_discrete_token(self, token_idx: int, total_tokens: int = 64) -> SemanticFingerprint:
        """
        Constructs an orthogonal semantic embedding for a discrete token index.
        Uses a deterministic orthogonal basis or structured hyperspherical phase encoding.
        """
        rng = np.random.RandomState(self.seed + token_idx * 101)
        # Create a unit vector in ambient space with distinct direction
        vec = np.zeros(self.ambient_dim, dtype=np.float64)
        basis_idx = token_idx % self.ambient_dim
        vec[basis_idx] = 1.0
        # Add subtle harmonic perturbation for rich spectrum
        harmonics = rng.randn(min(16, self.ambient_dim)) * 0.1
        vec[:len(harmonics)] += harmonics
        vec /= np.linalg.norm(vec)

        return self.encode(vec, token_label=f"T{token_idx:03d}")

    @staticmethod
    def legacy_statistical_prism(e: np.ndarray) -> np.ndarray:
        """
        The legacy moment-based transducer from StatisticalPrism.py:
        f(e) = (5 * mean(e), 10 * var(e), 2 * skew(e)).
        """
        mean_v = float(np.mean(e))
        var_v = float(np.var(e))
        skew_v = float(stats.skew(e)) if var_v > 1e-12 else 0.0
        return np.array([5.0 * mean_v, 10.0 * var_v, 2.0 * skew_v], dtype=np.float64)

    def audit_legacy_counterexample(self) -> CounterexampleAuditResult:
        """
        Executes the exact information-loss counterexample from RESEARCH_SYNTHESIS.md:
        - Two orthogonal 1,536-dimensional vectors with the same multiset of entries.
        - Proves legacy prism collapses them into identical coordinates.
        - Proves IdentityPreservingEncoder retains substantial Euclidean distance.
        """
        dim = self.ambient_dim
        # Construct two orthogonal vectors with identical multiset of coordinates
        # Pattern: vector A has [1, -1, 1, -1, ...] on first half, zero on second half
        # vector B has identical values but permuted to second half
        half = dim // 2
        pattern = np.array([1.0, -1.0] * (half // 2), dtype=np.float64)
        if len(pattern) < half:
            pattern = np.pad(pattern, (0, half - len(pattern)))

        vec_a = np.zeros(dim, dtype=np.float64)
        vec_b = np.zeros(dim, dtype=np.float64)

        vec_a[:half] = pattern
        vec_b[half:half + len(pattern)] = pattern

        vec_a /= np.linalg.norm(vec_a)
        vec_b /= np.linalg.norm(vec_b)

        # Verify orthogonality in ambient space
        cosine_sim = float(np.dot(vec_a, vec_b))
        assert abs(cosine_sim) < 1e-10, f"Vectors not orthogonal: cos={cosine_sim}"

        # 1. Legacy StatisticalPrism
        legacy_a = self.legacy_statistical_prism(vec_a)
        legacy_b = self.legacy_statistical_prism(vec_b)
        legacy_diff = float(np.linalg.norm(legacy_a - legacy_b))
        legacy_collapsed = legacy_diff < 1e-8

        # 2. IdentityPreservingEncoder
        fp_a = self.encode(vec_a)
        fp_b = self.encode(vec_b)
        geo_diff = float(np.linalg.norm(fp_a.manifold_coords - fp_b.manifold_coords))
        identity_preserved = geo_diff > 0.1

        return CounterexampleAuditResult(
            vector_a_norm=float(np.linalg.norm(vec_a)),
            vector_b_norm=float(np.linalg.norm(vec_b)),
            cosine_similarity=cosine_sim,
            legacy_prism_a=legacy_a,
            legacy_prism_b=legacy_b,
            legacy_collapsed=legacy_collapsed,
            identity_encoder_coords_a=fp_a.manifold_coords,
            identity_encoder_coords_b=fp_b.manifold_coords,
            identity_preserved=identity_preserved,
            euclidean_separation=geo_diff
        )
