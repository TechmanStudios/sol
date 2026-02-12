#!/usr/bin/env python3
"""
SOL Orchestrator — Multi-Agent Pipeline Runner

Chains the full SOL research pipeline into a single automated execution:

    smoke → cortex → consolidate → hippocampus → evolve → report

Each stage is optional and configurable.  The orchestrator tracks results,
enforces guardrails, and generates a final pipeline summary.

Usage:
    python orchestrator.py                    # Full pipeline
    python orchestrator.py --skip evolve      # Drop evolve stage
    python orchestrator.py --only cortex consolidate  # Subset
    python orchestrator.py --dry-run          # Plan only
    python orchestrator.py --resume <run-id>  # Resume from failure

Architecture:
    - Each stage is a thin wrapper around the existing tool's Python API.
    - No stage directly imports another stage — the orchestrator is the
      only integration point.
    - Core graph is NEVER modified.  SHA256 verified before and after.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent
_CORE_DIR = _SOL_ROOT / "tools" / "sol-core"
_CORTEX_DIR = _SOL_ROOT / "tools" / "sol-cortex"
_EVOLVE_DIR = _SOL_ROOT / "tools" / "sol-evolve"
_HIPPO_DIR = _SOL_ROOT / "tools" / "sol-hippocampus"
_DATA_DIR = _SOL_ROOT / "data"
_PIPELINE_DIR = _DATA_DIR / "pipeline_runs"

_DEFAULT_GRAPH = _CORE_DIR / "default_graph.json"

# Lazy sys.path injection (done per-stage to avoid import pollution)
_PATH_INJECTED: set[str] = set()


def _inject_path(directory: Path):
    d = str(directory)
    if d not in _PATH_INJECTED:
        if d not in sys.path:
            sys.path.insert(0, d)
        _PATH_INJECTED.add(d)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STAGES = ("smoke", "cortex", "consolidate", "hippocampus", "evolve", "report")

STAGE_DESCRIPTIONS = {
    "smoke":       "Engine smoke test — verify sol_engine loads and runs",
    "cortex":      "Autonomous scientist — scan gaps → hypothesize → execute",
    "consolidate": "Extract findings → generate candidate proof packets",
    "hippocampus": "Dream cycle — replay, consolidate memory, meta-learn",
    "evolve":      "A/B regression tests on evolve candidates (optional)",
    "report":      "Generate final pipeline summary",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    """Result of a single pipeline stage."""
    stage: str
    status: str = "pending"          # pending | running | passed | failed | skipped
    started_at: str = ""
    completed_at: str = ""
    elapsed_sec: float = 0.0
    output: dict = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineConfig:
    """Runtime configuration for a pipeline run."""
    # Stage selection
    stages: list[str] = field(default_factory=lambda: list(STAGES))
    skip: list[str] = field(default_factory=list)

    # Cortex options
    cortex_max_protocols: int = 3
    cortex_gap_type: str | None = None
    cortex_max_steps: int | None = None

    # Hippocampus options
    dream_sessions: int | None = None
    dream_dry_run: bool = False

    # Evolve options
    evolve_candidates: list[str] = field(default_factory=list)

    # General
    dry_run: bool = False
    verbose: bool = True

    @property
    def active_stages(self) -> list[str]:
        return [s for s in self.stages if s not in self.skip]


# ---------------------------------------------------------------------------
# Core immutability guard
# ---------------------------------------------------------------------------

def _graph_sha256() -> str:
    return hashlib.sha256(_DEFAULT_GRAPH.read_bytes()).hexdigest()


_EXPECTED_SHA = "b9800d5313886818c7c1980829e1ca5da7d63d9e2218e36c020df80db19b06fb"


def verify_core_immutability() -> bool:
    """True if default_graph.json is byte-identical to the frozen reference."""
    return _graph_sha256() == _EXPECTED_SHA


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------

def stage_smoke(cfg: PipelineConfig) -> dict:
    """Run the engine smoke test."""
    _inject_path(_CORE_DIR)
    from sol_engine import SOLEngine

    engine = SOLEngine.from_default_graph()
    engine.inject("grail", 50)
    for _ in range(10):
        engine.step(dt=0.12, c_press=0.1, damping=0.2)
    metrics = engine.compute_metrics()

    ok = (metrics["mass"] > 0 and metrics["entropy"] > 0 and
          metrics.get("maxRho", 0) > 0)

    result = {
        "engine_ok": ok,
        "nodes": len(engine.get_node_states()),
        "mass": round(metrics["mass"], 2),
        "entropy": round(metrics["entropy"], 4),
        "maxRho": round(metrics.get("maxRho", 0), 2),
        "core_sha256": _graph_sha256(),
    }
    if not ok:
        raise RuntimeError(f"Engine smoke test FAILED: {result}")
    return result


def stage_cortex(cfg: PipelineConfig) -> dict:
    """Run a cortex autonomous-scientist session."""
    _inject_path(_CORTEX_DIR)
    _inject_path(_CORE_DIR)

    from run_loop import CortexSession, SessionConfig

    config = SessionConfig(
        max_protocols=cfg.cortex_max_protocols,
        gap_type_filter=cfg.cortex_gap_type,
        dry_run=cfg.dry_run,
        verbose=cfg.verbose,
    )
    if cfg.cortex_max_steps:
        config.max_total_steps = cfg.cortex_max_steps

    session = CortexSession(config)
    summary = session.run()

    return {
        "session_id": summary["session_id"],
        "session_dir": str(session.session_dir),
        "protocols_run": summary["protocols_run"],
        "total_steps": summary["total_steps"],
        "hypotheses": summary["hypotheses_generated"],
        "gaps_addressed": summary["gaps_addressed"],
        "sanity_results": summary["sanity_results"],
        "dry_run": summary.get("dry_run", False),
    }


def stage_consolidate(cfg: PipelineConfig, cortex_result: dict) -> dict:
    """Consolidate the cortex session into proof packets."""
    _inject_path(_CORTEX_DIR)
    _inject_path(_CORE_DIR)

    session_dir = cortex_result.get("session_dir")
    if not session_dir:
        return {"status": "skipped", "reason": "no cortex session to consolidate"}

    if cortex_result.get("dry_run"):
        return {"status": "skipped", "reason": "cortex was a dry run — nothing to consolidate"}

    from consolidate import consolidate_session

    result = consolidate_session(Path(session_dir))
    return result


def stage_hippocampus(cfg: PipelineConfig) -> dict:
    """Run a dream cycle + compact memory."""
    _inject_path(_HIPPO_DIR)
    _inject_path(_CORE_DIR)

    from dream_cycle import DreamCycle
    from memory_store import compact, memory_stats

    dc = DreamCycle(
        max_sessions=cfg.dream_sessions,
        dry_run=cfg.dream_dry_run or cfg.dry_run,
    )
    dream_summary = dc.run()

    # Compact after dreaming
    if not (cfg.dream_dry_run or cfg.dry_run):
        compact()

    stats = memory_stats()

    return {
        "dream_session_id": dream_summary.get("session_id"),
        "sessions_replayed": dream_summary.get("sessions_replayed", 0),
        "replays_run": dream_summary.get("replays_run", 0),
        "basins_discovered": dream_summary.get("basins_discovered", 0),
        "basins_reinforced": dream_summary.get("basins_reinforced", 0),
        "basins_decayed": dream_summary.get("basins_decayed", 0),
        "memory_nodes": stats.get("node_count", 0),
        "memory_edges": stats.get("edge_count", 0),
        "dry_run": dream_summary.get("dry_run", False),
    }


def stage_evolve(cfg: PipelineConfig) -> dict:
    """Run A/B regression tests on specified candidates."""
    _inject_path(_EVOLVE_DIR)
    _inject_path(_CORE_DIR)

    if not cfg.evolve_candidates:
        return {"status": "skipped", "reason": "no evolve candidates specified"}

    from ab_test import ABTest

    all_reports: list[dict] = []
    for cand_name in cfg.evolve_candidates:
        try:
            test = ABTest(cand_name)
            report = test.run()
            all_reports.append({
                "candidate": cand_name,
                "verdict": report["overall_verdict"],
                "protocols_tested": len(report.get("protocols", {})),
                "elapsed_sec": report.get("elapsed_sec", 0),
            })
        except Exception as e:
            all_reports.append({
                "candidate": cand_name,
                "verdict": "ERROR",
                "error": str(e),
            })

    return {
        "candidates_tested": len(all_reports),
        "reports": all_reports,
        "any_regress": any(r["verdict"] == "REGRESS" for r in all_reports),
    }


def stage_report(cfg: PipelineConfig, all_results: dict[str, StageResult],
                 run_id: str) -> dict:
    """Generate a final pipeline summary."""
    stages_passed = sum(1 for r in all_results.values() if r.status == "passed")
    stages_failed = sum(1 for r in all_results.values() if r.status == "failed")
    stages_skipped = sum(1 for r in all_results.values() if r.status == "skipped")
    total_elapsed = sum(r.elapsed_sec for r in all_results.values())

    # Core immutability final check
    core_ok = verify_core_immutability()

    summary = {
        "run_id": run_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "stages_passed": stages_passed,
        "stages_failed": stages_failed,
        "stages_skipped": stages_skipped,
        "total_elapsed_sec": round(total_elapsed, 2),
        "core_immutability": "PASS" if core_ok else "FAIL",
        "pipeline_verdict": "PASS" if stages_failed == 0 and core_ok else "FAIL",
        "stages": {name: r.to_dict() for name, r in all_results.items()},
    }

    return summary


# ---------------------------------------------------------------------------
# Pipeline Runner
# ---------------------------------------------------------------------------

class PipelineRunner:
    """
    Orchestrates the full SOL research pipeline.

    Stages execute sequentially: smoke → cortex → consolidate →
    hippocampus → evolve → report.

    Each stage is isolated — failures don't cascade unless the stage
    is marked critical (smoke is critical; evolve is optional).
    """

    CRITICAL_STAGES = {"smoke"}  # Pipeline aborts if these fail

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self.run_id = datetime.now(timezone.utc).strftime("PL-%Y%m%d-%H%M%S")
        self.run_dir = _PIPELINE_DIR / self.run_id
        self.results: dict[str, StageResult] = {}

    def run(self) -> dict:
        """Execute the full pipeline. Returns the final summary."""
        active = self.config.active_stages
        self._print_header(active)

        # Pre-flight: core immutability
        if not verify_core_immutability():
            raise RuntimeError(
                "ABORT: Core graph SHA256 mismatch before pipeline start! "
                "The sacred graph has been corrupted."
            )

        cortex_result: dict = {}

        for stage_name in active:
            if stage_name == "report":
                continue  # Report is always last

            result = StageResult(stage=stage_name)
            self.results[stage_name] = result

            self._print_stage_start(stage_name)
            result.status = "running"
            result.started_at = datetime.now(timezone.utc).isoformat()
            t0 = time.time()

            try:
                if stage_name == "smoke":
                    result.output = stage_smoke(self.config)

                elif stage_name == "cortex":
                    result.output = stage_cortex(self.config)
                    cortex_result = result.output

                elif stage_name == "consolidate":
                    if not cortex_result:
                        result.output = {"status": "skipped",
                                         "reason": "no cortex result to consolidate"}
                        result.status = "skipped"
                    else:
                        result.output = stage_consolidate(self.config, cortex_result)

                elif stage_name == "hippocampus":
                    result.output = stage_hippocampus(self.config)

                elif stage_name == "evolve":
                    result.output = stage_evolve(self.config)
                    if result.output.get("status") == "skipped":
                        result.status = "skipped"

                if result.status == "running":
                    result.status = "passed"

            except Exception as e:
                result.status = "failed"
                result.error = f"{type(e).__name__}: {e}"
                if self.config.verbose:
                    traceback.print_exc()

                if stage_name in self.CRITICAL_STAGES:
                    self._print_abort(stage_name, result.error)
                    break

            result.elapsed_sec = round(time.time() - t0, 2)
            result.completed_at = datetime.now(timezone.utc).isoformat()
            self._print_stage_result(stage_name, result)

            # Post-stage: verify core immutability
            if not verify_core_immutability():
                result.status = "failed"
                result.error = "Core graph was MODIFIED by this stage — FORBIDDEN"
                self._print_abort(stage_name, result.error)
                break

        # Final report
        report_result = StageResult(stage="report")
        report_result.started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.time()
        report_result.output = stage_report(
            self.config, self.results, self.run_id)
        report_result.status = "passed"
        report_result.elapsed_sec = round(time.time() - t0, 2)
        report_result.completed_at = datetime.now(timezone.utc).isoformat()
        self.results["report"] = report_result

        # Save pipeline run to disk
        self._save_run(report_result.output)
        self._print_footer(report_result.output)

        return report_result.output

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_run(self, summary: dict):
        """Save pipeline run data."""
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Full summary
        summary_path = self.run_dir / "pipeline_summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, default=str), encoding="utf-8")

        # Individual stage results
        for name, result in self.results.items():
            stage_path = self.run_dir / f"stage_{name}.json"
            stage_path.write_text(
                json.dumps(result.to_dict(), indent=2, default=str),
                encoding="utf-8")

    # ------------------------------------------------------------------
    # Console output
    # ------------------------------------------------------------------

    def _print_header(self, active: list[str]):
        if not self.config.verbose:
            return
        print(f"\n{'='*70}")
        print(f"  SOL Pipeline — {self.run_id}")
        print(f"  Stages: {' -> '.join(active)}")
        if self.config.dry_run:
            print(f"  Mode: DRY RUN")
        print(f"{'='*70}")

    def _print_stage_start(self, stage: str):
        if not self.config.verbose:
            return
        desc = STAGE_DESCRIPTIONS.get(stage, "")
        print(f"\n{'-'*70}")
        print(f"  [{stage.upper()}] {desc}")
        print(f"{'-'*70}")

    def _print_stage_result(self, stage: str, result: StageResult):
        if not self.config.verbose:
            return
        icon = {"passed": "+", "failed": "!", "skipped": "-"}.get(result.status, "?")
        print(f"  [{icon}] {stage}: {result.status.upper()} ({result.elapsed_sec}s)")
        if result.error:
            print(f"      Error: {result.error}")

    def _print_abort(self, stage: str, error: str):
        if not self.config.verbose:
            return
        print(f"\n  !! PIPELINE ABORT — critical stage '{stage}' failed")
        print(f"  !! {error}")

    def _print_footer(self, summary: dict):
        if not self.config.verbose:
            return
        verdict = summary["pipeline_verdict"]
        icon = "+" if verdict == "PASS" else "!"
        print(f"\n{'='*70}")
        print(f"  [{icon}] Pipeline Verdict: {verdict}")
        print(f"  Passed: {summary['stages_passed']}  "
              f"Failed: {summary['stages_failed']}  "
              f"Skipped: {summary['stages_skipped']}")
        print(f"  Total time: {summary['total_elapsed_sec']}s")
        print(f"  Core immutability: {summary['core_immutability']}")
        print(f"  Output: {self.run_dir.relative_to(_SOL_ROOT)}")
        print(f"{'='*70}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SOL Orchestrator — Multi-Agent Pipeline Runner",
        epilog=(
            "Stages (in order): " + " -> ".join(STAGES) + "\n\n"
            "Examples:\n"
            "  python orchestrator.py                        # Full pipeline\n"
            "  python orchestrator.py --skip evolve          # Skip evolve\n"
            "  python orchestrator.py --only cortex consolidate  # Subset\n"
            "  python orchestrator.py --dry-run              # Plan only\n"
            "  python orchestrator.py --evolve-candidates tune_conductance_gamma_up\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Stage selection
    parser.add_argument("--skip", nargs="+", choices=list(STAGES),
                        default=[], help="Stages to skip")
    parser.add_argument("--only", nargs="+", choices=list(STAGES),
                        default=[], help="Run only these stages (+ smoke + report)")

    # Cortex options
    parser.add_argument("--cortex-protocols", type=int, default=3,
                        help="Max protocols per cortex session (default: 3)")
    parser.add_argument("--cortex-gap-type", type=str, default=None,
                        help="Only pursue this gap type in cortex")
    parser.add_argument("--cortex-max-steps", type=int, default=None,
                        help="Total step budget for cortex")

    # Hippocampus options
    parser.add_argument("--dream-sessions", type=int, default=None,
                        help="Max sessions to replay in dream cycle")
    parser.add_argument("--dream-dry-run", action="store_true",
                        help="Dream cycle dry-run (show what would replay)")

    # Evolve options
    parser.add_argument("--evolve-candidates", nargs="+", default=[],
                        help="Evolve candidate names to A/B test")

    # General
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry run across all stages")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose output")
    parser.add_argument("--json", action="store_true",
                        help="Output final summary as JSON")

    args = parser.parse_args()

    # Build config
    if args.only:
        # Always include smoke (first) and report (last)
        stages = ["smoke"] + [s for s in args.only if s != "smoke"] + ["report"]
        # Deduplicate preserving order
        seen: set[str] = set()
        stages = [s for s in stages if not (s in seen or seen.add(s))]
    else:
        stages = list(STAGES)

    config = PipelineConfig(
        stages=stages,
        skip=args.skip,
        cortex_max_protocols=args.cortex_protocols,
        cortex_gap_type=args.cortex_gap_type,
        cortex_max_steps=args.cortex_max_steps,
        dream_sessions=args.dream_sessions,
        dream_dry_run=args.dream_dry_run,
        evolve_candidates=args.evolve_candidates,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )

    runner = PipelineRunner(config)
    summary = runner.run()

    if args.json:
        print(json.dumps(summary, indent=2, default=str))

    verdict = summary.get("pipeline_verdict", "UNKNOWN")
    sys.exit(0 if verdict == "PASS" else 1)


# ---------------------------------------------------------------------------
# Public API — used by sol-rsi execute_plan()
# ---------------------------------------------------------------------------

def run_pipeline(config: PipelineConfig | None = None) -> dict:
    """Convenience function to run a full pipeline and return the summary.

    This is the entry point used by the RSI engine's execution bridge
    (``from orchestrator import PipelineConfig, run_pipeline``).
    """
    runner = PipelineRunner(config)
    return runner.run()


if __name__ == "__main__":
    main()
