"""
SOL Benchmarks: Flagship Delayed-Recall & Conflict-Routing Benchmark Runner
File: sol/benchmarks/delayed_recall_runner.py

Orchestrates the full comparative benchmark suite across:
- 3 External Baselines: Explicit FSM/DAG, Linear Diffusion, Echo State Reservoir
- 4 SOL Configurations: Adaptive Swarm, Frozen Controller, Controller Only, Substrate Ablated

Computes aggregated metrics:
- Recall Accuracy on Valid Trials (%)
- Conflict Rejection Rate on Contradictory Trials (%)
- False Commit Rate on Contradictory Trials (%) [Target: 0.00%]
- Read-Disturb Margin (Ratio)
- Recovery Time (Steps)
- Thermodynamic Dissipated Energy (Work)
- Wall-Clock Latency (ms)
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from sol.benchmarks.identity_encoder import IdentityPreservingEncoder
from sol.benchmarks.flagship_task import (
    DelayedRecallTrial,
    FlagshipTaskGenerator,
    TrialResult,
    TrialType
)
from sol.benchmarks.baselines import (
    ExplicitFSMDAGBaseline,
    LinearGraphDiffusionBaseline,
    EchoStateReservoirBaseline
)
from sol.benchmarks.sol_evaluator import SolBenchmarkEvaluator, EvaluationMode


@dataclass
class ModelAggregateMetrics:
    """Aggregated statistical metrics for a single model across benchmark trials."""
    model_name: str
    total_trials: int
    valid_trials_count: int
    conflict_trials_count: int
    recall_accuracy: float                  # Accuracy on valid trials (0.0 to 1.0)
    conflict_rejection_rate: float          # Quarantine/Hold rate on conflict trials (0.0 to 1.0)
    false_commit_rate: float                # False positive commits on conflict trials (0.0 to 1.0)
    mean_read_disturb_margin: float         # Mean ratio of read2 / read1
    mean_recovery_time_steps: float         # Mean settling steps
    mean_energy_dissipated: float           # Mean Carnot work dissipated
    mean_latency_ms: float                  # Mean wall-clock time per trial
    total_memory_kb: float                  # Peak memory footprint in KB


@dataclass
class BenchmarkSuiteResults:
    """Complete summary of a benchmark suite execution."""
    suite_id: str
    total_trials: int
    model_metrics: Dict[str, ModelAggregateMetrics]
    trial_records: List[TrialResult]
    audit_counterexample: Dict[str, Any]

    def to_summary_table(self) -> str:
        """Renders markdown summary comparison table."""
        header = (
            "| Model Architecture | Valid Recall Acc | Conflict Reject Rate | False Commit Rate | Read-Disturb Margin | Mean Latency | Mean Energy (dE) |\n"
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
        )
        rows = [header]
        for name, m in self.model_metrics.items():
            row = (
                f"| **{m.model_name}** | {m.recall_accuracy * 100:.1f}% | "
                f"{m.conflict_rejection_rate * 100:.1f}% | {m.false_commit_rate * 100:.1f}% | "
                f"{m.mean_read_disturb_margin:.3f} | {m.mean_latency_ms:.2f} ms | {m.mean_energy_dissipated:.3f} |"
            )
            rows.append(row)
        return "\n".join(rows)


class FlagshipBenchmarkRunner:
    """
    High-level orchestrator for the Flagship Delayed-Recall & Conflict-Routing Benchmark.
    """
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        ambient_dim: int = 1536,
        manifold_dim: int = 4
    ):
        self.storage_dir = storage_dir or Path(".benchmark_results")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.encoder = IdentityPreservingEncoder(ambient_dim=ambient_dim, manifold_dim=manifold_dim)

    def run_suite(
        self,
        num_trials: int = 30,
        delay_steps_list: Optional[List[int]] = None,
        topology_seed: int = 1001,
        input_seed: int = 2002
    ) -> BenchmarkSuiteResults:
        """
        Executes all 7 model configurations across the synthetic trial suite.
        """
        if delay_steps_list is None:
            delay_steps_list = [5, 15, 30, 60]

        # 1. Audit Information-Loss Resolution
        audit = self.encoder.audit_legacy_counterexample()
        audit_dict = {
            "cosine_similarity": audit.cosine_similarity,
            "legacy_collapsed": audit.legacy_collapsed,
            "identity_preserved": audit.identity_preserved,
            "euclidean_separation": audit.euclidean_separation
        }

        # 2. Generate Balanced Trials
        generator = FlagshipTaskGenerator(
            topology_seed=topology_seed,
            input_seed=input_seed
        )
        trials = generator.generate_suite(
            num_trials=num_trials,
            delay_steps_list=delay_steps_list
        )

        # 3. Instantiate Models
        models = [
            ExplicitFSMDAGBaseline(encoder=self.encoder),
            LinearGraphDiffusionBaseline(encoder=self.encoder),
            EchoStateReservoirBaseline(encoder=self.encoder),
            SolBenchmarkEvaluator(mode=EvaluationMode.ADAPTIVE_SWARM, encoder=self.encoder, storage_dir=self.storage_dir),
            SolBenchmarkEvaluator(mode=EvaluationMode.FROZEN_CONTROLLER, encoder=self.encoder, storage_dir=self.storage_dir),
            SolBenchmarkEvaluator(mode=EvaluationMode.CONTROLLER_ONLY, encoder=self.encoder, storage_dir=self.storage_dir),
            SolBenchmarkEvaluator(mode=EvaluationMode.SUBSTRATE_ABLATED, encoder=self.encoder, storage_dir=self.storage_dir),
        ]

        all_results: List[TrialResult] = []
        metrics_by_model: Dict[str, ModelAggregateMetrics] = {}

        for model in models:
            model_results: List[TrialResult] = []
            for trial in trials:
                res = model.execute_trial(trial)
                model_results.append(res)
                all_results.append(res)

            # Compute aggregated statistics
            valid_trials = [r for r in model_results if r.trial_type == TrialType.VALID_RECALL]
            conflict_trials = [r for r in model_results if r.trial_type in (TrialType.CONTRADICTION, TrialType.DISCONNECTED)]

            valid_acc = float(np.mean([1.0 if r.is_correct_recall else 0.0 for r in valid_trials])) if valid_trials else 0.0
            conflict_reject = float(np.mean([1.0 if r.rejected_conflict else 0.0 for r in conflict_trials])) if conflict_trials else 0.0
            false_commit = float(np.mean([1.0 if r.committed_false_claim else 0.0 for r in conflict_trials])) if conflict_trials else 0.0

            mean_margin = float(np.mean([r.read_disturb_margin for r in model_results]))
            mean_recovery = float(np.mean([r.recovery_time_steps for r in model_results]))
            mean_energy = float(np.mean([r.energy_dissipated for r in model_results]))
            mean_lat = float(np.mean([r.latency_ms for r in model_results]))
            mean_mem_kb = float(np.mean([r.memory_peak_bytes / 1024.0 for r in model_results]))

            metrics_by_model[model.model_name] = ModelAggregateMetrics(
                model_name=model.model_name,
                total_trials=len(model_results),
                valid_trials_count=len(valid_trials),
                conflict_trials_count=len(conflict_trials),
                recall_accuracy=round(valid_acc, 4),
                conflict_rejection_rate=round(conflict_reject, 4),
                false_commit_rate=round(false_commit, 4),
                mean_read_disturb_margin=round(mean_margin, 4),
                mean_recovery_time_steps=round(mean_recovery, 2),
                mean_energy_dissipated=round(mean_energy, 4),
                mean_latency_ms=round(mean_lat, 3),
                total_memory_kb=round(mean_mem_kb, 2)
            )

        suite_res = BenchmarkSuiteResults(
            suite_id=f"FLAGSHIP-BENCHMARK-S{input_seed}",
            total_trials=len(trials),
            model_metrics=metrics_by_model,
            trial_records=all_results,
            audit_counterexample=audit_dict
        )

        return suite_res
