"""
SOL Kernel: Geometry & Metric Deformation Subsystem
"""

from sol.kernel.geometry.ricci import (
    DiscreteRicciFlowEngine,
    EnergyMomentumTensor,
    ExcitonTrajectory
)
from sol.kernel.geometry.logic_manifold import (
    LogicGateType,
    LogicGateResult,
    RiemannianLogicManifold,
    FullAdderResult,
    RippleCarryResult,
    RippleCarryManifoldCircuit,
    ALUOp,
    ALUResult,
    RiemannianALU
)

__all__ = [
    "DiscreteRicciFlowEngine",
    "EnergyMomentumTensor",
    "ExcitonTrajectory",
    "LogicGateType",
    "LogicGateResult",
    "RiemannianLogicManifold",
    "FullAdderResult",
    "RippleCarryResult",
    "RippleCarryManifoldCircuit",
    "ALUOp",
    "ALUResult",
    "RiemannianALU"
]
