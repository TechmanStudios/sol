"""
SOL Kernel: Causal Emergence and Effective Information (EI) Framework
File: sol/kernel/causal/__init__.py

Implements Erik Hoel's Effective Information (EI) metrics and causal emergence
analysis across continuous Riemannian semantic circuits and autonomous exciton swarms.
"""

from .effective_information import (
    CausalMetrics,
    CausalEmergenceReport,
    compute_entropy,
    compute_tpm_determinism,
    compute_tpm_degeneracy,
    compute_effective_information,
    coarse_grain_tpm,
    compute_causal_emergence,
    generate_hoel_canonical_network,
    generate_noisy_logic_micro_tpm,
)

__all__ = [
    "CausalMetrics",
    "CausalEmergenceReport",
    "compute_entropy",
    "compute_tpm_determinism",
    "compute_tpm_degeneracy",
    "compute_effective_information",
    "coarse_grain_tpm",
    "compute_causal_emergence",
    "generate_hoel_canonical_network",
    "generate_noisy_logic_micro_tpm",
]
