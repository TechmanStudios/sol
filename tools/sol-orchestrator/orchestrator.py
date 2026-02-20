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
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from delegation_v1 import (
    AdaptiveTriggerEngine,
    TrustLedger,
    build_stage_contract,
    evaluate_self_reconfigure_acceptance,
    evaluate_self_reconfigure_proposals,
    load_adaptive_policy,
    resolve_cortex_adaptive_plan,
    resolve_stage_adaptive_plan,
)

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
_DELEGATION_LEDGER = _PIPELINE_DIR / "_delegation_trust_ledger.json"
_SELF_RECONFIG_APPROVAL_LEDGER = _PIPELINE_DIR / "_self_reconfigure_approvals.json"
_ADAPTIVE_POLICY_PATH = _THIS_DIR / "delegation_policy.json"

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


def stage_report(
    cfg: PipelineConfig,
    all_results: dict[str, StageResult],
    run_id: str,
    delegation_summary: dict[str, Any] | None = None,
) -> dict:
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
        "delegation_v1": delegation_summary or {"enabled": False},
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
        self.trigger_engine = AdaptiveTriggerEngine()
        self.adaptive_policy = load_adaptive_policy(_ADAPTIVE_POLICY_PATH)
        self.trust_ledger = TrustLedger(
            _DELEGATION_LEDGER,
            dynamics=self.adaptive_policy.get("trust_dynamics", {}),
        )
        self.delegation_events: list[dict[str, Any]] = []

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
            contract = build_stage_contract(stage_name, self.run_id)
            self.delegation_events.append(
                {
                    "event": "contract_issued",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "stage": stage_name,
                    "contract": contract.to_dict(),
                }
            )

            self._print_stage_start(stage_name)
            result.status = "running"
            result.started_at = datetime.now(timezone.utc).isoformat()
            t0 = time.time()

            try:
                if stage_name == "smoke":
                    result.output = stage_smoke(self.config)

                elif stage_name == "cortex":
                    result.output = stage_cortex(self.config)

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

            result.output = result.output or {}
            result.output["delegation_contract"] = contract.to_dict()

            triggers = self.trigger_engine.evaluate(
                stage=stage_name,
                status=result.status,
                output=result.output,
                elapsed_sec=result.elapsed_sec,
                contract=contract,
            )

            if stage_name == "cortex":
                result, triggers = self._apply_cortex_adaptation(
                    result=result,
                    triggers=triggers,
                    contract=contract,
                )
            elif stage_name in {"consolidate", "hippocampus", "evolve"}:
                result, triggers = self._apply_non_cortex_adaptation(
                    stage_name=stage_name,
                    result=result,
                    triggers=triggers,
                    contract=contract,
                    cortex_result=cortex_result,
                )

            if triggers:
                result.output["delegation_triggers"] = triggers
                self.delegation_events.append(
                    {
                        "event": "triggers_detected",
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "stage": stage_name,
                        "triggers": triggers,
                    }
                )

            self.trust_ledger.record(
                stage=stage_name,
                status=result.status,
                elapsed_sec=result.elapsed_sec,
                trigger_types=[t["type"] for t in triggers],
                run_id=self.run_id,
            )

            if stage_name == "cortex" and result.status in {"passed", "skipped"}:
                cortex_result = result.output

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

        trigger_counts: dict[str, int] = {}
        stages_with_triggers = 0
        for stage_result in self.results.values():
            stage_triggers = stage_result.output.get("delegation_triggers", [])
            if stage_triggers:
                stages_with_triggers += 1
            for trigger in stage_triggers:
                trigger_type = trigger.get("type", "unknown")
                trigger_counts[trigger_type] = trigger_counts.get(trigger_type, 0) + 1

        trust_snapshot = self.trust_ledger.snapshot()
        approval_ledger = self._load_self_reconfigure_approval_ledger()
        self_reconfigure = evaluate_self_reconfigure_proposals(
            policy=self.adaptive_policy,
            trust_snapshot=trust_snapshot,
            run_audit=approval_ledger.get("run_audit", []),
        )
        autonomous_approval = self._resolve_self_reconfigure_autonomous_approval(
            proposals=self_reconfigure.get("proposals", []),
            approval_ledger=approval_ledger,
        )
        if autonomous_approval.get("new_approved_proposal_ids"):
            existing_ids = approval_ledger.get("approved_proposal_ids", [])
            if not isinstance(existing_ids, list):
                existing_ids = []
            merged = set(str(item) for item in existing_ids if str(item))
            merged.update(autonomous_approval.get("new_approved_proposal_ids", []))
            approval_ledger["approved_proposal_ids"] = sorted(merged)
            self.delegation_events.append(
                {
                    "event": "self_reconfigure_auto_approval",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "details": autonomous_approval,
                }
            )

        approval_ledger_ids = approval_ledger.get("approved_proposal_ids", [])
        self_reconfigure_acceptance = evaluate_self_reconfigure_acceptance(
            policy=self.adaptive_policy,
            self_reconfigure=self_reconfigure,
            approval_ledger_ids=approval_ledger_ids,
        )
        self_reconfigure_acceptance["autonomous_approval"] = autonomous_approval
        approval_ledger = self._record_self_reconfigure_approval_audit(
            ledger=approval_ledger,
            proposals=self_reconfigure.get("proposals", []),
            acceptance=self_reconfigure_acceptance,
            autonomous_approved_ids=autonomous_approval.get("new_approved_proposal_ids", []),
            trust_snapshot=trust_snapshot,
        )
        approval_ledger, pruning_summary = self._prune_self_reconfigure_approval_ledger(
            ledger=approval_ledger,
        )
        approval_ledger, feedback_summary = self._evaluate_self_reconfigure_feedback(
            ledger=approval_ledger,
            trust_snapshot=trust_snapshot,
        )
        # Record revoked IDs in the current run's audit entry for cooldown tracking
        feedback_revoked_id_list: list[str] = []
        if feedback_summary.get("revoked"):
            feedback_revoked_id_list = sorted(feedback_summary["revoked"].keys())
            run_audit = approval_ledger.get("run_audit", [])
            if isinstance(run_audit, list) and run_audit:
                last_entry = run_audit[-1]
                if isinstance(last_entry, dict):
                    last_entry["feedback_revoked_ids"] = feedback_revoked_id_list
        # Phase 4.9: Escalation awareness — permanently block repeatedly-revoked IDs
        approval_ledger, escalation_summary = self._evaluate_self_reconfigure_escalation(
            ledger=approval_ledger,
            feedback_revoked_ids=feedback_revoked_id_list,
        )
        approval_ledger, utility_summary = self._evaluate_self_reconfigure_utility_learning(
            ledger=approval_ledger,
            trust_snapshot=trust_snapshot,
        )
        self._save_self_reconfigure_approval_ledger(approval_ledger)
        self_reconfigure_acceptance["approval_ledger"] = {
            "path": str(_SELF_RECONFIG_APPROVAL_LEDGER),
            "approved_id_count": len(approval_ledger.get("approved_proposal_ids", [])),
            "permanently_blocked_count": len(approval_ledger.get("permanently_blocked_ids", [])),
            "audit_entries": len(approval_ledger.get("run_audit", [])),
            "pruning": pruning_summary,
            "feedback": feedback_summary,
            "escalation": escalation_summary,
            "utility_learning": utility_summary,
        }
        self_reconfigure["acceptance"] = self_reconfigure_acceptance

        if self_reconfigure.get("proposals"):
            self.delegation_events.append(
                {
                    "event": "self_reconfigure_proposals",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "details": self_reconfigure,
                }
            )
        if self_reconfigure_acceptance.get("accepted_proposals"):
            self.delegation_events.append(
                {
                    "event": "self_reconfigure_acceptance",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "details": self_reconfigure_acceptance,
                }
            )
        if pruning_summary.get("removed"):
            self.delegation_events.append(
                {
                    "event": "self_reconfigure_pruning",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "details": pruning_summary,
                }
            )
        if feedback_summary.get("revoked"):
            self.delegation_events.append(
                {
                    "event": "self_reconfigure_feedback_revocation",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "details": feedback_summary,
                }
            )
        if escalation_summary.get("newly_blocked"):
            self.delegation_events.append(
                {
                    "event": "self_reconfigure_escalation",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "details": escalation_summary,
                }
            )
        if utility_summary.get("enabled"):
            observed_outcomes = utility_summary.get("observed_outcomes", {})
            blocked_expected = autonomous_approval.get("blocked_expected_utility", {})
            self.delegation_events.append(
                {
                    "event": "self_reconfigure_utility_learning",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "details": {
                        "expected_utilities": utility_summary.get("expected_utilities", {}),
                        "observed_outcomes": observed_outcomes,
                        "blocked_expected_utility": blocked_expected,
                    },
                }
            )

        delegation_summary = {
            "enabled": True,
            "contracts_issued": len([e for e in self.delegation_events if e.get("event") == "contract_issued"]),
            "adaptive_actions": len([e for e in self.delegation_events if e.get("event") == "adaptive_action"]),
            "adaptive_policy_version": self.adaptive_policy.get("version", "unknown"),
            "adaptive_policy_enabled": self.adaptive_policy.get("enabled", True),
            "stages_with_triggers": stages_with_triggers,
            "trigger_counts": trigger_counts,
            "trust_snapshot": trust_snapshot,
            "self_reconfigure": self_reconfigure,
        }

        report_result.output = stage_report(
            self.config,
            self.results,
            self.run_id,
            delegation_summary=delegation_summary,
        )
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

    def _load_self_reconfigure_approval_ledger(self) -> dict[str, Any]:
        default = {
            "version": 1,
            "updated": datetime.now(timezone.utc).isoformat(),
            "approved_proposal_ids": [],
            "permanently_blocked_ids": [],
            "proposal_outcomes": {},
            "run_audit": [],
        }
        if not _SELF_RECONFIG_APPROVAL_LEDGER.exists():
            return default
        try:
            payload = json.loads(_SELF_RECONFIG_APPROVAL_LEDGER.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

        if not isinstance(payload, dict):
            return default

        approved = payload.get("approved_proposal_ids", [])
        if not isinstance(approved, list):
            approved = []
        blocked = payload.get("permanently_blocked_ids", [])
        if not isinstance(blocked, list):
            blocked = []
        outcomes = payload.get("proposal_outcomes", {})
        if not isinstance(outcomes, dict):
            outcomes = {}
        run_audit = payload.get("run_audit", [])
        if not isinstance(run_audit, list):
            run_audit = []

        return {
            "version": int(payload.get("version", 1) or 1),
            "updated": str(payload.get("updated", default["updated"])),
            "approved_proposal_ids": [str(item) for item in approved if str(item)],
            "permanently_blocked_ids": [str(item) for item in blocked if str(item)],
            "proposal_outcomes": {
                str(k): v for k, v in outcomes.items()
                if str(k) and isinstance(v, dict)
            },
            "run_audit": run_audit,
        }

    def _record_self_reconfigure_approval_audit(
        self,
        ledger: dict[str, Any],
        proposals: list[dict[str, Any]],
        acceptance: dict[str, Any],
        autonomous_approved_ids: list[str] | None = None,
        trust_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        proposal_ids = [
            str(p.get("proposal_id", ""))
            for p in proposals
            if isinstance(p, dict) and str(p.get("proposal_id", ""))
        ]
        accepted = acceptance.get("accepted_proposals", []) if isinstance(acceptance, dict) else []
        accepted_ids = [
            str(p.get("proposal_id", ""))
            for p in accepted
            if isinstance(p, dict) and str(p.get("proposal_id", ""))
        ]

        # Build compact trust snapshot per stage for feedback evaluation
        trust_stages: dict[str, float] = {}
        if isinstance(trust_snapshot, dict):
            agents = trust_snapshot.get("agents", {})
            if isinstance(agents, dict):
                for key, stats in agents.items():
                    if key.startswith("stage:") and isinstance(stats, dict):
                        stage = key[len("stage:"):]
                        try:
                            trust_stages[stage] = round(float(stats.get("trust_score", 0.5)), 3)
                        except (TypeError, ValueError):
                            trust_stages[stage] = 0.5

        run_audit = ledger.get("run_audit", []) if isinstance(ledger, dict) else []
        if not isinstance(run_audit, list):
            run_audit = []
        audit_entry: dict[str, Any] = {
            "run_id": self.run_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "proposal_ids": proposal_ids,
            "accepted_proposal_ids": accepted_ids,
            "autonomous_approved_proposal_ids": [
                str(item) for item in (autonomous_approved_ids or []) if str(item)
            ],
            "pending_proposals": int(acceptance.get("pending_proposals", 0) or 0),
        }
        if trust_stages:
            audit_entry["trust_stages"] = trust_stages
        run_audit.append(audit_entry)
        if len(run_audit) > 500:
            run_audit = run_audit[-500:]

        approved_ids = ledger.get("approved_proposal_ids", []) if isinstance(ledger, dict) else []
        if not isinstance(approved_ids, list):
            approved_ids = []
        blocked_ids = ledger.get("permanently_blocked_ids", []) if isinstance(ledger, dict) else []
        if not isinstance(blocked_ids, list):
            blocked_ids = []
        proposal_outcomes = ledger.get("proposal_outcomes", {}) if isinstance(ledger, dict) else {}
        if not isinstance(proposal_outcomes, dict):
            proposal_outcomes = {}

        return {
            "version": int(ledger.get("version", 1) or 1) if isinstance(ledger, dict) else 1,
            "updated": datetime.now(timezone.utc).isoformat(),
            "approved_proposal_ids": [str(item) for item in approved_ids if str(item)],
            "permanently_blocked_ids": [str(item) for item in blocked_ids if str(item)],
            "proposal_outcomes": {
                str(k): v for k, v in proposal_outcomes.items()
                if str(k) and isinstance(v, dict)
            },
            "run_audit": run_audit,
        }

    def _save_self_reconfigure_approval_ledger(self, ledger: dict[str, Any]):
        _SELF_RECONFIG_APPROVAL_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        _SELF_RECONFIG_APPROVAL_LEDGER.write_text(
            json.dumps(ledger, indent=2, default=str),
            encoding="utf-8",
        )

    def _resolve_self_reconfigure_autonomous_approval(
        self,
        proposals: list[dict[str, Any]],
        approval_ledger: dict[str, Any],
    ) -> dict[str, Any]:
        acceptance_cfg = self.adaptive_policy.get("self_reconfigure", {}).get("acceptance", {})
        auto_cfg = acceptance_cfg.get("autonomous_approval", {}) if isinstance(acceptance_cfg, dict) else {}
        enabled = isinstance(auto_cfg, dict) and bool(auto_cfg.get("enabled", False))

        if not enabled:
            return {
                "enabled": False,
                "considered": 0,
                "new_approved_proposal_ids": [],
            }

        lookback_raw = auto_cfg.get("lookback_runs", 40)
        lookback_runs = int(40 if lookback_raw is None else lookback_raw)
        if lookback_runs < 0:
            lookback_runs = 0
        min_repeated_raw = auto_cfg.get("min_repeated_proposals", 3)
        min_repeated_proposals = int(3 if min_repeated_raw is None else min_repeated_raw)
        if min_repeated_proposals < 1:
            min_repeated_proposals = 1
        max_new_raw = auto_cfg.get("max_new_approvals_per_run", 1)
        max_new_approvals_per_run = int(1 if max_new_raw is None else max_new_raw)
        if max_new_approvals_per_run < 0:
            max_new_approvals_per_run = 0
        min_trust_score_raw = auto_cfg.get("min_trust_score", 0.9)
        min_trust_score = float(0.9 if min_trust_score_raw is None else min_trust_score_raw)
        min_trust_confidence_raw = auto_cfg.get("min_trust_confidence_ema", 0.85)
        min_trust_confidence_ema = float(0.85 if min_trust_confidence_raw is None else min_trust_confidence_raw)

        allow_modes_raw = auto_cfg.get("allow_modes", ["relax"])
        allow_modes: set[str] = set()
        if isinstance(allow_modes_raw, list):
            allow_modes = {str(item) for item in allow_modes_raw if str(item)}
        if not allow_modes:
            allow_modes = {"relax"}

        utility_cfg = auto_cfg.get("utility_learning", {}) if isinstance(auto_cfg, dict) else {}
        utility_enabled = isinstance(utility_cfg, dict) and bool(utility_cfg.get("enabled", False))
        utility_min_obs_raw = utility_cfg.get("min_observations_for_gating", 2) if isinstance(utility_cfg, dict) else 2
        utility_min_observations_for_gating = int(2 if utility_min_obs_raw is None else utility_min_obs_raw)
        if utility_min_observations_for_gating < 1:
            utility_min_observations_for_gating = 1
        utility_min_expected_raw = utility_cfg.get("min_expected_utility", -0.02) if isinstance(utility_cfg, dict) else -0.02
        utility_min_expected_utility = float(-0.02 if utility_min_expected_raw is None else utility_min_expected_raw)

        # Phase 5.4: bounded low-confidence exploration policy
        exploration_cfg = utility_cfg.get("exploration", {}) if isinstance(utility_cfg, dict) else {}
        exploration_enabled = isinstance(exploration_cfg, dict) and bool(exploration_cfg.get("enabled", False))
        exploration_max_raw = exploration_cfg.get("max_explorations_per_run", 1) if isinstance(exploration_cfg, dict) else 1
        exploration_max_per_run = int(1 if exploration_max_raw is None else exploration_max_raw)
        if exploration_max_per_run < 0:
            exploration_max_per_run = 0
        exploration_max_conf_raw = exploration_cfg.get("max_expected_utility_confidence", 0.5) if isinstance(exploration_cfg, dict) else 0.5
        exploration_max_expected_confidence = float(0.5 if exploration_max_conf_raw is None else exploration_max_conf_raw)
        exploration_max_expected_confidence = max(0.0, min(1.0, exploration_max_expected_confidence))
        exploration_min_trust_raw = exploration_cfg.get("min_trust_score", min_trust_score) if isinstance(exploration_cfg, dict) else min_trust_score
        exploration_min_trust_score = float(min_trust_score if exploration_min_trust_raw is None else exploration_min_trust_raw)
        exploration_min_conf_raw = exploration_cfg.get("min_trust_confidence_ema", min_trust_confidence_ema) if isinstance(exploration_cfg, dict) else min_trust_confidence_ema
        exploration_min_trust_confidence_ema = float(min_trust_confidence_ema if exploration_min_conf_raw is None else exploration_min_conf_raw)
        exploration_allow_modes_raw = exploration_cfg.get("allow_modes", ["relax"]) if isinstance(exploration_cfg, dict) else ["relax"]
        exploration_allow_modes: set[str] = set()
        if isinstance(exploration_allow_modes_raw, list):
            exploration_allow_modes = {str(item) for item in exploration_allow_modes_raw if str(item)}
        if not exploration_allow_modes:
            exploration_allow_modes = {"relax"}

        approved_existing_raw = approval_ledger.get("approved_proposal_ids", []) if isinstance(approval_ledger, dict) else []
        approved_existing = {str(item) for item in approved_existing_raw if str(item)}

        outcomes_raw = approval_ledger.get("proposal_outcomes", {}) if isinstance(approval_ledger, dict) else {}
        proposal_outcomes: dict[str, dict[str, Any]] = {}
        if isinstance(outcomes_raw, dict):
            proposal_outcomes = {
                str(pid): stats
                for pid, stats in outcomes_raw.items()
                if str(pid) and isinstance(stats, dict)
            }

        run_audit = approval_ledger.get("run_audit", []) if isinstance(approval_ledger, dict) else []
        if not isinstance(run_audit, list):
            run_audit = []
        history = run_audit[-lookback_runs:] if lookback_runs > 0 else []
        proposal_counts: dict[str, int] = {}
        for row in history:
            if not isinstance(row, dict):
                continue
            row_ids = row.get("proposal_ids", [])
            if not isinstance(row_ids, list):
                continue
            for proposal_id in row_ids:
                pid = str(proposal_id)
                if not pid:
                    continue
                proposal_counts[pid] = proposal_counts.get(pid, 0) + 1

        # Phase 4.8: Build cooldown set from recent feedback revocations
        fb_cfg = auto_cfg.get("feedback", {}) if isinstance(auto_cfg, dict) else {}
        cooldown_raw = fb_cfg.get("cooldown_runs_after_revocation", 20) if isinstance(fb_cfg, dict) else 20
        cooldown_runs = int(20 if cooldown_raw is None else cooldown_raw)
        if cooldown_runs < 0:
            cooldown_runs = 0
        cooldown_ids: set[str] = set()
        # Phase 5.0d: Track runs remaining until cooldown expires per ID
        cooldown_details: dict[str, dict[str, Any]] = {}
        if cooldown_runs > 0:
            cooldown_window = run_audit[-cooldown_runs:] if cooldown_runs > 0 else []
            for cw_idx, row in enumerate(cooldown_window):
                if not isinstance(row, dict):
                    continue
                revoked_ids = row.get("feedback_revoked_ids", [])
                if isinstance(revoked_ids, list):
                    for rid in revoked_ids:
                        srid = str(rid)
                        if srid:
                            cooldown_ids.add(srid)
                            # Runs remaining = cooldown_runs - (distance from end of window)
                            runs_since = len(cooldown_window) - cw_idx - 1
                            remaining = cooldown_runs - runs_since
                            # Keep the most recent (highest remaining) if revoked multiple times
                            prev = cooldown_details.get(srid, {})
                            if remaining > prev.get("runs_remaining", 0):
                                cooldown_details[srid] = {
                                    "runs_remaining": remaining,
                                    "revoked_at_audit_index": len(run_audit) - len(cooldown_window) + cw_idx,
                                }

        # Phase 4.9: Load permanently blocked IDs from ledger
        blocked_raw = approval_ledger.get("permanently_blocked_ids", []) if isinstance(approval_ledger, dict) else []
        permanently_blocked: set[str] = set()
        if isinstance(blocked_raw, list):
            permanently_blocked = {str(item) for item in blocked_raw if str(item)}

        new_approved: list[str] = []
        exploratory_approved: dict[str, dict[str, Any]] = {}
        exploration_used = 0
        considered = 0
        skipped: dict[str, str] = {}
        blocked_expected_utility: dict[str, dict[str, Any]] = {}
        for proposal in proposals:
            if len(new_approved) >= max_new_approvals_per_run:
                break
            if not isinstance(proposal, dict):
                continue
            considered += 1

            proposal_id = str(proposal.get("proposal_id", "") or "")
            if not proposal_id:
                continue

            if proposal_id in permanently_blocked:
                skipped[proposal_id] = "permanently_blocked"
                continue

            if proposal_id in approved_existing or proposal_id in new_approved:
                skipped[proposal_id] = "already_approved"
                continue

            if proposal_id in cooldown_ids:
                skipped[proposal_id] = "revocation_cooldown"
                continue

            mode = str(proposal.get("mode", "") or "")
            if mode not in allow_modes:
                skipped[proposal_id] = "mode_not_allowed"
                continue

            metrics = proposal.get("metrics", {}) if isinstance(proposal.get("metrics", {}), dict) else {}
            trust_score = float(metrics.get("trust_score", 0.0) or 0.0)
            trust_confidence_ema = float(metrics.get("trust_confidence_ema", 0.0) or 0.0)
            if trust_score < min_trust_score:
                skipped[proposal_id] = "trust_score_below_threshold"
                continue
            if trust_confidence_ema < min_trust_confidence_ema:
                skipped[proposal_id] = "confidence_below_threshold"
                continue

            repeated = proposal_counts.get(proposal_id, 0) + 1

            expected_utility: float | None = None
            utility_observations = 0
            utility_confidence = 0.0
            outcome_stats = proposal_outcomes.get(proposal_id, {})
            if isinstance(outcome_stats, dict):
                try:
                    utility_observations = int(outcome_stats.get("observations", 0) or 0)
                except (TypeError, ValueError):
                    utility_observations = 0
                if utility_observations < 0:
                    utility_observations = 0
                if utility_observations > 0:
                    try:
                        expected_utility = float(outcome_stats.get("avg_utility", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        expected_utility = 0.0
                utility_confidence = min(
                    1.0,
                    utility_observations / float(max(1, utility_min_observations_for_gating)),
                )

            # Phase 5.4: bounded exploration path for low-confidence utility
            can_explore = (
                exploration_enabled
                and exploration_used < exploration_max_per_run
                and mode in exploration_allow_modes
                and trust_score >= exploration_min_trust_score
                and trust_confidence_ema >= exploration_min_trust_confidence_ema
                and utility_confidence <= exploration_max_expected_confidence
            )

            exploratory = False
            if repeated < min_repeated_proposals:
                if can_explore:
                    exploratory = True
                    exploration_used += 1
                    exploratory_approved[proposal_id] = {
                        "reason": "low_utility_confidence_exploration",
                        "utility_confidence": round(utility_confidence, 3),
                        "max_expected_utility_confidence": round(exploration_max_expected_confidence, 3),
                        "repetition_count": repeated,
                        "min_repeated_proposals": min_repeated_proposals,
                    }
                else:
                    skipped[proposal_id] = "insufficient_repetition"
                    continue

            if (
                utility_enabled
                and expected_utility is not None
                and utility_observations >= utility_min_observations_for_gating
                and expected_utility < utility_min_expected_utility
            ):
                skipped[proposal_id] = "negative_expected_utility"
                blocked_expected_utility[proposal_id] = {
                    "expected_utility": round(expected_utility, 4),
                    "min_expected_utility": round(utility_min_expected_utility, 4),
                    "observations": utility_observations,
                    "confidence": round(utility_confidence, 3),
                }
                continue

            # Phase 5.0c: Compute evidence rationale for actionable intelligence
            # Trust trend: compare first-half vs second-half trust for this stage
            stage_from_id = proposal_id.split(":")[0] if ":" in proposal_id else ""
            trust_trend = "unknown"
            if stage_from_id and history:
                half = max(1, len(history) // 2)
                first_half_scores: list[float] = []
                second_half_scores: list[float] = []
                for h_idx, h_row in enumerate(history):
                    if not isinstance(h_row, dict):
                        continue
                    ts = h_row.get("trust_stages", {})
                    if isinstance(ts, dict) and stage_from_id in ts:
                        try:
                            score = float(ts[stage_from_id])
                        except (TypeError, ValueError):
                            continue
                        if h_idx < half:
                            first_half_scores.append(score)
                        else:
                            second_half_scores.append(score)
                if first_half_scores and second_half_scores:
                    avg_first = sum(first_half_scores) / len(first_half_scores)
                    avg_second = sum(second_half_scores) / len(second_half_scores)
                    delta = avg_second - avg_first
                    if delta > 0.02:
                        trust_trend = "improving"
                    elif delta < -0.02:
                        trust_trend = "declining"
                    else:
                        trust_trend = "stable"

            new_approved.append(proposal_id)
            # Attach rationale to the proposal dict (ephemeral, for output only)
            proposal["approval_rationale"] = {
                "repetition_count": repeated,
                "lookback_runs": lookback_runs,
                "trust_score_at_approval": round(trust_score, 3),
                "trust_confidence_at_approval": round(trust_confidence_ema, 3),
                "trust_trend": trust_trend,
                "expected_utility": round(expected_utility, 4) if expected_utility is not None else None,
                "expected_utility_confidence": round(utility_confidence, 3),
                "utility_observations": utility_observations,
                "exploratory": exploratory,
            }

        # Phase 5.0c: Collect rationale for each newly approved ID
        approval_rationales: dict[str, dict[str, Any]] = {}
        for proposal in proposals:
            if not isinstance(proposal, dict):
                continue
            pid = str(proposal.get("proposal_id", "") or "")
            if pid in new_approved and "approval_rationale" in proposal:
                approval_rationales[pid] = proposal.pop("approval_rationale")

        return {
            "enabled": True,
            "lookback_runs": lookback_runs,
            "min_repeated_proposals": min_repeated_proposals,
            "max_new_approvals_per_run": max_new_approvals_per_run,
            "min_trust_score": round(min_trust_score, 3),
            "min_trust_confidence_ema": round(min_trust_confidence_ema, 3),
            "allow_modes": sorted(allow_modes),
            "considered": considered,
            "new_approved_proposal_ids": new_approved,
            "approval_rationales": approval_rationales,
            "cooldown_runs_after_revocation": cooldown_runs,
            "cooldown_ids_active": sorted(cooldown_ids),
            "cooldown_details": cooldown_details,
            "utility_learning": {
                "enabled": utility_enabled,
                "min_observations_for_gating": utility_min_observations_for_gating,
                "min_expected_utility": round(utility_min_expected_utility, 4),
                "exploration": {
                    "enabled": exploration_enabled,
                    "max_explorations_per_run": exploration_max_per_run,
                    "max_expected_utility_confidence": round(exploration_max_expected_confidence, 3),
                    "used": exploration_used,
                    "allow_modes": sorted(exploration_allow_modes),
                },
            },
            "exploratory_approved": exploratory_approved,
            "blocked_expected_utility": blocked_expected_utility,
            "permanently_blocked_ids": sorted(permanently_blocked),
            "skipped": skipped,
        }

    def _prune_self_reconfigure_approval_ledger(
        self,
        ledger: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Phase 4.6: Autonomously prune stale approval IDs from the ledger.

        Returns (updated_ledger, pruning_summary).
        """
        acceptance_cfg = self.adaptive_policy.get("self_reconfigure", {}).get("acceptance", {})
        auto_cfg = acceptance_cfg.get("autonomous_approval", {}) if isinstance(acceptance_cfg, dict) else {}
        prune_cfg = auto_cfg.get("pruning", {}) if isinstance(auto_cfg, dict) else {}
        enabled = isinstance(prune_cfg, dict) and bool(prune_cfg.get("enabled", False))

        if not enabled:
            return ledger, {"enabled": False, "removed": []}

        max_approved_raw = prune_cfg.get("max_approved_ids", 50)
        max_approved_ids = int(50 if max_approved_raw is None else max_approved_raw)
        if max_approved_ids < 0:
            max_approved_ids = 0
        expire_unused_raw = prune_cfg.get("expire_unused_after_runs", 60)
        expire_unused_after_runs = int(60 if expire_unused_raw is None else expire_unused_raw)
        if expire_unused_after_runs < 0:
            expire_unused_after_runs = 0
        expire_accepted_raw = prune_cfg.get("expire_after_acceptance_runs", 30)
        expire_after_acceptance_runs = int(30 if expire_accepted_raw is None else expire_accepted_raw)
        if expire_after_acceptance_runs < 0:
            expire_after_acceptance_runs = 0

        approved_ids = ledger.get("approved_proposal_ids", []) if isinstance(ledger, dict) else []
        if not isinstance(approved_ids, list):
            approved_ids = []
        approved_set = {str(item) for item in approved_ids if str(item)}

        run_audit = ledger.get("run_audit", []) if isinstance(ledger, dict) else []
        if not isinstance(run_audit, list):
            run_audit = []

        removed: dict[str, dict[str, Any]] = {}

        # Phase 5.0e: Build last-seen index for all approved IDs (used by multiple rules)
        last_seen_global: dict[str, int] = {}
        for idx, row in enumerate(run_audit):
            if not isinstance(row, dict):
                continue
            for pid in row.get("proposal_ids", []):
                spid = str(pid)
                if spid:
                    last_seen_global[spid] = idx

        # --- Expire IDs not proposed in the last N runs ---
        if expire_unused_after_runs > 0 and run_audit:
            recent_window = run_audit[-expire_unused_after_runs:]
            recently_proposed: set[str] = set()
            for row in recent_window:
                if not isinstance(row, dict):
                    continue
                for pid in row.get("proposal_ids", []):
                    spid = str(pid)
                    if spid:
                        recently_proposed.add(spid)
            for aid in list(approved_set):
                if aid not in recently_proposed:
                    ls_idx = last_seen_global.get(aid, -1)
                    removed[aid] = {
                        "reason": "unused_expired",
                        "last_seen_audit_index": ls_idx,
                        "runs_since_last_seen": (len(run_audit) - ls_idx - 1) if ls_idx >= 0 else len(run_audit),
                        "expire_unused_after_runs": expire_unused_after_runs,
                    }
                    approved_set.discard(aid)

        # --- Expire IDs that were accepted N+ runs ago ---
        if expire_after_acceptance_runs > 0 and run_audit:
            cutoff_idx = max(0, len(run_audit) - expire_after_acceptance_runs)
            old_accepted: set[str] = set()
            first_accepted_at: dict[str, int] = {}
            for r_idx, row in enumerate(run_audit[:cutoff_idx]):
                if not isinstance(row, dict):
                    continue
                for pid in row.get("accepted_proposal_ids", []):
                    spid = str(pid)
                    if spid:
                        old_accepted.add(spid)
                        if spid not in first_accepted_at:
                            first_accepted_at[spid] = r_idx
            # Only expire if the ID was NOT also accepted within the recent window
            recent_accepted: set[str] = set()
            for row in run_audit[cutoff_idx:]:
                if not isinstance(row, dict):
                    continue
                for pid in row.get("accepted_proposal_ids", []):
                    spid = str(pid)
                    if spid:
                        recent_accepted.add(spid)
            for aid in list(approved_set):
                if aid in old_accepted and aid not in recent_accepted:
                    acc_idx = first_accepted_at.get(aid, -1)
                    removed[aid] = {
                        "reason": "acceptance_expired",
                        "first_accepted_audit_index": acc_idx,
                        "runs_since_first_acceptance": (len(run_audit) - acc_idx - 1) if acc_idx >= 0 else len(run_audit),
                        "expire_after_acceptance_runs": expire_after_acceptance_runs,
                    }
                    approved_set.discard(aid)

        # --- Enforce hard cap ---
        if max_approved_ids > 0 and len(approved_set) > max_approved_ids:
            # Keep the most recently active IDs (those proposed most recently)
            scored = sorted(
                approved_set,
                key=lambda x: last_seen_global.get(x, -1),
                reverse=True,
            )
            to_keep = set(scored[:max_approved_ids])
            for aid in scored[max_approved_ids:]:
                if aid not in removed:  # don't double-count
                    ls_idx = last_seen_global.get(aid, -1)
                    removed[aid] = {
                        "reason": "cap_exceeded",
                        "last_seen_audit_index": ls_idx,
                        "runs_since_last_seen": (len(run_audit) - ls_idx - 1) if ls_idx >= 0 else len(run_audit),
                        "max_approved_ids": max_approved_ids,
                    }
                approved_set.discard(aid)

        updated_ledger = dict(ledger) if isinstance(ledger, dict) else {}
        updated_ledger["approved_proposal_ids"] = sorted(approved_set)

        return updated_ledger, {
            "enabled": True,
            "max_approved_ids": max_approved_ids,
            "expire_unused_after_runs": expire_unused_after_runs,
            "expire_after_acceptance_runs": expire_after_acceptance_runs,
            "ids_before": len(approved_ids),
            "ids_after": len(approved_set),
            "removed": removed,
        }

    def _evaluate_self_reconfigure_feedback(
        self,
        ledger: dict[str, Any],
        trust_snapshot: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Phase 4.7: Feedback loop — auto-revoke approved IDs that degraded trust.

        For each approved proposal ID that was accepted in a past run, compare
        the stage trust score at acceptance time with the current trust score.
        If trust degraded beyond the threshold, revoke the ID.

        Returns (updated_ledger, feedback_summary).
        """
        acceptance_cfg = self.adaptive_policy.get("self_reconfigure", {}).get("acceptance", {})
        auto_cfg = acceptance_cfg.get("autonomous_approval", {}) if isinstance(acceptance_cfg, dict) else {}
        fb_cfg = auto_cfg.get("feedback", {}) if isinstance(auto_cfg, dict) else {}
        enabled = isinstance(fb_cfg, dict) and bool(fb_cfg.get("enabled", False))

        if not enabled:
            return ledger, {"enabled": False, "revoked": {}}

        min_runs_raw = fb_cfg.get("min_runs_after_acceptance", 5)
        min_runs_after_acceptance = int(5 if min_runs_raw is None else min_runs_raw)
        if min_runs_after_acceptance < 1:
            min_runs_after_acceptance = 1
        max_degrad_raw = fb_cfg.get("max_trust_degradation", 0.15)
        max_trust_degradation = float(0.15 if max_degrad_raw is None else max_degrad_raw)
        if max_trust_degradation < 0.0:
            max_trust_degradation = 0.0
        max_revoc_raw = fb_cfg.get("max_revocations_per_run", 1)
        max_revocations_per_run = int(1 if max_revoc_raw is None else max_revoc_raw)
        if max_revocations_per_run < 0:
            max_revocations_per_run = 0

        approved_ids = ledger.get("approved_proposal_ids", []) if isinstance(ledger, dict) else []
        if not isinstance(approved_ids, list):
            approved_ids = []
        approved_set = set(str(item) for item in approved_ids if str(item))

        run_audit = ledger.get("run_audit", []) if isinstance(ledger, dict) else []
        if not isinstance(run_audit, list):
            run_audit = []

        # Current trust per stage
        current_trust: dict[str, float] = {}
        agents = trust_snapshot.get("agents", {}) if isinstance(trust_snapshot, dict) else {}
        if isinstance(agents, dict):
            for key, stats in agents.items():
                if key.startswith("stage:") and isinstance(stats, dict):
                    stage = key[len("stage:"):]
                    try:
                        current_trust[stage] = float(stats.get("trust_score", 0.5))
                    except (TypeError, ValueError):
                        current_trust[stage] = 0.5

        # For each approved ID, find the first run where it was accepted and
        # record the trust score for its stage at that point.
        revoked: dict[str, dict[str, Any]] = {}
        evaluated = 0

        for aid in sorted(approved_set):
            if len(revoked) >= max_revocations_per_run:
                break

            # Extract stage from proposal_id format: "{stage}:{mode}:{change}"
            parts = aid.split(":")
            if len(parts) < 2:
                continue
            stage = parts[0]

            # Find the audit row where this ID was first accepted
            first_accepted_idx: int | None = None
            baseline_trust: float | None = None
            for idx, row in enumerate(run_audit):
                if not isinstance(row, dict):
                    continue
                row_accepted = row.get("accepted_proposal_ids", [])
                if not isinstance(row_accepted, list):
                    continue
                if aid in [str(x) for x in row_accepted]:
                    first_accepted_idx = idx
                    # Use trust_stages from this row as baseline
                    trust_stages = row.get("trust_stages", {})
                    if isinstance(trust_stages, dict) and stage in trust_stages:
                        try:
                            baseline_trust = float(trust_stages[stage])
                        except (TypeError, ValueError):
                            pass
                    break

            if first_accepted_idx is None or baseline_trust is None:
                continue

            evaluated += 1

            # Check we have enough runs after acceptance
            runs_after = len(run_audit) - first_accepted_idx - 1
            if runs_after < min_runs_after_acceptance:
                continue

            # Compare baseline trust to current trust
            now_trust = current_trust.get(stage, 0.5)
            degradation = baseline_trust - now_trust

            if degradation > max_trust_degradation:
                # Phase 5.0b: Build trust trajectory from acceptance to now
                trajectory: list[dict[str, Any]] = []
                # Sample up to 10 evenly-spaced points between acceptance and now
                span = runs_after + 1  # total rows from acceptance to end
                step = max(1, span // 10)
                for t_idx in range(first_accepted_idx, len(run_audit), step):
                    t_row = run_audit[t_idx]
                    if not isinstance(t_row, dict):
                        continue
                    ts = t_row.get("trust_stages", {})
                    if isinstance(ts, dict) and stage in ts:
                        try:
                            trajectory.append({
                                "audit_index": t_idx,
                                "runs_after_acceptance": t_idx - first_accepted_idx,
                                "trust_score": round(float(ts[stage]), 3),
                            })
                        except (TypeError, ValueError):
                            pass
                # Always include the final current value
                trajectory.append({
                    "audit_index": len(run_audit),
                    "runs_after_acceptance": runs_after,
                    "trust_score": round(now_trust, 3),
                    "source": "live_snapshot",
                })

                revoked[aid] = {
                    "reason": "trust_degraded",
                    "stage": stage,
                    "baseline_trust": round(baseline_trust, 3),
                    "current_trust": round(now_trust, 3),
                    "degradation": round(degradation, 3),
                    "runs_after_acceptance": runs_after,
                    "trust_trajectory": trajectory,
                }
                approved_set.discard(aid)

        updated_ledger = dict(ledger) if isinstance(ledger, dict) else {}
        updated_ledger["approved_proposal_ids"] = sorted(approved_set)

        return updated_ledger, {
            "enabled": True,
            "min_runs_after_acceptance": min_runs_after_acceptance,
            "max_trust_degradation": round(max_trust_degradation, 3),
            "max_revocations_per_run": max_revocations_per_run,
            "evaluated": evaluated,
            "revoked": revoked,
        }

    def _evaluate_self_reconfigure_utility_learning(
        self,
        ledger: dict[str, Any],
        trust_snapshot: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Phase 5.3: Score accepted proposals and learn expected utility.

        Utility metric (MVP): stage trust delta from acceptance baseline to
        current trust snapshot. Positive deltas are favorable outcomes.

        Returns (updated_ledger, utility_summary).
        """
        acceptance_cfg = self.adaptive_policy.get("self_reconfigure", {}).get("acceptance", {})
        auto_cfg = acceptance_cfg.get("autonomous_approval", {}) if isinstance(acceptance_cfg, dict) else {}
        utility_cfg = auto_cfg.get("utility_learning", {}) if isinstance(auto_cfg, dict) else {}
        enabled = isinstance(utility_cfg, dict) and bool(utility_cfg.get("enabled", False))

        if not enabled:
            return ledger, {"enabled": False, "observed_outcomes": {}, "expected_utilities": {}}

        min_runs_raw = utility_cfg.get("min_runs_after_acceptance", 5)
        min_runs_after_acceptance = int(5 if min_runs_raw is None else min_runs_raw)
        if min_runs_after_acceptance < 1:
            min_runs_after_acceptance = 1

        min_obs_raw = utility_cfg.get("min_observations_for_gating", 2)
        min_observations_for_gating = int(2 if min_obs_raw is None else min_obs_raw)
        if min_observations_for_gating < 1:
            min_observations_for_gating = 1

        min_expected_raw = utility_cfg.get("min_expected_utility", -0.02)
        min_expected_utility = float(-0.02 if min_expected_raw is None else min_expected_raw)

        lookback_raw = utility_cfg.get("lookback_acceptance_events", 20)
        lookback_acceptance_events = int(20 if lookback_raw is None else lookback_raw)
        if lookback_acceptance_events < 1:
            lookback_acceptance_events = 1

        run_audit = ledger.get("run_audit", []) if isinstance(ledger, dict) else []
        if not isinstance(run_audit, list):
            run_audit = []

        outcomes_raw = ledger.get("proposal_outcomes", {}) if isinstance(ledger, dict) else {}
        proposal_outcomes: dict[str, dict[str, Any]] = {}
        if isinstance(outcomes_raw, dict):
            proposal_outcomes = {
                str(pid): dict(stats)
                for pid, stats in outcomes_raw.items()
                if str(pid) and isinstance(stats, dict)
            }

        # Current trust per stage
        current_trust: dict[str, float] = {}
        agents = trust_snapshot.get("agents", {}) if isinstance(trust_snapshot, dict) else {}
        if isinstance(agents, dict):
            for key, stats in agents.items():
                if key.startswith("stage:") and isinstance(stats, dict):
                    stage = key[len("stage:"):]
                    try:
                        current_trust[stage] = float(stats.get("trust_score", 0.5))
                    except (TypeError, ValueError):
                        current_trust[stage] = 0.5

        # Track recent acceptance events per proposal ID
        acceptance_events: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for idx, row in enumerate(run_audit):
            if not isinstance(row, dict):
                continue
            accepted_ids = row.get("accepted_proposal_ids", [])
            if not isinstance(accepted_ids, list):
                continue
            for raw_pid in accepted_ids:
                proposal_id = str(raw_pid)
                if not proposal_id:
                    continue
                entries = acceptance_events.setdefault(proposal_id, [])
                entries.append((idx, row))
                if len(entries) > lookback_acceptance_events:
                    entries.pop(0)

        observed_outcomes: dict[str, dict[str, Any]] = {}
        for proposal_id, events in acceptance_events.items():
            if not events:
                continue

            stats = proposal_outcomes.get(proposal_id, {})
            prev_scored_idx_raw = stats.get("last_scored_acceptance_index", -1)
            try:
                prev_scored_idx = int(-1 if prev_scored_idx_raw is None else prev_scored_idx_raw)
            except (TypeError, ValueError):
                prev_scored_idx = -1

            selected_event: tuple[int, dict[str, Any]] | None = None
            for candidate_idx, candidate_row in reversed(events):
                runs_after_candidate = len(run_audit) - candidate_idx - 1
                if runs_after_candidate < min_runs_after_acceptance:
                    continue
                if candidate_idx <= prev_scored_idx:
                    continue
                selected_event = (candidate_idx, candidate_row)
                break

            if selected_event is None:
                continue

            accept_idx, accept_row = selected_event
            stage = proposal_id.split(":")[0] if ":" in proposal_id else ""
            if not stage:
                continue

            trust_stages = accept_row.get("trust_stages", {}) if isinstance(accept_row, dict) else {}
            if not isinstance(trust_stages, dict) or stage not in trust_stages:
                continue
            try:
                baseline_trust = float(trust_stages[stage])
            except (TypeError, ValueError):
                continue

            runs_after_acceptance = len(run_audit) - accept_idx - 1
            if runs_after_acceptance < min_runs_after_acceptance:
                continue

            now_trust = float(current_trust.get(stage, 0.5))
            observed_utility = now_trust - baseline_trust

            obs_raw = stats.get("observations", 0)
            try:
                observations = int(0 if obs_raw is None else obs_raw)
            except (TypeError, ValueError):
                observations = 0
            if observations < 0:
                observations = 0

            avg_raw = stats.get("avg_utility", 0.0)
            try:
                avg_utility = float(0.0 if avg_raw is None else avg_raw)
            except (TypeError, ValueError):
                avg_utility = 0.0

            observations += 1
            avg_utility = avg_utility + ((observed_utility - avg_utility) / observations)

            positive = int(stats.get("positive_outcomes", 0) or 0)
            negative = int(stats.get("negative_outcomes", 0) or 0)
            neutral = int(stats.get("neutral_outcomes", 0) or 0)
            if observed_utility > 0.01:
                positive += 1
            elif observed_utility < -0.01:
                negative += 1
            else:
                neutral += 1

            confidence = min(1.0, observations / float(max(1, min_observations_for_gating)))

            proposal_outcomes[proposal_id] = {
                "stage": stage,
                "observations": observations,
                "avg_utility": round(avg_utility, 4),
                "last_observed_utility": round(observed_utility, 4),
                "positive_outcomes": positive,
                "negative_outcomes": negative,
                "neutral_outcomes": neutral,
                "expected_utility_confidence": round(confidence, 3),
                "last_scored_acceptance_index": accept_idx,
                "last_scored_run_id": self.run_id,
                "updated": datetime.now(timezone.utc).isoformat(),
            }

            observed_outcomes[proposal_id] = {
                "stage": stage,
                "baseline_trust": round(baseline_trust, 3),
                "current_trust": round(now_trust, 3),
                "observed_utility": round(observed_utility, 4),
                "expected_utility": round(avg_utility, 4),
                "confidence": round(confidence, 3),
                "observations": observations,
                "runs_after_acceptance": runs_after_acceptance,
            }

        if observed_outcomes and isinstance(run_audit, list):
            last_row = run_audit[-1] if run_audit else None
            if isinstance(last_row, dict):
                last_row["proposal_outcomes"] = observed_outcomes

        expected_utilities: dict[str, dict[str, Any]] = {}
        for proposal_id, stats in proposal_outcomes.items():
            if not isinstance(stats, dict):
                continue
            expected_utilities[proposal_id] = {
                "expected_utility": round(float(stats.get("avg_utility", 0.0) or 0.0), 4),
                "confidence": round(float(stats.get("expected_utility_confidence", 0.0) or 0.0), 3),
                "observations": int(stats.get("observations", 0) or 0),
            }

        updated_ledger = dict(ledger) if isinstance(ledger, dict) else {}
        updated_ledger["proposal_outcomes"] = proposal_outcomes
        updated_ledger["run_audit"] = run_audit

        return updated_ledger, {
            "enabled": True,
            "min_runs_after_acceptance": min_runs_after_acceptance,
            "min_observations_for_gating": min_observations_for_gating,
            "min_expected_utility": round(min_expected_utility, 4),
            "lookback_acceptance_events": lookback_acceptance_events,
            "observed_outcomes": observed_outcomes,
            "expected_utilities": expected_utilities,
        }

    def _evaluate_self_reconfigure_escalation(
        self,
        ledger: dict[str, Any],
        feedback_revoked_ids: list[str],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Phase 4.9: Escalation awareness — permanently block IDs
        that cycle through approve → degrade → revoke repeatedly.

        Scans the full audit history for cumulative revocation counts
        per ID.  When a newly-revoked ID's total revocation count meets
        or exceeds *max_revocation_cycles*, it is moved to the
        *permanently_blocked_ids* list in the ledger.

        Returns (updated_ledger, escalation_summary).
        """
        acceptance_cfg = self.adaptive_policy.get("self_reconfigure", {}).get("acceptance", {})
        auto_cfg = acceptance_cfg.get("autonomous_approval", {}) if isinstance(acceptance_cfg, dict) else {}
        fb_cfg = auto_cfg.get("feedback", {}) if isinstance(auto_cfg, dict) else {}
        esc_cfg = fb_cfg.get("escalation", {}) if isinstance(fb_cfg, dict) else {}
        enabled = isinstance(esc_cfg, dict) and bool(esc_cfg.get("enabled", False))

        if not enabled or not feedback_revoked_ids:
            return ledger, {"enabled": enabled, "newly_blocked": {}}

        max_cycles_raw = esc_cfg.get("max_revocation_cycles", 2)
        max_revocation_cycles = int(2 if max_cycles_raw is None else max_cycles_raw)
        if max_revocation_cycles < 1:
            max_revocation_cycles = 1

        # Build cumulative revocation count per ID from full audit history
        run_audit = ledger.get("run_audit", []) if isinstance(ledger, dict) else []
        if not isinstance(run_audit, list):
            run_audit = []
        revocation_counts: dict[str, int] = {}
        for row in run_audit:
            if not isinstance(row, dict):
                continue
            row_revoked = row.get("feedback_revoked_ids", [])
            if not isinstance(row_revoked, list):
                continue
            for rid in row_revoked:
                srid = str(rid)
                if srid:
                    revocation_counts[srid] = revocation_counts.get(srid, 0) + 1

        # Also count the current run's revocations (just recorded)
        for rid in feedback_revoked_ids:
            srid = str(rid)
            if srid:
                revocation_counts[srid] = revocation_counts.get(srid, 0)
                # Note: current run's feedback_revoked_ids are already in the
                # audit entry at this point, so they are counted above.

        blocked_raw = ledger.get("permanently_blocked_ids", []) if isinstance(ledger, dict) else []
        if not isinstance(blocked_raw, list):
            blocked_raw = []
        blocked_set = set(str(item) for item in blocked_raw if str(item))

        newly_blocked: dict[str, dict[str, Any]] = {}
        for rid in feedback_revoked_ids:
            srid = str(rid)
            if not srid or srid in blocked_set:
                continue
            total = revocation_counts.get(srid, 0)
            if total >= max_revocation_cycles:
                # Phase 5.0a: Build structural diagnosis — acceptance cycle history
                parts = srid.split(":")
                stage = parts[0] if parts else ""
                cycles: list[dict[str, Any]] = []
                # Walk audit to find each acceptance → revocation cycle
                cycle_start_idx: int | None = None
                cycle_start_trust: float | None = None
                for a_idx, a_row in enumerate(run_audit):
                    if not isinstance(a_row, dict):
                        continue
                    # Check if this row accepted the ID
                    row_accepted = a_row.get("accepted_proposal_ids", [])
                    if isinstance(row_accepted, list) and srid in [str(x) for x in row_accepted]:
                        ts = a_row.get("trust_stages", {})
                        if isinstance(ts, dict) and stage in ts:
                            try:
                                cycle_start_trust = round(float(ts[stage]), 3)
                            except (TypeError, ValueError):
                                cycle_start_trust = None
                        else:
                            cycle_start_trust = None
                        cycle_start_idx = a_idx
                    # Check if this row revoked the ID
                    row_revoked = a_row.get("feedback_revoked_ids", [])
                    if isinstance(row_revoked, list) and srid in [str(x) for x in row_revoked]:
                        revoke_trust: float | None = None
                        ts = a_row.get("trust_stages", {})
                        if isinstance(ts, dict) and stage in ts:
                            try:
                                revoke_trust = round(float(ts[stage]), 3)
                            except (TypeError, ValueError):
                                pass
                        cycles.append({
                            "accepted_at_index": cycle_start_idx,
                            "accepted_trust": cycle_start_trust,
                            "revoked_at_index": a_idx,
                            "revoked_trust": revoke_trust,
                            "runs_in_cycle": (a_idx - cycle_start_idx) if cycle_start_idx is not None else None,
                        })
                        cycle_start_idx = None
                        cycle_start_trust = None

                newly_blocked[srid] = {
                    "reason": "exceeded_max_revocation_cycles",
                    "total_revocations": total,
                    "max_revocation_cycles": max_revocation_cycles,
                    "diagnosis": {
                        "stage": stage,
                        "cycles": cycles,
                        "pattern": "structural" if len(cycles) >= max_revocation_cycles else "transient",
                        "recommendation": (
                            f"Stage '{stage}' degrades trust each time this reconfiguration is applied. "
                            "The underlying issue is likely a mismatch between the proposed change and "
                            "the stage's operational requirements."
                        ),
                    },
                }
                blocked_set.add(srid)
                # Also ensure it is removed from approved_proposal_ids
                approved = ledger.get("approved_proposal_ids", []) if isinstance(ledger, dict) else []
                if isinstance(approved, list):
                    ledger["approved_proposal_ids"] = [
                        str(item) for item in approved
                        if str(item) and str(item) != srid
                    ]

        updated_ledger = dict(ledger) if isinstance(ledger, dict) else {}
        updated_ledger["permanently_blocked_ids"] = sorted(blocked_set)

        return updated_ledger, {
            "enabled": True,
            "max_revocation_cycles": max_revocation_cycles,
            "newly_blocked": newly_blocked,
        }

    def _apply_cortex_adaptation(
        self,
        result: StageResult,
        triggers: list[dict[str, Any]],
        contract,
    ) -> tuple[StageResult, list[dict[str, Any]]]:
        """Phase 1.1 adaptive coordination for cortex.

        If trigger conditions indicate weak execution quality, run one
        recomposed retry and optionally adopt its output.
        """
        if result.status != "passed":
            return result, triggers

        trigger_types = {t.get("type") for t in triggers if t.get("type")}
        stage_context = self.trust_ledger.get_stage_context("cortex")
        plan = resolve_cortex_adaptive_plan(
            trigger_types=trigger_types,
            base_config={
                "cortex_max_protocols": self.config.cortex_max_protocols,
                "cortex_max_steps": self.config.cortex_max_steps,
            },
            policy=self.adaptive_policy,
            trust_score=stage_context.get("trust_score", 0.5),
            stage_context=stage_context,
        )
        if not plan:
            return result, triggers

        base_protocols = int(result.output.get("protocols_run", 0) or 0)
        retry_config = replace(
            self.config,
            cortex_gap_type=plan["retry_gap_type"],
            cortex_max_protocols=plan["retry_max_protocols"],
            cortex_max_steps=plan["retry_max_steps"],
        )

        retry_status = "failed"
        retry_output: dict[str, Any] = {}
        retry_triggers: list[dict[str, Any]] = []
        retry_error: str | None = None
        t0 = time.time()
        try:
            retry_output = stage_cortex(retry_config)
            retry_status = "passed"
        except Exception as e:
            retry_error = f"{type(e).__name__}: {e}"
        retry_elapsed = round(time.time() - t0, 2)

        if retry_status == "passed":
            retry_triggers = self.trigger_engine.evaluate(
                stage="cortex",
                status=retry_status,
                output=retry_output,
                elapsed_sec=retry_elapsed,
                contract=contract,
            )

        retry_protocols = int(retry_output.get("protocols_run", 0) or 0)
        adoption_rule = plan.get("adoption_rule", "higher_protocols_run")
        if adoption_rule == "always_on_success":
            adopted = retry_status == "passed"
        else:
            adopted = retry_status == "passed" and retry_protocols > base_protocols

        adaptive_record = {
            "triggered_by": plan["reason"],
            "plan": plan,
            "retry_status": retry_status,
            "retry_elapsed_sec": retry_elapsed,
            "retry_protocols_run": retry_protocols,
            "adopted": adopted,
            "retry_error": retry_error,
            "retry_triggers": retry_triggers,
        }

        self.delegation_events.append(
            {
                "event": "adaptive_action",
                "ts": datetime.now(timezone.utc).isoformat(),
                "stage": "cortex",
                "details": adaptive_record,
            }
        )

        result.elapsed_sec = round(result.elapsed_sec + retry_elapsed, 2)

        if adopted:
            previous_summary = {
                "protocols_run": base_protocols,
                "total_steps": result.output.get("total_steps", 0),
                "session_id": result.output.get("session_id", ""),
            }
            result.output = retry_output
            result.output["adaptive_response"] = {
                "adopted": True,
                "previous_output_summary": previous_summary,
                **adaptive_record,
            }
            return result, retry_triggers

        result.output["adaptive_response"] = {
            "adopted": False,
            **adaptive_record,
        }

        combined_trigger_types = set(t.get("type") for t in triggers)
        combined = list(triggers)
        for trigger in retry_triggers:
            trigger_type = trigger.get("type")
            if trigger_type not in combined_trigger_types:
                combined.append(trigger)
                combined_trigger_types.add(trigger_type)

        return result, combined

    def _apply_non_cortex_adaptation(
        self,
        stage_name: str,
        result: StageResult,
        triggers: list[dict[str, Any]],
        contract,
        cortex_result: dict[str, Any],
    ) -> tuple[StageResult, list[dict[str, Any]]]:
        """Phase 1.3 adaptive coordination for non-cortex stages."""
        if result.status not in {"failed", "passed"}:
            return result, triggers

        trigger_types = {t.get("type") for t in triggers if t.get("type")}
        stage_context = self.trust_ledger.get_stage_context(stage_name)
        plan = resolve_stage_adaptive_plan(
            stage=stage_name,
            trigger_types=trigger_types,
            policy=self.adaptive_policy,
            trust_score=stage_context.get("trust_score", 0.5),
            stage_context=stage_context,
        )
        if not plan:
            return result, triggers

        if plan.get("strategy") != "retry_same_stage":
            return result, triggers

        retry_output: dict[str, Any] = {}
        retry_status = "failed"
        retry_error: str | None = None
        t0 = time.time()
        try:
            if stage_name == "consolidate":
                retry_output = stage_consolidate(self.config, cortex_result)
            elif stage_name == "hippocampus":
                retry_output = stage_hippocampus(self.config)
            elif stage_name == "evolve":
                retry_output = stage_evolve(self.config)
            else:
                return result, triggers

            retry_status = "passed"
            if isinstance(retry_output, dict) and retry_output.get("status") == "skipped":
                retry_status = "skipped"
        except Exception as e:
            retry_error = f"{type(e).__name__}: {e}"
        retry_elapsed = round(time.time() - t0, 2)

        retry_triggers: list[dict[str, Any]] = []
        if retry_status in {"passed", "failed"}:
            retry_triggers = self.trigger_engine.evaluate(
                stage=stage_name,
                status=retry_status,
                output=retry_output,
                elapsed_sec=retry_elapsed,
                contract=contract,
            )

        adoption_rule = plan.get("adoption_rule", "success_replaces_failure")
        if adoption_rule == "always_on_success":
            adopted = retry_status == "passed"
        else:
            adopted = result.status == "failed" and retry_status == "passed"

        adaptive_record = {
            "triggered_by": plan.get("reason", "unknown"),
            "plan": plan,
            "retry_status": retry_status,
            "retry_elapsed_sec": retry_elapsed,
            "adopted": adopted,
            "retry_error": retry_error,
            "retry_triggers": retry_triggers,
        }

        self.delegation_events.append(
            {
                "event": "adaptive_action",
                "ts": datetime.now(timezone.utc).isoformat(),
                "stage": stage_name,
                "details": adaptive_record,
            }
        )

        result.elapsed_sec = round(result.elapsed_sec + retry_elapsed, 2)

        if adopted:
            result.status = retry_status
            result.error = None
            result.output = retry_output or {}
            result.output["delegation_contract"] = contract.to_dict()
            result.output["adaptive_response"] = {
                "adopted": True,
                **adaptive_record,
            }
            return result, retry_triggers

        result.output["adaptive_response"] = {
            "adopted": False,
            **adaptive_record,
        }

        combined_trigger_types = set(t.get("type") for t in triggers)
        combined = list(triggers)
        for trigger in retry_triggers:
            trigger_type = trigger.get("type")
            if trigger_type not in combined_trigger_types:
                combined.append(trigger)
                combined_trigger_types.add(trigger_type)

        return result, combined

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

        # Delegation events (contracts + triggers)
        delegation_events_path = self.run_dir / "delegation_events.json"
        delegation_events_path.write_text(
            json.dumps(self.delegation_events, indent=2, default=str),
            encoding="utf-8",
        )

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
