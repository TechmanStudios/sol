"""
SOL Kernel: Vector 8 Autonomous Self-Assembling Riemannian Semantic Circuits
Package: sol.kernel.synthesis

Exports continuous Riemannian circuit topology, autonomous synthesis engine,
neuro-symbolic reflection, and dynamic online metaplasticity.
"""

from sol.kernel.synthesis.circuit_topology import (
    CircuitNodeType,
    CircuitNode,
    CircuitEvaluationResult,
    SelfAssembledCircuit
)
from sol.kernel.synthesis.circuit_synthesizer import (
    TruthTableSpec,
    CANONICAL_SPECS,
    SynthesisResult,
    RiemannianCircuitSynthesizer,
    build_canonical_specs
)
from sol.kernel.synthesis.symbolic_reflector import (
    DAGNodeInfo,
    CircuitDAG,
    SymbolicReflectionReport,
    SymbolicReflector
)
from sol.kernel.synthesis.metaplasticity import (
    MetaplasticityReport,
    MetaplasticityEngine
)

__all__ = [
    "CircuitNodeType",
    "CircuitNode",
    "CircuitEvaluationResult",
    "SelfAssembledCircuit",
    "TruthTableSpec",
    "CANONICAL_SPECS",
    "SynthesisResult",
    "RiemannianCircuitSynthesizer",
    "build_canonical_specs",
    "DAGNodeInfo",
    "CircuitDAG",
    "SymbolicReflectionReport",
    "SymbolicReflector",
    "MetaplasticityReport",
    "MetaplasticityEngine"
]
