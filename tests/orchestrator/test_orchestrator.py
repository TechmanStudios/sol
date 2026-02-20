"""
Tests for sol-orchestrator — pipeline runner, stage isolation,
core immutability verification, and config handling.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_ORCH_DIR = _SOL_ROOT / "tools" / "sol-orchestrator"
_CORE_DIR = _SOL_ROOT / "tools" / "sol-core"

for p in (_ORCH_DIR, _CORE_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from orchestrator import (
    PipelineConfig, PipelineRunner, StageResult,
    STAGES, STAGE_DESCRIPTIONS,
    stage_smoke, verify_core_immutability,
    _graph_sha256, _EXPECTED_SHA,
)


# ======================================================================
# PipelineConfig
# ======================================================================

class TestPipelineConfig:
    def test_default_stages(self):
        cfg = PipelineConfig()
        assert cfg.active_stages == list(STAGES)

    def test_skip_stages(self):
        cfg = PipelineConfig(skip=["evolve", "hippocampus"])
        active = cfg.active_stages
        assert "evolve" not in active
        assert "hippocampus" not in active
        assert "cortex" in active
        assert "smoke" in active

    def test_custom_stages(self):
        cfg = PipelineConfig(stages=["smoke", "cortex", "report"])
        assert cfg.active_stages == ["smoke", "cortex", "report"]

    def test_combined_skip_and_custom(self):
        cfg = PipelineConfig(stages=["smoke", "cortex", "report"], skip=["cortex"])
        assert cfg.active_stages == ["smoke", "report"]

    def test_dry_run_flag(self):
        cfg = PipelineConfig(dry_run=True)
        assert cfg.dry_run is True


# ======================================================================
# StageResult
# ======================================================================

class TestStageResult:
    def test_to_dict(self):
        r = StageResult(stage="smoke", status="passed", elapsed_sec=1.5)
        d = r.to_dict()
        assert d["stage"] == "smoke"
        assert d["status"] == "passed"
        assert d["elapsed_sec"] == 1.5

    def test_default_pending(self):
        r = StageResult(stage="cortex")
        assert r.status == "pending"


# ======================================================================
# Core Immutability
# ======================================================================

class TestCoreImmutability:
    def test_sha256_matches_expected(self):
        assert _graph_sha256() == _EXPECTED_SHA

    def test_verify_returns_true(self):
        assert verify_core_immutability() is True


# ======================================================================
# stage_smoke
# ======================================================================

class TestStageSmoke:
    def test_smoke_passes(self):
        cfg = PipelineConfig()
        result = stage_smoke(cfg)
        assert result["engine_ok"] is True
        assert result["nodes"] == 140
        assert result["mass"] > 0
        assert result["entropy"] > 0
        assert result["core_sha256"] == _EXPECTED_SHA


# ======================================================================
# STAGE_DESCRIPTIONS
# ======================================================================

class TestConstants:
    def test_all_stages_have_descriptions(self):
        for s in STAGES:
            assert s in STAGE_DESCRIPTIONS, f"No description for stage '{s}'"


# ======================================================================
# PipelineRunner — dry-run (fast, no real execution)
# ======================================================================

class TestPipelineRunnerDryRun:
    def test_dry_run_all_stages(self, tmp_path, monkeypatch):
        """Dry run with all stages — everything should pass/skip, no real execution."""
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")

        cfg = PipelineConfig(
            dry_run=True,
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        summary = runner.run()

        assert summary["core_immutability"] == "PASS"
        assert summary["pipeline_verdict"] == "PASS"
        # Smoke should still pass (it's a real engine check even in dry run)
        assert runner.results["smoke"].status == "passed"
        # Cortex in dry run still runs (but with dry_run flag)
        assert runner.results["cortex"].status == "passed"

    def test_delegation_summary_includes_self_reconfigure(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")

        cfg = PipelineConfig(
            dry_run=True,
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        summary = runner.run()

        delegation = summary.get("delegation_v1", {})
        assert delegation.get("enabled") is True
        self_reconfigure = delegation.get("self_reconfigure", {})
        assert "enabled" in self_reconfigure
        assert "proposal_only" in self_reconfigure
        assert "proposals" in self_reconfigure
        acceptance = self_reconfigure.get("acceptance", {})
        assert "require_explicit_approval" in acceptance
        assert "accepted_proposals" in acceptance
        assert acceptance.get("auto_apply_enabled") is False

    def test_self_reconfigure_acceptance_uses_approval_ledger(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        approved_ids = [
            "cortex:relax:relax_retry_limits",
            "consolidate:relax:relax_retry_limits",
            "hippocampus:relax:relax_retry_limits",
            "evolve:relax:relax_retry_limits",
            "cortex:tighten:tighten_retry_limits",
            "consolidate:tighten:tighten_retry_limits",
            "hippocampus:tighten:tighten_retry_limits",
            "evolve:tighten:tighten_retry_limits",
        ]

        approval_ledger = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger.parent.mkdir(parents=True, exist_ok=True)
        approval_ledger.write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated": "2026-02-17T00:00:00+00:00",
                    "approved_proposal_ids": approved_ids,
                    "run_audit": [],
                }
            ),
            encoding="utf-8",
        )

        cfg = PipelineConfig(
            dry_run=True,
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        accepted = acceptance.get("accepted_proposals", [])
        assert len(accepted) == 1
        assert accepted[0].get("proposal_id") in approved_ids

        persisted = json.loads(approval_ledger.read_text(encoding="utf-8"))
        run_audit = persisted.get("run_audit", [])
        assert len(run_audit) >= 1
        assert run_audit[-1].get("run_id") == runner.run_id

    def test_self_reconfigure_autonomous_approval_without_manual_ids(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        approval_ledger = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger.parent.mkdir(parents=True, exist_ok=True)
        approval_ledger.write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated": "2026-02-17T00:00:00+00:00",
                    "approved_proposal_ids": [],
                    "run_audit": [],
                }
            ),
            encoding="utf-8",
        )

        cfg = PipelineConfig(
            dry_run=True,
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["min_repeated_proposals"] = 1
        auto_cfg["max_new_approvals_per_run"] = 1
        auto_cfg["min_trust_score"] = 0.0
        auto_cfg["min_trust_confidence_ema"] = 0.0
        auto_cfg["allow_modes"] = ["relax", "tighten"]

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        autonomous = acceptance.get("autonomous_approval", {})
        accepted = acceptance.get("accepted_proposals", [])

        assert len(autonomous.get("new_approved_proposal_ids", [])) == 1
        assert len(accepted) == 1
        assert accepted[0].get("proposal_id") == autonomous.get("new_approved_proposal_ids", [""])[0]

        persisted = json.loads(approval_ledger.read_text(encoding="utf-8"))
        assert autonomous.get("new_approved_proposal_ids", [""])[0] in persisted.get("approved_proposal_ids", [])
        run_audit = persisted.get("run_audit", [])
        assert run_audit[-1].get("autonomous_approved_proposal_ids")

    def test_self_reconfigure_pruning_expires_unused_ids(self, tmp_path, monkeypatch):
        """Phase 4.6: IDs not proposed within expire_unused_after_runs are pruned."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        # Seed ledger with a stale ID that was never proposed in recent audit
        stale_id = "cortex:relax:stale_old_id"
        fresh_id = "cortex:relax:relax_retry_limits"
        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        approval_ledger_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated": "2026-02-17T00:00:00+00:00",
                    "approved_proposal_ids": [stale_id, fresh_id],
                    "run_audit": [
                        # stale_id was only proposed 5 runs ago, but expire window is 3
                        {"run_id": "old-1", "ts": "2026-02-10T00:00:00+00:00", "proposal_ids": [stale_id], "accepted_proposal_ids": [], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                        {"run_id": "old-2", "ts": "2026-02-11T00:00:00+00:00", "proposal_ids": [stale_id], "accepted_proposal_ids": [], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                        # Recent: only fresh_id proposed
                        {"run_id": "recent-1", "ts": "2026-02-15T00:00:00+00:00", "proposal_ids": [fresh_id], "accepted_proposal_ids": [], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                        {"run_id": "recent-2", "ts": "2026-02-16T00:00:00+00:00", "proposal_ids": [fresh_id], "accepted_proposal_ids": [], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                        {"run_id": "recent-3", "ts": "2026-02-17T00:00:00+00:00", "proposal_ids": [fresh_id], "accepted_proposal_ids": [], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                    ],
                }
            ),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        # Set expire_unused_after_runs=3 so only last 3 audit rows matter
        prune_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]["pruning"]
        prune_cfg["enabled"] = True
        prune_cfg["expire_unused_after_runs"] = 3
        prune_cfg["expire_after_acceptance_runs"] = 999  # disable acceptance expiry for this test
        prune_cfg["max_approved_ids"] = 999  # disable cap for this test

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        pruning = acceptance.get("approval_ledger", {}).get("pruning", {})

        assert pruning.get("enabled") is True
        assert stale_id in pruning.get("removed", {}), f"Expected stale_id to be pruned: {pruning}"
        assert pruning["removed"][stale_id]["reason"] == "unused_expired"
        assert pruning["removed"][stale_id]["runs_since_last_seen"] > 0

        # Verify persisted ledger no longer contains stale_id
        persisted = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
        assert stale_id not in persisted.get("approved_proposal_ids", [])

    def test_self_reconfigure_pruning_expires_accepted_and_caps(self, tmp_path, monkeypatch):
        """Phase 4.6: IDs accepted long ago are expired; hard cap enforced."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        accepted_old_id = "cortex:relax:accepted_long_ago"
        active_id_1 = "cortex:relax:active_1"
        active_id_2 = "consolidate:relax:active_2"
        cap_overflow_id = "evolve:relax:overflow"

        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        approval_ledger_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated": "2026-02-17T00:00:00+00:00",
                    "approved_proposal_ids": [accepted_old_id, active_id_1, active_id_2, cap_overflow_id],
                    "run_audit": [
                        # accepted_old_id was accepted 5 runs ago (old)
                        {"run_id": "old-1", "ts": "2026-02-10T00:00:00+00:00", "proposal_ids": [accepted_old_id, active_id_1], "accepted_proposal_ids": [accepted_old_id], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                        {"run_id": "old-2", "ts": "2026-02-11T00:00:00+00:00", "proposal_ids": [active_id_1], "accepted_proposal_ids": [], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                        {"run_id": "old-3", "ts": "2026-02-12T00:00:00+00:00", "proposal_ids": [active_id_1, active_id_2], "accepted_proposal_ids": [], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                        # Recent window (last 2 runs) — accepted_old_id NOT accepted recently
                        {"run_id": "recent-1", "ts": "2026-02-16T00:00:00+00:00", "proposal_ids": [active_id_1, active_id_2], "accepted_proposal_ids": [active_id_1], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                        {"run_id": "recent-2", "ts": "2026-02-17T00:00:00+00:00", "proposal_ids": [active_id_1, active_id_2, cap_overflow_id], "accepted_proposal_ids": [], "autonomous_approved_proposal_ids": [], "pending_proposals": 0},
                    ],
                }
            ),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        prune_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]["pruning"]
        prune_cfg["enabled"] = True
        prune_cfg["expire_unused_after_runs"] = 999  # disable unused expiry
        prune_cfg["expire_after_acceptance_runs"] = 2  # only last 2 runs are "recent"
        prune_cfg["max_approved_ids"] = 2  # hard cap at 2

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        pruning = acceptance.get("approval_ledger", {}).get("pruning", {})

        assert pruning.get("enabled") is True
        removed = pruning.get("removed", {})
        # accepted_old_id should be expired (accepted in old window, not in recent)
        assert accepted_old_id in removed, f"Expected acceptance-expired: {removed}"
        assert removed[accepted_old_id]["reason"] == "acceptance_expired"
        assert removed[accepted_old_id]["runs_since_first_acceptance"] > 0

        # After acceptance expiry, remaining = active_id_1, active_id_2, cap_overflow_id (3)
        # Cap = 2, so one more should be pruned as cap_exceeded
        assert pruning["ids_after"] <= 2, f"Cap should limit to 2: {pruning}"

        # Verify persisted
        persisted = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
        assert accepted_old_id not in persisted.get("approved_proposal_ids", [])
        assert len(persisted.get("approved_proposal_ids", [])) <= 2

    def test_self_reconfigure_feedback_revokes_degraded_approval(self, tmp_path, monkeypatch):
        """Phase 4.7: An accepted ID whose stage trust degraded is auto-revoked."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        degraded_id = "cortex:relax:relax_retry_limits"
        healthy_id = "consolidate:relax:relax_retry_limits"

        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Build audit: degraded_id accepted 10 runs ago with high baseline trust
        audit_rows = []
        # Row 0: acceptance row — trust was 0.95 for cortex at acceptance time
        audit_rows.append({
            "run_id": "accept-run",
            "ts": "2026-02-05T00:00:00+00:00",
            "proposal_ids": [degraded_id, healthy_id],
            "accepted_proposal_ids": [degraded_id, healthy_id],
            "autonomous_approved_proposal_ids": [],
            "pending_proposals": 0,
            "trust_stages": {"cortex": 0.95, "consolidate": 0.90},
        })
        # Rows 1-9: subsequent runs (enough for min_runs_after_acceptance=5)
        for i in range(1, 10):
            audit_rows.append({
                "run_id": f"post-{i}",
                "ts": f"2026-02-{5+i:02d}T00:00:00+00:00",
                "proposal_ids": [degraded_id, healthy_id],
                "accepted_proposal_ids": [],
                "autonomous_approved_proposal_ids": [],
                "pending_proposals": 0,
                "trust_stages": {"cortex": round(0.95 - i * 0.05, 3), "consolidate": 0.88},
            })

        approval_ledger_path.write_text(
            json.dumps({
                "version": 1,
                "updated": "2026-02-17T00:00:00+00:00",
                "approved_proposal_ids": [degraded_id, healthy_id],
                "run_audit": audit_rows,
            }),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)

        # Enable feedback with low degradation threshold
        fb_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]["feedback"]
        fb_cfg["enabled"] = True
        fb_cfg["min_runs_after_acceptance"] = 5
        fb_cfg["max_trust_degradation"] = 0.10  # cortex dropped 0.95->~0.50 = 0.45 degradation
        fb_cfg["max_revocations_per_run"] = 2

        # Disable pruning to isolate feedback test
        runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]["pruning"]["enabled"] = False

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        feedback = acceptance.get("approval_ledger", {}).get("feedback", {})

        assert feedback.get("enabled") is True
        revoked = feedback.get("revoked", {})
        # cortex trust degraded by ~0.45 (0.95 -> current ~0.5 in dry-run)
        # The degraded_id should be revoked
        assert degraded_id in revoked, f"Expected degraded_id revoked: {feedback}"
        assert revoked[degraded_id]["reason"] == "trust_degraded"
        assert revoked[degraded_id]["baseline_trust"] == 0.95

        # Phase 5.0b: Verify trust trajectory is included
        trajectory = revoked[degraded_id].get("trust_trajectory", [])
        assert len(trajectory) >= 2, f"Expected trajectory samples: {revoked[degraded_id]}"
        # First sample should be near baseline, last should be near current
        assert trajectory[0]["trust_score"] >= 0.9
        assert trajectory[-1]["source"] == "live_snapshot"

        # Verify persisted ledger no longer contains degraded_id
        persisted = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
        assert degraded_id not in persisted.get("approved_proposal_ids", [])

    def test_self_reconfigure_feedback_skips_recent_acceptance(self, tmp_path, monkeypatch):
        """Phase 4.7: Feedback does not revoke if too few runs after acceptance."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        recent_id = "cortex:relax:relax_retry_limits"

        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Acceptance was only 2 runs ago — below min_runs_after_acceptance=5
        audit_rows = [
            {
                "run_id": "accept-run",
                "ts": "2026-02-15T00:00:00+00:00",
                "proposal_ids": [recent_id],
                "accepted_proposal_ids": [recent_id],
                "autonomous_approved_proposal_ids": [],
                "pending_proposals": 0,
                "trust_stages": {"cortex": 0.95},
            },
            {
                "run_id": "post-1",
                "ts": "2026-02-16T00:00:00+00:00",
                "proposal_ids": [recent_id],
                "accepted_proposal_ids": [],
                "autonomous_approved_proposal_ids": [],
                "pending_proposals": 0,
                "trust_stages": {"cortex": 0.4},  # big drop, but too recent
            },
        ]

        approval_ledger_path.write_text(
            json.dumps({
                "version": 1,
                "updated": "2026-02-17T00:00:00+00:00",
                "approved_proposal_ids": [recent_id],
                "run_audit": audit_rows,
            }),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)

        fb_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]["feedback"]
        fb_cfg["enabled"] = True
        fb_cfg["min_runs_after_acceptance"] = 5  # need 5, only have 2
        fb_cfg["max_trust_degradation"] = 0.10
        fb_cfg["max_revocations_per_run"] = 1

        runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]["pruning"]["enabled"] = False

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        feedback = acceptance.get("approval_ledger", {}).get("feedback", {})

        assert feedback.get("enabled") is True
        revoked = feedback.get("revoked", {})
        # Should NOT be revoked — too recent
        assert recent_id not in revoked, f"Should not revoke recent acceptance: {feedback}"

        # ID should still be in persisted ledger
        persisted = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
        assert recent_id in persisted.get("approved_proposal_ids", [])

    def test_self_reconfigure_cooldown_blocks_reapproval(self, tmp_path, monkeypatch):
        """Phase 4.8: A revoked ID cannot be auto-approved during cooldown window."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        revoked_id = "cortex:relax:relax_retry_limits"

        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Build audit: revoked_id was feedback-revoked 2 runs ago (within cooldown=5)
        audit_rows = []
        for i in range(5):
            row = {
                "run_id": f"run-{i}",
                "ts": f"2026-02-{10+i:02d}T00:00:00+00:00",
                "proposal_ids": [revoked_id],
                "accepted_proposal_ids": [],
                "autonomous_approved_proposal_ids": [],
                "pending_proposals": 0,
            }
            # Mark the revocation 2 runs ago
            if i == 3:
                row["feedback_revoked_ids"] = [revoked_id]
            audit_rows.append(row)

        approval_ledger_path.write_text(
            json.dumps({
                "version": 1,
                "updated": "2026-02-17T00:00:00+00:00",
                "approved_proposal_ids": [],  # revoked, so not in approved list
                "run_audit": audit_rows,
            }),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["min_repeated_proposals"] = 1
        auto_cfg["max_new_approvals_per_run"] = 1
        auto_cfg["min_trust_score"] = 0.0
        auto_cfg["min_trust_confidence_ema"] = 0.0
        auto_cfg["allow_modes"] = ["relax", "tighten"]
        auto_cfg["feedback"]["cooldown_runs_after_revocation"] = 5
        auto_cfg["pruning"]["enabled"] = False
        auto_cfg["feedback"]["enabled"] = False  # disable feedback eval itself for this test

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        autonomous = acceptance.get("autonomous_approval", {})

        # The proposal should be skipped due to cooldown
        skipped = autonomous.get("skipped", {})
        assert revoked_id in skipped, f"Expected cooldown skip: {autonomous}"
        assert skipped[revoked_id] == "revocation_cooldown"
        assert len(autonomous.get("new_approved_proposal_ids", [])) == 0

    def test_self_reconfigure_cooldown_expires_allows_reapproval(self, tmp_path, monkeypatch):
        """Phase 4.8: After cooldown expires, a previously revoked ID can be re-approved."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        old_revoked_id = "cortex:relax:relax_retry_limits"

        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Build audit: revoked_id was feedback-revoked 10 runs ago, cooldown=3
        audit_rows = []
        for i in range(10):
            row = {
                "run_id": f"run-{i}",
                "ts": f"2026-02-{10+i:02d}T00:00:00+00:00",
                "proposal_ids": [old_revoked_id],
                "accepted_proposal_ids": [],
                "autonomous_approved_proposal_ids": [],
                "pending_proposals": 0,
            }
            # Revocation happened at run-0 (oldest)
            if i == 0:
                row["feedback_revoked_ids"] = [old_revoked_id]
            audit_rows.append(row)

        approval_ledger_path.write_text(
            json.dumps({
                "version": 1,
                "updated": "2026-02-17T00:00:00+00:00",
                "approved_proposal_ids": [],
                "run_audit": audit_rows,
            }),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["min_repeated_proposals"] = 1
        auto_cfg["max_new_approvals_per_run"] = 1
        auto_cfg["min_trust_score"] = 0.0
        auto_cfg["min_trust_confidence_ema"] = 0.0
        auto_cfg["allow_modes"] = ["relax", "tighten"]
        auto_cfg["feedback"]["cooldown_runs_after_revocation"] = 3  # only last 3 runs checked
        auto_cfg["pruning"]["enabled"] = False
        auto_cfg["feedback"]["enabled"] = False

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        autonomous = acceptance.get("autonomous_approval", {})

        # Cooldown expired (revocation was 10 runs ago, window=3) → should be re-approved
        assert len(autonomous.get("new_approved_proposal_ids", [])) == 1
        skipped = autonomous.get("skipped", {})
        assert old_revoked_id not in skipped, f"Should not be blocked: {autonomous}"

        # Verify persisted
        persisted = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
        assert old_revoked_id in persisted.get("approved_proposal_ids", [])

    def test_self_reconfigure_escalation_blocks_repeatedly_revoked(self, tmp_path, monkeypatch):
        """Phase 4.9: An ID revoked >= max_revocation_cycles times is permanently blocked."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        target_id = "cortex:relax:relax_retry_limits"

        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Build audit: target_id was already revoked once in old history, and
        # will be revoked again in this run → total = 2 >= max_revocation_cycles=2
        audit_rows = []
        # First cycle: approved at run-0, accepted at run-1, revoked at run-5
        audit_rows.append({
            "run_id": "run-0",
            "ts": "2026-02-01T00:00:00+00:00",
            "proposal_ids": [target_id],
            "accepted_proposal_ids": [],
            "autonomous_approved_proposal_ids": [target_id],
            "pending_proposals": 0,
            "trust_stages": {"cortex": 0.95},
        })
        audit_rows.append({
            "run_id": "run-1",
            "ts": "2026-02-02T00:00:00+00:00",
            "proposal_ids": [target_id],
            "accepted_proposal_ids": [target_id],
            "autonomous_approved_proposal_ids": [],
            "pending_proposals": 0,
            "trust_stages": {"cortex": 0.94},
        })
        # Several intermediate runs
        for i in range(2, 7):
            audit_rows.append({
                "run_id": f"run-{i}",
                "ts": f"2026-02-{2+i:02d}T00:00:00+00:00",
                "proposal_ids": [target_id],
                "accepted_proposal_ids": [target_id],
                "autonomous_approved_proposal_ids": [],
                "pending_proposals": 0,
                "trust_stages": {"cortex": 0.94 - (i * 0.05)},
            })
        # First revocation recorded at run-7
        audit_rows.append({
            "run_id": "run-7",
            "ts": "2026-02-09T00:00:00+00:00",
            "proposal_ids": [target_id],
            "accepted_proposal_ids": [],
            "autonomous_approved_proposal_ids": [],
            "pending_proposals": 0,
            "trust_stages": {"cortex": 0.60},
            "feedback_revoked_ids": [target_id],
        })
        # Second cycle: re-approved after cooldown expired, accepted again
        audit_rows.append({
            "run_id": "run-30",
            "ts": "2026-03-01T00:00:00+00:00",
            "proposal_ids": [target_id],
            "accepted_proposal_ids": [],
            "autonomous_approved_proposal_ids": [target_id],
            "pending_proposals": 0,
            "trust_stages": {"cortex": 0.92},
        })
        audit_rows.append({
            "run_id": "run-31",
            "ts": "2026-03-02T00:00:00+00:00",
            "proposal_ids": [target_id],
            "accepted_proposal_ids": [target_id],
            "autonomous_approved_proposal_ids": [],
            "pending_proposals": 0,
            "trust_stages": {"cortex": 0.91},
        })
        # Runs after second acceptance where trust degrades again
        for i in range(6):
            audit_rows.append({
                "run_id": f"run-{32+i}",
                "ts": f"2026-03-{3+i:02d}T00:00:00+00:00",
                "proposal_ids": [target_id],
                "accepted_proposal_ids": [target_id],
                "autonomous_approved_proposal_ids": [],
                "pending_proposals": 0,
                "trust_stages": {"cortex": 0.91 - (i * 0.06)},
            })

        approval_ledger_path.write_text(
            json.dumps({
                "version": 1,
                "updated": "2026-03-09T00:00:00+00:00",
                "approved_proposal_ids": [target_id],
                "permanently_blocked_ids": [],
                "run_audit": audit_rows,
            }),
            encoding="utf-8",
        )

        # Setup: trust for cortex is now low enough to trigger feedback revocation
        trust_ledger_path = tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json"
        trust_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        trust_ledger_path.write_text(
            json.dumps({
                "version": 1,
                "agents": {
                    "stage:cortex": {
                        "total": 20,
                        "passed": 14,
                        "failed": 6,
                        "skipped": 0,
                        "avg_elapsed_sec": 1.0,
                        "trigger_events": 0,
                        "trigger_counts": {},
                        "last_run_id": "",
                        "last_seen": "",
                        "trust_score": 0.55,
                        "lifetime_trust_score": 0.55,
                        "dynamic_trust_score": 0.55,
                        "trust_confidence": 0.9,
                        "trust_confidence_ema": 0.9,
                        "base_blended_trust": 0.55,
                        "recent_trigger_history": [],
                        "recent_trigger_rate": 0.0,
                        "recent_trigger_load_history": [],
                        "recent_trigger_load": 0.0,
                    },
                },
            }),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["pruning"]["enabled"] = False
        auto_cfg["feedback"]["enabled"] = True
        auto_cfg["feedback"]["min_runs_after_acceptance"] = 3
        auto_cfg["feedback"]["max_trust_degradation"] = 0.10
        auto_cfg["feedback"]["escalation"]["enabled"] = True
        auto_cfg["feedback"]["escalation"]["max_revocation_cycles"] = 2

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        ledger_info = acceptance.get("approval_ledger", {})
        feedback = ledger_info.get("feedback", {})
        escalation = ledger_info.get("escalation", {})

        # Feedback should have revoked the ID (second revocation)
        assert target_id in feedback.get("revoked", {}), f"Expected feedback revoke: {feedback}"

        # Escalation should have permanently blocked it (2nd revocation = max_revocation_cycles)
        assert escalation.get("enabled") is True
        assert target_id in escalation.get("newly_blocked", {}), f"Expected escalation block: {escalation}"
        assert escalation["newly_blocked"][target_id]["total_revocations"] >= 2

        # Phase 5.0a: Verify structural diagnosis is included
        diagnosis = escalation["newly_blocked"][target_id].get("diagnosis", {})
        assert diagnosis.get("stage") == "cortex"
        assert diagnosis.get("pattern") == "structural"
        assert len(diagnosis.get("cycles", [])) >= 2
        assert "recommendation" in diagnosis

        # Verify persisted: ID in permanently_blocked_ids, NOT in approved_proposal_ids
        persisted = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
        assert target_id in persisted.get("permanently_blocked_ids", [])
        assert target_id not in persisted.get("approved_proposal_ids", [])
        assert ledger_info.get("permanently_blocked_count", 0) >= 1

    def test_self_reconfigure_permanently_blocked_stays_blocked(self, tmp_path, monkeypatch):
        """Phase 4.9: A permanently blocked ID is skipped even when it meets all approval criteria."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        blocked_id = "cortex:relax:relax_retry_limits"

        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Build audit with repeated proposals so the ID would normally qualify
        audit_rows = []
        for i in range(10):
            audit_rows.append({
                "run_id": f"run-{i}",
                "ts": f"2026-02-{10+i:02d}T00:00:00+00:00",
                "proposal_ids": [blocked_id],
                "accepted_proposal_ids": [],
                "autonomous_approved_proposal_ids": [],
                "pending_proposals": 0,
            })

        approval_ledger_path.write_text(
            json.dumps({
                "version": 1,
                "updated": "2026-02-20T00:00:00+00:00",
                "approved_proposal_ids": [],
                "permanently_blocked_ids": [blocked_id],
                "run_audit": audit_rows,
            }),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["min_repeated_proposals"] = 1
        auto_cfg["max_new_approvals_per_run"] = 1
        auto_cfg["min_trust_score"] = 0.0
        auto_cfg["min_trust_confidence_ema"] = 0.0
        auto_cfg["allow_modes"] = ["relax", "tighten"]
        auto_cfg["pruning"]["enabled"] = False
        auto_cfg["feedback"]["enabled"] = False

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        autonomous = acceptance.get("autonomous_approval", {})

        # Should be permanently blocked — not approved
        skipped = autonomous.get("skipped", {})
        assert blocked_id in skipped, f"Expected permanently_blocked skip: {autonomous}"
        assert skipped[blocked_id] == "permanently_blocked"
        assert len(autonomous.get("new_approved_proposal_ids", [])) == 0
        assert blocked_id in autonomous.get("permanently_blocked_ids", [])

        # Verify it's still in blocked list after the run
        persisted = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
        assert blocked_id in persisted.get("permanently_blocked_ids", [])
        assert blocked_id not in persisted.get("approved_proposal_ids", [])

    def test_self_reconfigure_utility_learning_scores_outcomes(self, tmp_path, monkeypatch):
        """Phase 5.3: accepted proposals accumulate observed/expected utility in ledger."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        target_id = "cortex:relax:relax_retry_limits"
        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        approval_ledger_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated": "2026-02-17T00:00:00+00:00",
                    "approved_proposal_ids": [target_id],
                    "proposal_outcomes": {},
                    "run_audit": [
                        {
                            "run_id": "accept-run",
                            "ts": "2026-02-10T00:00:00+00:00",
                            "proposal_ids": [target_id],
                            "accepted_proposal_ids": [target_id],
                            "autonomous_approved_proposal_ids": [],
                            "pending_proposals": 0,
                            "trust_stages": {"cortex": 0.80},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["min_repeated_proposals"] = 1
        auto_cfg["max_new_approvals_per_run"] = 1
        auto_cfg["min_trust_score"] = 0.0
        auto_cfg["min_trust_confidence_ema"] = 0.0
        auto_cfg["allow_modes"] = ["relax", "tighten"]
        auto_cfg["pruning"]["enabled"] = False
        auto_cfg["feedback"]["enabled"] = False
        auto_cfg["utility_learning"]["enabled"] = True
        auto_cfg["utility_learning"]["min_runs_after_acceptance"] = 1
        auto_cfg["utility_learning"]["min_observations_for_gating"] = 1

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        utility = acceptance.get("approval_ledger", {}).get("utility_learning", {})

        assert utility.get("enabled") is True
        observed = utility.get("observed_outcomes", {})
        assert target_id in observed, f"Expected observed utility outcome: {utility}"
        assert "observed_utility" in observed[target_id]
        assert "expected_utility" in observed[target_id]
        assert "confidence" in observed[target_id]

        persisted = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
        outcome_stats = persisted.get("proposal_outcomes", {}).get(target_id, {})
        assert int(outcome_stats.get("observations", 0) or 0) >= 1
        assert "avg_utility" in outcome_stats
        assert "expected_utility_confidence" in outcome_stats

    def test_self_reconfigure_utility_gate_blocks_negative_expected_utility(self, tmp_path, monkeypatch):
        """Phase 5.3: auto-approval is blocked when expected utility is persistently negative."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        target_id = "cortex:relax:relax_retry_limits"
        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        approval_ledger_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated": "2026-02-17T00:00:00+00:00",
                    "approved_proposal_ids": [],
                    "permanently_blocked_ids": [],
                    "proposal_outcomes": {
                        target_id: {
                            "stage": "cortex",
                            "observations": 4,
                            "avg_utility": -0.25,
                            "last_observed_utility": -0.30,
                            "positive_outcomes": 0,
                            "negative_outcomes": 4,
                            "neutral_outcomes": 0,
                            "expected_utility_confidence": 1.0,
                        }
                    },
                    "run_audit": [
                        {
                            "run_id": "hist-1",
                            "ts": "2026-02-10T00:00:00+00:00",
                            "proposal_ids": [target_id],
                            "accepted_proposal_ids": [],
                            "autonomous_approved_proposal_ids": [],
                            "pending_proposals": 0,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["target_stages"] = ["cortex"]
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["min_repeated_proposals"] = 1
        auto_cfg["max_new_approvals_per_run"] = 1
        auto_cfg["min_trust_score"] = 0.0
        auto_cfg["min_trust_confidence_ema"] = 0.0
        auto_cfg["allow_modes"] = ["relax", "tighten"]
        auto_cfg["pruning"]["enabled"] = False
        auto_cfg["feedback"]["enabled"] = False
        auto_cfg["utility_learning"]["enabled"] = True
        auto_cfg["utility_learning"]["min_observations_for_gating"] = 2
        auto_cfg["utility_learning"]["min_expected_utility"] = -0.05

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        autonomous = acceptance.get("autonomous_approval", {})

        assert len(autonomous.get("new_approved_proposal_ids", [])) == 0
        skipped = autonomous.get("skipped", {})
        assert skipped.get(target_id) == "negative_expected_utility", f"Expected utility gate skip: {autonomous}"

        blocked = autonomous.get("blocked_expected_utility", {})
        assert target_id in blocked
        assert blocked[target_id]["expected_utility"] < blocked[target_id]["min_expected_utility"]
        assert blocked[target_id]["confidence"] >= 1.0

    def test_self_reconfigure_exploration_allows_low_confidence_candidate(self, tmp_path, monkeypatch):
        """Phase 5.4: bounded exploration can approve low-confidence utility candidates."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        target_id = "cortex:relax:relax_retry_limits"
        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        approval_ledger_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated": "2026-02-18T00:00:00+00:00",
                    "approved_proposal_ids": [],
                    "proposal_outcomes": {
                        target_id: {
                            "stage": "cortex",
                            "observations": 1,
                            "avg_utility": 0.01,
                            "expected_utility_confidence": 0.2,
                        }
                    },
                    "run_audit": [],
                }
            ),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["target_stages"] = ["cortex"]
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["min_repeated_proposals"] = 3  # would normally block with empty audit history
        auto_cfg["max_new_approvals_per_run"] = 1
        auto_cfg["min_trust_score"] = 0.0
        auto_cfg["min_trust_confidence_ema"] = 0.0
        auto_cfg["allow_modes"] = ["relax", "tighten"]
        auto_cfg["pruning"]["enabled"] = False
        auto_cfg["feedback"]["enabled"] = False
        auto_cfg["utility_learning"]["enabled"] = True
        auto_cfg["utility_learning"]["min_observations_for_gating"] = 2
        auto_cfg["utility_learning"]["exploration"] = {
            "enabled": True,
            "max_explorations_per_run": 1,
            "max_expected_utility_confidence": 0.5,
            "min_trust_score": 0.0,
            "min_trust_confidence_ema": 0.0,
            "allow_modes": ["relax"],
        }

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        autonomous = acceptance.get("autonomous_approval", {})

        approved = autonomous.get("new_approved_proposal_ids", [])
        assert target_id in approved, f"Expected exploratory approval: {autonomous}"
        exploratory = autonomous.get("exploratory_approved", {})
        assert target_id in exploratory
        assert exploratory[target_id]["reason"] == "low_utility_confidence_exploration"
        assert autonomous.get("utility_learning", {}).get("exploration", {}).get("used") == 1

    def test_self_reconfigure_exploration_disabled_keeps_repetition_block(self, tmp_path, monkeypatch):
        """Phase 5.4: without exploration, low-confidence candidates remain repetition-blocked."""
        import orchestrator as orch

        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")
        monkeypatch.setattr(orch, "_DELEGATION_LEDGER", tmp_path / "pipeline_runs" / "_delegation_trust_ledger.json")
        monkeypatch.setattr(orch, "_SELF_RECONFIG_APPROVAL_LEDGER", tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json")

        target_id = "cortex:relax:relax_retry_limits"
        approval_ledger_path = tmp_path / "pipeline_runs" / "_self_reconfigure_approvals.json"
        approval_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        approval_ledger_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated": "2026-02-18T00:00:00+00:00",
                    "approved_proposal_ids": [],
                    "proposal_outcomes": {
                        target_id: {
                            "stage": "cortex",
                            "observations": 1,
                            "avg_utility": 0.01,
                            "expected_utility_confidence": 0.2,
                        }
                    },
                    "run_audit": [],
                }
            ),
            encoding="utf-8",
        )

        cfg = PipelineConfig(dry_run=True, verbose=False)
        runner = PipelineRunner(cfg)
        runner.adaptive_policy["self_reconfigure"]["min_stage_observations"] = 0
        runner.adaptive_policy["self_reconfigure"]["min_confidence"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["max_proposals_per_run"] = 1
        runner.adaptive_policy["self_reconfigure"]["target_stages"] = ["cortex"]
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["min_trust_score"] = 0.0
        runner.adaptive_policy["self_reconfigure"]["relax_when"]["max_trigger_rate"] = 1.0

        auto_cfg = runner.adaptive_policy["self_reconfigure"]["acceptance"]["autonomous_approval"]
        auto_cfg["enabled"] = True
        auto_cfg["min_repeated_proposals"] = 3
        auto_cfg["max_new_approvals_per_run"] = 1
        auto_cfg["min_trust_score"] = 0.0
        auto_cfg["min_trust_confidence_ema"] = 0.0
        auto_cfg["allow_modes"] = ["relax", "tighten"]
        auto_cfg["pruning"]["enabled"] = False
        auto_cfg["feedback"]["enabled"] = False
        auto_cfg["utility_learning"]["enabled"] = True
        auto_cfg["utility_learning"]["min_observations_for_gating"] = 2
        auto_cfg["utility_learning"]["exploration"] = {
            "enabled": False,
            "max_explorations_per_run": 1,
            "max_expected_utility_confidence": 0.5,
            "min_trust_score": 0.0,
            "min_trust_confidence_ema": 0.0,
            "allow_modes": ["relax"],
        }

        summary = runner.run()
        acceptance = summary.get("delegation_v1", {}).get("self_reconfigure", {}).get("acceptance", {})
        autonomous = acceptance.get("autonomous_approval", {})

        assert target_id not in autonomous.get("new_approved_proposal_ids", [])
        assert autonomous.get("skipped", {}).get(target_id) == "insufficient_repetition"
        assert autonomous.get("utility_learning", {}).get("exploration", {}).get("used") == 0

    def test_smoke_only(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")

        cfg = PipelineConfig(
            stages=["smoke", "report"],
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        summary = runner.run()

        assert summary["pipeline_verdict"] == "PASS"
        assert summary["stages_passed"] >= 1  # smoke + report
        assert "cortex" not in runner.results

    def test_skip_evolve(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")

        cfg = PipelineConfig(
            skip=["evolve"],
            dry_run=True,
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        summary = runner.run()

        assert "evolve" not in runner.results

    def test_pipeline_output_saved(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")

        cfg = PipelineConfig(
            stages=["smoke", "report"],
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        runner.run()

        run_dir = tmp_path / "pipeline_runs" / runner.run_id
        assert run_dir.exists()
        assert (run_dir / "pipeline_summary.json").exists()
        assert (run_dir / "stage_smoke.json").exists()
        assert (run_dir / "stage_report.json").exists()

    def test_pipeline_summary_json_valid(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")

        cfg = PipelineConfig(
            stages=["smoke", "report"],
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        runner.run()

        run_dir = tmp_path / "pipeline_runs" / runner.run_id
        summary = json.loads((run_dir / "pipeline_summary.json").read_text())
        assert summary["run_id"] == runner.run_id
        assert summary["core_immutability"] == "PASS"

    def test_evolve_skipped_when_no_candidates(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")

        cfg = PipelineConfig(
            stages=["smoke", "evolve", "report"],
            evolve_candidates=[],
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        summary = runner.run()

        assert runner.results["evolve"].status == "skipped"
        assert "no evolve candidates" in runner.results["evolve"].output.get("reason", "")


# ======================================================================
# Pipeline with consolidate (needs cortex result)
# ======================================================================

class TestPipelineConsolidate:
    def test_consolidate_skipped_without_cortex(self, tmp_path, monkeypatch):
        import orchestrator as orch
        monkeypatch.setattr(orch, "_PIPELINE_DIR", tmp_path / "pipeline_runs")

        cfg = PipelineConfig(
            stages=["smoke", "consolidate", "report"],
            verbose=False,
        )
        runner = PipelineRunner(cfg)
        summary = runner.run()

        assert runner.results["consolidate"].status == "skipped"
