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
