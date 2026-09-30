"""
SOL Benchmarks: Quantitative Scientific Evaluation & Comparative Baselines
Package: sol.benchmarks
"""

from sol.benchmarks.identity_encoder import (
    IdentityPreservingEncoder,
    SemanticFingerprint,
    CounterexampleAuditResult
)
from sol.benchmarks.flagship_task import (
    DelayedRecallTrial,
    FlagshipTaskGenerator,
    GroundTruthOracle,
    TrialType,
    TrialResult
)
from sol.benchmarks.baselines import (
    ExplicitFSMDAGBaseline,
    LinearGraphDiffusionBaseline,
    EchoStateReservoirBaseline
)
from sol.benchmarks.sol_evaluator import (
    SolBenchmarkEvaluator,
    EvaluationMode
)
from sol.benchmarks.delayed_recall_runner import (
    FlagshipBenchmarkRunner,
    BenchmarkSuiteResults
)

__all__ = [
    "IdentityPreservingEncoder",
    "SemanticFingerprint",
    "CounterexampleAuditResult",
    "DelayedRecallTrial",
    "FlagshipTaskGenerator",
    "GroundTruthOracle",
    "TrialType",
    "TrialResult",
    "ExplicitFSMDAGBaseline",
    "LinearGraphDiffusionBaseline",
    "EchoStateReservoirBaseline",
    "SolBenchmarkEvaluator",
    "EvaluationMode",
    "FlagshipBenchmarkRunner",
    "BenchmarkSuiteResults",
]
