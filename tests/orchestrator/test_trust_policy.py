"""Trust-weighted adaptive policy resolver tests (Phase 2.0)."""
from __future__ import annotations

import sys
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_ORCH_DIR = _SOL_ROOT / "tools" / "sol-orchestrator"

if str(_ORCH_DIR) not in sys.path:
    sys.path.insert(0, str(_ORCH_DIR))

from delegation_v1 import (
    default_adaptive_policy,
    evaluate_self_reconfigure_acceptance,
    evaluate_self_reconfigure_proposals,
    resolve_cortex_adaptive_plan,
    resolve_stage_adaptive_plan,
)


def test_cortex_low_trust_disables_retry():
    policy = default_adaptive_policy()
    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        trust_score=0.1,
    )
    assert plan is None


def test_cortex_high_trust_changes_adoption_rule():
    policy = default_adaptive_policy()
    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        trust_score=0.95,
    )
    assert plan is not None
    assert plan["adoption_rule"] == "always_on_success"


def test_non_cortex_low_trust_disables_retry():
    policy = default_adaptive_policy()
    plan = resolve_stage_adaptive_plan(
        stage="consolidate",
        trigger_types={"anomaly"},
        policy=policy,
        trust_score=0.2,
    )
    assert plan is None


def test_non_cortex_mid_trust_allows_retry():
    policy = default_adaptive_policy()
    plan = resolve_stage_adaptive_plan(
        stage="consolidate",
        trigger_types={"anomaly"},
        policy=policy,
        trust_score=0.6,
    )
    assert plan is not None
    assert plan["strategy"] == "retry_same_stage"


def test_adaptive_threshold_tighten_blocks_retry():
    policy = default_adaptive_policy()
    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.38, "recent_trigger_rate": 0.5},
    )
    assert plan is None


def test_adaptive_threshold_relax_allows_retry():
    policy = default_adaptive_policy()
    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.34, "recent_trigger_rate": 0.0},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("adjustment_mode") == "relax"


def test_adaptive_threshold_tighten_scales_and_caps():
    policy = default_adaptive_policy()
    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.7, "recent_trigger_rate": 0.99},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("adjustment_mode") == "tighten"
    assert trust_meta.get("threshold_adjustment") == 0.2
    assert trust_meta.get("low_threshold") == 0.55


def test_adaptive_threshold_relax_scales_and_caps():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["low_trigger_rate"] = 0.6
    adaptive_cfg["trigger_rate_step"] = 0.1
    adaptive_cfg["threshold_step"] = 0.05
    adaptive_cfg["max_adjustment"] = 0.2

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.2, "recent_trigger_rate": 0.0},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("adjustment_mode") == "relax"
    assert trust_meta.get("threshold_adjustment") == -0.2
    assert trust_meta.get("low_threshold") == 0.15


def test_adaptive_threshold_uses_trigger_load_signal():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["signal_mode"] = "max"
    adaptive_cfg["high_trigger_rate"] = 0.4
    adaptive_cfg["threshold_step"] = 0.1

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.4,
            "recent_trigger_rate": 0.0,
            "recent_trigger_load": 0.9,
        },
    )
    assert plan is None


def test_low_trust_warmup_does_not_disable_retry():
    policy = default_adaptive_policy()
    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.1, "recent_trigger_rate": 0.0, "total": 1},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("sample_guard_applied") is True


def test_low_trust_after_min_observations_disables_retry():
    policy = default_adaptive_policy()
    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.1, "recent_trigger_rate": 0.0, "total": 10},
    )
    assert plan is None


def test_adaptive_threshold_warmup_blocks_adjustment():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 5

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.34, "recent_trigger_rate": 0.0, "total": 2},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("adaptive_warmup_applied") is True
    assert trust_meta.get("adjustment_mode") == "none"


def test_adaptive_threshold_warmup_enables_after_min_observations():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 5

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.34, "recent_trigger_rate": 0.0, "total": 8},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("adaptive_warmup_applied") is False
    assert trust_meta.get("adjustment_mode") == "relax"


def test_adaptive_deadband_blocks_boundary_adjustment():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 0
    adaptive_cfg["deadband"] = 0.02
    adaptive_cfg["high_trigger_rate"] = 0.3

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.36, "recent_trigger_rate": 0.31, "total": 8},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("adjustment_mode") == "none"
    assert trust_meta.get("threshold_adjustment") == 0.0


def test_adaptive_deadband_allows_adjustment_beyond_boundary():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 0
    adaptive_cfg["ramp_observations"] = 1
    adaptive_cfg["deadband"] = 0.02
    adaptive_cfg["high_trigger_rate"] = 0.3

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.36, "recent_trigger_rate": 0.33, "total": 8},
    )
    assert plan is None


def test_adaptive_signal_ramp_blocks_early_post_warmup_adjustment():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 5
    adaptive_cfg["ramp_observations"] = 5
    adaptive_cfg["deadband"] = 0.0
    adaptive_cfg["high_trigger_rate"] = 0.3

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.36, "recent_trigger_rate": 0.9, "total": 5},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("signal_ramp_factor") == 0.2
    assert trust_meta.get("adjustment_mode") == "none"


def test_adaptive_signal_ramp_allows_late_adjustment():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 5
    adaptive_cfg["ramp_observations"] = 5
    adaptive_cfg["deadband"] = 0.0
    adaptive_cfg["high_trigger_rate"] = 0.3

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.36, "recent_trigger_rate": 0.9, "total": 9},
    )
    assert plan is None


def test_asymmetric_deadband_blocks_tighten_but_allows_relax():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 0
    adaptive_cfg["ramp_observations"] = 1
    adaptive_cfg["high_trigger_rate"] = 0.3
    adaptive_cfg["low_trigger_rate"] = 0.2
    adaptive_cfg["high_deadband"] = 0.05
    adaptive_cfg["low_deadband"] = 0.0

    # Tighten blocked: 0.33 < 0.30 + 0.05
    tighten_plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.36, "recent_trigger_rate": 0.33, "total": 10},
    )
    assert tighten_plan is not None
    tighten_meta = tighten_plan.get("trust_control", {})
    assert tighten_meta.get("adjustment_mode") == "none"

    # Relax allowed: 0.18 <= 0.20 - 0.00
    relax_plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.36, "recent_trigger_rate": 0.18, "total": 10},
    )
    assert relax_plan is not None
    relax_meta = relax_plan.get("trust_control", {})
    assert relax_meta.get("adjustment_mode") == "relax"
    assert relax_meta.get("threshold_adjustment") < 0


def test_asymmetric_deadband_metadata_exposed():
    policy = default_adaptive_policy()
    adaptive_cfg = policy["stages"]["cortex"]["trust_control"]["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 0
    adaptive_cfg["ramp_observations"] = 1
    adaptive_cfg["high_deadband"] = 0.07
    adaptive_cfg["low_deadband"] = 0.01

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={"trust_score": 0.36, "recent_trigger_rate": 0.31, "total": 10},
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("high_deadband") == 0.07
    assert trust_meta.get("low_deadband") == 0.01


def test_confidence_guard_blocks_low_trust_override():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.4

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.1,
            "trust_confidence": 0.2,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("confidence_guard_applied") is True


def test_confident_low_trust_still_applies_low_trust_override():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.4

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.1,
            "trust_confidence": 0.9,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is None


def test_low_confidence_scales_threshold_adjustment():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.0
    trust_cfg["confidence_scaling"]["min_confidence_for_low_override"] = 0.0
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.0
    trust_cfg["confidence_scaling"]["scale_threshold_adjustment"] = True
    trust_cfg["confidence_scaling"]["min_threshold_adjustment_scale"] = 0.25

    adaptive_cfg = trust_cfg["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 0
    adaptive_cfg["ramp_observations"] = 1
    adaptive_cfg["deadband"] = 0.0
    adaptive_cfg["high_trigger_rate"] = 0.3
    adaptive_cfg["threshold_step"] = 0.1
    adaptive_cfg["trigger_rate_step"] = 0.1
    adaptive_cfg["max_adjustment"] = 0.2

    stage_context = {
        "trust_score": 0.2,
        "trust_confidence": 0.2,
        "recent_trigger_rate": 0.4,
        "total": 10,
    }

    scaled_plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context=stage_context,
    )
    assert scaled_plan is not None
    scaled_meta = scaled_plan.get("trust_control", {})
    assert scaled_meta.get("adjustment_confidence_scale") == 0.25
    assert scaled_meta.get("threshold_adjustment") == 0.025

    trust_cfg["confidence_scaling"]["scale_threshold_adjustment"] = False
    unscaled_plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context=stage_context,
    )
    assert unscaled_plan is None


def test_low_confidence_trigger_signal_scaling_blocks_tighten():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.0
    trust_cfg["confidence_scaling"]["scale_trigger_signal"] = True
    trust_cfg["confidence_scaling"]["min_trigger_signal_scale"] = 0.25

    adaptive_cfg = trust_cfg["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 0
    adaptive_cfg["ramp_observations"] = 1
    adaptive_cfg["deadband"] = 0.0
    adaptive_cfg["high_trigger_rate"] = 0.3

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.36,
            "trust_confidence": 0.2,
            "recent_trigger_rate": 0.9,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("adjustment_mode") == "none"
    assert trust_meta.get("trigger_confidence_scale") == 0.25


def test_high_confidence_trigger_signal_scaling_allows_tighten():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.0
    trust_cfg["confidence_scaling"]["scale_trigger_signal"] = True
    trust_cfg["confidence_scaling"]["min_trigger_signal_scale"] = 0.25

    adaptive_cfg = trust_cfg["adaptive_thresholds"]
    adaptive_cfg["min_signal_observations"] = 0
    adaptive_cfg["ramp_observations"] = 1
    adaptive_cfg["deadband"] = 0.0
    adaptive_cfg["high_trigger_rate"] = 0.3

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.36,
            "trust_confidence": 0.9,
            "recent_trigger_rate": 0.9,
            "total": 10,
        },
    )
    assert plan is None


def test_low_confidence_scaled_min_observations_blocks_override():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 3
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.0
    trust_cfg["confidence_scaling"]["scale_min_observations"] = True
    trust_cfg["confidence_scaling"]["max_min_observations"] = 10

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.1,
            "trust_confidence": 0.2,
            "recent_trigger_rate": 0.0,
            "total": 5,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("effective_min_observations") == 9
    assert trust_meta.get("sample_guard_applied") is True


def test_high_confidence_scaled_min_observations_allows_override():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 3
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.0
    trust_cfg["confidence_scaling"]["scale_min_observations"] = True
    trust_cfg["confidence_scaling"]["max_min_observations"] = 10

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.1,
            "trust_confidence": 0.9,
            "recent_trigger_rate": 0.0,
            "total": 5,
        },
    )
    assert plan is None


def test_directional_confidence_gate_allows_low_override_but_blocks_high_override():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["min_confidence_for_low_override"] = 0.2
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.95
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.2
    trust_cfg["adaptive_thresholds"]["enabled"] = False

    low_plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.1,
            "trust_confidence": 1.0,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert low_plan is None

    high_plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.98,
            "trust_confidence": 0.4,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert high_plan is not None
    trust_meta = high_plan.get("trust_control", {})
    assert trust_meta.get("high_confidence_guard_applied") is True
    assert high_plan.get("adoption_rule") == "higher_protocols_run"


def test_directional_confidence_gate_allows_high_override_when_confident():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["min_confidence_for_low_override"] = 0.2
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.95
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.2

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.98,
            "trust_confidence": 0.98,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("high_confidence_guard_applied") is False
    assert plan.get("adoption_rule") == "always_on_success"


def test_confidence_source_ema_blocks_high_override_when_ema_low():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "ema"
    trust_cfg["confidence_scaling"]["min_confidence_for_low_override"] = 0.2
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.9
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.2
    trust_cfg["adaptive_thresholds"]["enabled"] = False

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.98,
            "trust_confidence": 0.98,
            "trust_confidence_ema": 0.4,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("confidence_source") == "ema"
    assert trust_meta.get("control_confidence") == 0.4
    assert trust_meta.get("high_confidence_guard_applied") is True
    assert plan.get("adoption_rule") == "higher_protocols_run"


def test_confidence_source_ema_allows_high_override_when_ema_high():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "ema"
    trust_cfg["confidence_scaling"]["min_confidence_for_low_override"] = 0.2
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.9
    trust_cfg["confidence_scaling"]["min_confidence_for_override"] = 0.2
    trust_cfg["adaptive_thresholds"]["enabled"] = False

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.98,
            "trust_confidence": 0.2,
            "trust_confidence_ema": 0.95,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("confidence_source") == "ema"
    assert trust_meta.get("control_confidence") == 0.95
    assert trust_meta.get("high_confidence_guard_applied") is False
    assert plan.get("adoption_rule") == "always_on_success"


def test_high_override_blocked_by_confidence_drop_guard():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["adaptive_thresholds"]["enabled"] = False
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "raw"
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.3
    trust_cfg["confidence_scaling"]["guard_high_on_confidence_drop"] = True
    trust_cfg["confidence_scaling"]["max_confidence_drop_for_high_override"] = 0.2

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.98,
            "trust_confidence": 0.7,
            "trust_confidence_ema": 0.95,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("high_confidence_drop_guard_applied") is True
    assert trust_meta.get("confidence_drop") == 0.25
    assert plan.get("adoption_rule") == "higher_protocols_run"


def test_high_override_allowed_when_confidence_drop_within_limit():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["adaptive_thresholds"]["enabled"] = False
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "raw"
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.3
    trust_cfg["confidence_scaling"]["guard_high_on_confidence_drop"] = True
    trust_cfg["confidence_scaling"]["max_confidence_drop_for_high_override"] = 0.2

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 1.0,
            "trust_confidence": 0.8,
            "trust_confidence_ema": 0.95,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("high_confidence_drop_guard_applied") is False
    assert trust_meta.get("confidence_drop") == 0.15
    assert plan.get("adoption_rule") == "always_on_success"


def test_low_override_blocked_by_confidence_recovery_guard():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["adaptive_thresholds"]["enabled"] = False
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "raw"
    trust_cfg["confidence_scaling"]["min_confidence_for_low_override"] = 0.0
    trust_cfg["confidence_scaling"]["guard_low_on_confidence_recovery"] = True
    trust_cfg["confidence_scaling"]["min_confidence_recovery_for_low_override"] = 0.2

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.1,
            "trust_confidence": 0.95,
            "trust_confidence_ema": 0.6,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("low_confidence_recovery_guard_applied") is True
    assert trust_meta.get("confidence_recovery") == 0.35
    assert plan.get("adoption_rule") == "higher_protocols_run"


def test_low_override_allowed_when_confidence_recovery_within_limit():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["adaptive_thresholds"]["enabled"] = False
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "raw"
    trust_cfg["confidence_scaling"]["min_confidence_for_low_override"] = 0.0
    trust_cfg["confidence_scaling"]["guard_low_on_confidence_recovery"] = True
    trust_cfg["confidence_scaling"]["min_confidence_recovery_for_low_override"] = 0.2

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"sanity_fail"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 0.1,
            "trust_confidence": 0.75,
            "trust_confidence_ema": 0.6,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is None


def test_high_override_blocked_by_confidence_volatility_guard():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["adaptive_thresholds"]["enabled"] = False
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "raw"
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.0
    trust_cfg["confidence_scaling"]["guard_overrides_on_confidence_volatility"] = True
    trust_cfg["confidence_scaling"]["max_confidence_volatility_for_overrides"] = 0.25

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 1.0,
            "trust_confidence": 0.95,
            "trust_confidence_ema": 0.6,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("confidence_volatility_guard_applied") is True
    assert trust_meta.get("confidence_volatility") == 0.35
    assert plan.get("adoption_rule") == "higher_protocols_run"


def test_high_override_allowed_when_confidence_volatility_within_limit():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["adaptive_thresholds"]["enabled"] = False
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "raw"
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.0
    trust_cfg["confidence_scaling"]["guard_overrides_on_confidence_volatility"] = True
    trust_cfg["confidence_scaling"]["max_confidence_volatility_for_overrides"] = 0.25

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 1.0,
            "trust_confidence": 0.85,
            "trust_confidence_ema": 0.7,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("confidence_volatility_guard_applied") is False
    assert trust_meta.get("confidence_volatility") == 0.15
    assert plan.get("adoption_rule") == "always_on_success"


def test_high_override_blocked_by_effective_trust_consensus_guard():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["adaptive_thresholds"]["enabled"] = False
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "raw"
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.0
    trust_cfg["confidence_scaling"]["guard_overrides_on_confidence_volatility"] = False
    trust_cfg["confidence_scaling"]["require_consensus_for_overrides"] = True
    trust_cfg["confidence_scaling"]["max_effective_trust_disagreement_for_overrides"] = 0.15

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 1.0,
            "trust_confidence": 0.95,
            "trust_confidence_ema": 0.6,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("consensus_guard_applied") is True
    assert trust_meta.get("effective_trust_disagreement") == 0.175
    assert plan.get("adoption_rule") == "higher_protocols_run"


def test_high_override_allowed_when_effective_trust_consensus_within_limit():
    policy = default_adaptive_policy()
    trust_cfg = policy["stages"]["cortex"]["trust_control"]
    trust_cfg["min_observations_for_override"] = 0
    trust_cfg["adaptive_thresholds"]["enabled"] = False
    trust_cfg["confidence_scaling"]["enabled"] = True
    trust_cfg["confidence_scaling"]["confidence_source"] = "raw"
    trust_cfg["confidence_scaling"]["min_confidence_for_high_override"] = 0.0
    trust_cfg["confidence_scaling"]["guard_overrides_on_confidence_volatility"] = False
    trust_cfg["confidence_scaling"]["require_consensus_for_overrides"] = True
    trust_cfg["confidence_scaling"]["max_effective_trust_disagreement_for_overrides"] = 0.15

    plan = resolve_cortex_adaptive_plan(
        trigger_types={"velocity_drop"},
        base_config={"cortex_max_protocols": 3, "cortex_max_steps": 1000},
        policy=policy,
        stage_context={
            "trust_score": 1.0,
            "trust_confidence": 0.9,
            "trust_confidence_ema": 0.7,
            "recent_trigger_rate": 0.0,
            "total": 10,
        },
    )
    assert plan is not None
    trust_meta = plan.get("trust_control", {})
    assert trust_meta.get("consensus_guard_applied") is False
    assert trust_meta.get("effective_trust_disagreement") == 0.1
    assert plan.get("adoption_rule") == "always_on_success"


def test_self_reconfigure_proposes_tighten_for_low_trust_high_trigger_stage():
    policy = default_adaptive_policy()
    snapshot = {
        "agents": {
            "stage:cortex": {
                "total": 12,
                "trust_score": 0.3,
                "recent_trigger_rate": 0.5,
                "trust_confidence_ema": 0.8,
            }
        }
    }

    result = evaluate_self_reconfigure_proposals(policy=policy, trust_snapshot=snapshot)
    assert result.get("enabled") is True
    assert result.get("proposal_only") is True
    proposals = result.get("proposals", [])
    assert len(proposals) == 1
    assert proposals[0].get("proposal_id") == "cortex:tighten:tighten_retry_limits"
    assert proposals[0].get("stage") == "cortex"
    assert proposals[0].get("mode") == "tighten"


def test_self_reconfigure_proposes_relax_for_high_trust_low_trigger_stage():
    policy = default_adaptive_policy()
    snapshot = {
        "agents": {
            "stage:hippocampus": {
                "total": 15,
                "trust_score": 0.95,
                "recent_trigger_rate": 0.01,
                "trust_confidence_ema": 0.9,
            }
        }
    }

    result = evaluate_self_reconfigure_proposals(policy=policy, trust_snapshot=snapshot)
    proposals = result.get("proposals", [])
    assert len(proposals) == 1
    assert proposals[0].get("stage") == "hippocampus"
    assert proposals[0].get("mode") == "relax"


def test_self_reconfigure_trend_gate_blocks_relax_during_declining_trust():
    """Phase 5.1: relax proposal suppressed when audit shows declining trust trend."""
    policy = default_adaptive_policy()
    # Ensure trend gating is enabled with low bar so our 5-entry audit qualifies
    policy["self_reconfigure"]["trend_gating"] = {
        "enabled": True,
        "min_trend_observations": 3,
        "min_trend_consistency": 0.6,
    }
    # Snapshot qualifies hippocampus for relax (high trust, low trigger rate)
    snapshot = {
        "agents": {
            "stage:hippocampus": {
                "total": 15,
                "trust_score": 0.95,
                "recent_trigger_rate": 0.01,
                "trust_confidence_ema": 0.9,
            }
        }
    }
    # Audit shows declining trust for hippocampus (each run lower)
    run_audit = [
        {"trust_stages": {"hippocampus": 0.98}},
        {"trust_stages": {"hippocampus": 0.96}},
        {"trust_stages": {"hippocampus": 0.93}},
        {"trust_stages": {"hippocampus": 0.90}},
        {"trust_stages": {"hippocampus": 0.87}},
    ]

    result = evaluate_self_reconfigure_proposals(
        policy=policy, trust_snapshot=snapshot, run_audit=run_audit,
    )
    # Relax should be suppressed because trust is declining
    assert result.get("proposals", []) == []
    # Trend metadata should still be present
    tg = result.get("trend_gating", {})
    assert tg.get("enabled") is True
    trends = tg.get("stage_trends", {})
    assert "hippocampus" in trends
    assert trends["hippocampus"]["direction"] == "declining"
    assert trends["hippocampus"]["sufficient"] is True


def test_self_reconfigure_trend_gate_allows_relax_during_improving_trust():
    """Phase 5.1: relax proposal emitted when audit shows improving trust trend."""
    policy = default_adaptive_policy()
    policy["self_reconfigure"]["trend_gating"] = {
        "enabled": True,
        "min_trend_observations": 3,
        "min_trend_consistency": 0.6,
    }
    snapshot = {
        "agents": {
            "stage:hippocampus": {
                "total": 15,
                "trust_score": 0.95,
                "recent_trigger_rate": 0.01,
                "trust_confidence_ema": 0.9,
            }
        }
    }
    # Audit shows improving trust for hippocampus (each run higher)
    run_audit = [
        {"trust_stages": {"hippocampus": 0.85}},
        {"trust_stages": {"hippocampus": 0.88}},
        {"trust_stages": {"hippocampus": 0.91}},
        {"trust_stages": {"hippocampus": 0.93}},
        {"trust_stages": {"hippocampus": 0.95}},
    ]

    result = evaluate_self_reconfigure_proposals(
        policy=policy, trust_snapshot=snapshot, run_audit=run_audit,
    )
    proposals = result.get("proposals", [])
    assert len(proposals) == 1
    assert proposals[0]["stage"] == "hippocampus"
    assert proposals[0]["mode"] == "relax"
    # Trend metadata attached to proposal
    trend = proposals[0].get("trend", {})
    assert trend["direction"] == "improving"
    assert trend["sufficient"] is True
    assert trend["observations"] >= 3
    # trend_gating section in result
    tg = result.get("trend_gating", {})
    assert tg["enabled"] is True
    assert tg["stage_trends"]["hippocampus"]["direction"] == "improving"


def test_self_reconfigure_no_proposal_when_confidence_below_gate():
    policy = default_adaptive_policy()
    snapshot = {
        "agents": {
            "stage:cortex": {
                "total": 20,
                "trust_score": 0.2,
                "recent_trigger_rate": 0.9,
                "trust_confidence_ema": 0.2,
            }
        }
    }

    result = evaluate_self_reconfigure_proposals(policy=policy, trust_snapshot=snapshot)
    assert result.get("proposals", []) == []


def test_self_reconfigure_acceptance_requires_explicit_approval():
    policy = default_adaptive_policy()
    snapshot = {
        "agents": {
            "stage:cortex": {
                "total": 12,
                "trust_score": 0.3,
                "recent_trigger_rate": 0.5,
                "trust_confidence_ema": 0.8,
            }
        }
    }
    proposals = evaluate_self_reconfigure_proposals(policy=policy, trust_snapshot=snapshot)

    acceptance = evaluate_self_reconfigure_acceptance(policy=policy, self_reconfigure=proposals)
    assert acceptance.get("require_explicit_approval") is True
    assert acceptance.get("accepted_proposals") == []
    assert acceptance.get("auto_apply_enabled") is False


def test_self_reconfigure_accepts_only_approved_proposal_ids():
    policy = default_adaptive_policy()
    policy["self_reconfigure"]["acceptance"]["approved_proposal_ids"] = ["cortex:tighten:tighten_retry_limits"]

    snapshot = {
        "agents": {
            "stage:cortex": {
                "total": 12,
                "trust_score": 0.3,
                "recent_trigger_rate": 0.5,
                "trust_confidence_ema": 0.8,
            }
        }
    }
    proposals = evaluate_self_reconfigure_proposals(policy=policy, trust_snapshot=snapshot)
    acceptance = evaluate_self_reconfigure_acceptance(policy=policy, self_reconfigure=proposals)

    accepted = acceptance.get("accepted_proposals", [])
    assert len(accepted) == 1
    assert accepted[0].get("proposal_id") == "cortex:tighten:tighten_retry_limits"
    assert accepted[0].get("accepted") is True
    assert accepted[0].get("apply_now") is False


def test_self_reconfigure_accepts_approval_ids_from_ledger():
    policy = default_adaptive_policy()
    policy["self_reconfigure"]["acceptance"]["approved_proposal_ids"] = []

    snapshot = {
        "agents": {
            "stage:cortex": {
                "total": 12,
                "trust_score": 0.3,
                "recent_trigger_rate": 0.5,
                "trust_confidence_ema": 0.8,
            }
        }
    }
    proposals = evaluate_self_reconfigure_proposals(policy=policy, trust_snapshot=snapshot)
    acceptance = evaluate_self_reconfigure_acceptance(
        policy=policy,
        self_reconfigure=proposals,
        approval_ledger_ids=["cortex:tighten:tighten_retry_limits"],
    )

    accepted = acceptance.get("accepted_proposals", [])
    assert len(accepted) == 1
    assert acceptance.get("approved_proposal_ids_policy") == []
    assert acceptance.get("approved_proposal_ids_ledger") == ["cortex:tighten:tighten_retry_limits"]


def test_self_reconfigure_can_disable_ledger_ids_source():
    policy = default_adaptive_policy()
    acceptance_cfg = policy["self_reconfigure"]["acceptance"]
    acceptance_cfg["approved_proposal_ids"] = []
    acceptance_cfg["use_approval_ledger_ids"] = False

    snapshot = {
        "agents": {
            "stage:cortex": {
                "total": 12,
                "trust_score": 0.3,
                "recent_trigger_rate": 0.5,
                "trust_confidence_ema": 0.8,
            }
        }
    }
    proposals = evaluate_self_reconfigure_proposals(policy=policy, trust_snapshot=snapshot)
    acceptance = evaluate_self_reconfigure_acceptance(
        policy=policy,
        self_reconfigure=proposals,
        approval_ledger_ids=["cortex:tighten:tighten_retry_limits"],
    )

    assert acceptance.get("accepted_proposals", []) == []
    assert acceptance.get("approved_proposal_ids_ledger") == []
