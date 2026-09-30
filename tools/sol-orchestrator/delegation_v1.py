#!/usr/bin/env python3
"""
Delegation V1 primitives for SOL Orchestrator.

Implements a minimal, local-first subset of intelligent delegation:
  1) Contract-first task specification per stage
  2) Runtime trigger detection for adaptive coordination
  3) Lightweight trust ledger for stage reliability tracking
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge overlay dict into base dict (overlay wins)."""
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_adaptive_policy() -> dict[str, Any]:
    """Default policy for Phase 1.2 adaptive coordination."""
    return {
        "version": "1.0",
        "enabled": True,
        "self_reconfigure": {
            "enabled": True,
            "proposal_only": True,
            "max_proposals_per_run": 2,
            "target_stages": ["cortex", "consolidate", "hippocampus", "evolve"],
            "min_stage_observations": 6,
            "min_confidence": 0.6,
            "acceptance": {
                "enabled": True,
                "require_explicit_approval": True,
                "approved_proposal_ids": [],
                "max_acceptances_per_run": 1,
                "use_approval_ledger_ids": True,
                "merge_policy_and_ledger_ids": True,
                "autonomous_approval": {
                    "enabled": True,
                    "lookback_runs": 40,
                    "min_repeated_proposals": 3,
                    "max_new_approvals_per_run": 1,
                    "min_trust_score": 0.9,
                    "min_trust_confidence_ema": 0.85,
                    "allow_modes": ["relax"],
                    "pruning": {
                        "enabled": True,
                        "max_approved_ids": 50,
                        "expire_unused_after_runs": 60,
                        "expire_after_acceptance_runs": 30,
                    },
                    "feedback": {
                        "enabled": True,
                        "min_runs_after_acceptance": 5,
                        "max_trust_degradation": 0.15,
                        "max_revocations_per_run": 1,
                        "cooldown_runs_after_revocation": 20,
                        "escalation": {
                            "enabled": True,
                            "max_revocation_cycles": 2,
                        },
                    },
                    "utility_learning": {
                        "enabled": True,
                        "min_runs_after_acceptance": 5,
                        "min_observations_for_gating": 2,
                        "min_expected_utility": -0.02,
                        "lookback_acceptance_events": 20,
                        "exploration": {
                            "enabled": True,
                            "max_explorations_per_run": 1,
                            "max_expected_utility_confidence": 0.5,
                            "min_trust_score": 0.9,
                            "min_trust_confidence_ema": 0.85,
                            "allow_modes": ["relax"],
                        },
                    },
                },
            },
            "tighten_when": {
                "max_trust_score": 0.45,
                "min_trigger_rate": 0.25,
                "recommended_change": "tighten_retry_limits",
            },
            "relax_when": {
                "min_trust_score": 0.9,
                "max_trigger_rate": 0.05,
                "recommended_change": "relax_retry_limits",
            },
            "trend_gating": {
                "enabled": True,
                "min_trend_observations": 5,
                "min_trend_consistency": 0.6,
            },
        },
        "trust_dynamics": {
            "default": {
                "alpha": 0.25,
                "success_gain": 1.0,
                "failure_penalty": 1.0,
                "min_score": 0.0,
                "max_score": 1.0,
                "history_window": 20,
                "dynamic_weight": 0.65,
                "lifetime_weight": 0.35,
                "confidence_k": 5.0,
                "confidence_ema_alpha": 0.3,
                "neutral_score": 0.5,
                "trigger_type_weights": {
                    "sanity_fail": 1.0,
                    "anomaly": 0.8,
                    "velocity_drop": 0.6,
                    "resource_overrun": 0.4,
                },
            },
            "stages": {
                "cortex": {
                    "alpha": 0.35,
                    "failure_penalty": 1.2,
                    "success_gain": 1.0,
                    "history_window": 20,
                },
                "consolidate": {
                    "alpha": 0.25,
                    "failure_penalty": 1.05,
                    "success_gain": 1.0,
                    "history_window": 12,
                },
                "hippocampus": {
                    "alpha": 0.2,
                    "failure_penalty": 1.0,
                    "success_gain": 1.05,
                    "history_window": 30,
                },
                "evolve": {
                    "alpha": 0.3,
                    "failure_penalty": 1.15,
                    "success_gain": 1.0,
                    "history_window": 15,
                },
            },
        },
        "stages": {
            "cortex": {
                "enabled": True,
                "max_retries_per_stage": 1,
                "trigger_priority": ["sanity_fail", "velocity_drop"],
                "adoption_rule": "higher_protocols_run",
                "trust_control": {
                    "enabled": True,
                    "min_observations_for_override": 3,
                    "low_trust_threshold": 0.35,
                    "high_trust_threshold": 0.9,
                    "confidence_scaling": {
                        "enabled": True,
                        "neutral_trust": 0.5,
                        "confidence_source": "raw",
                        "min_confidence_for_override": 0.3,
                        "min_confidence_for_low_override": 0.3,
                        "min_confidence_for_high_override": 0.3,
                        "guard_low_on_confidence_recovery": False,
                        "min_confidence_recovery_for_low_override": 0.2,
                        "guard_high_on_confidence_drop": False,
                        "max_confidence_drop_for_high_override": 0.2,
                        "guard_overrides_on_confidence_volatility": False,
                        "max_confidence_volatility_for_overrides": 0.25,
                        "require_consensus_for_overrides": False,
                        "max_effective_trust_disagreement_for_overrides": 0.15,
                        "scale_threshold_adjustment": True,
                        "min_threshold_adjustment_scale": 0.25,
                        "scale_trigger_signal": False,
                        "min_trigger_signal_scale": 0.25,
                        "scale_min_observations": False,
                        "max_min_observations": 10,
                    },
                    "adaptive_thresholds": {
                        "enabled": True,
                        "signal_mode": "max",
                        "min_signal_observations": 5,
                        "ramp_observations": 5,
                        "deadband": 0.02,
                        "high_deadband": 0.02,
                        "low_deadband": 0.02,
                        "high_trigger_rate": 0.3,
                        "low_trigger_rate": 0.05,
                        "trigger_rate_step": 0.1,
                        "threshold_step": 0.05,
                        "max_adjustment": 0.2,
                    },
                    "low_trust": {
                        "max_retries_per_stage": 0,
                        "adoption_rule": "success_replaces_failure",
                    },
                    "high_trust": {
                        "max_retries_per_stage": 1,
                        "adoption_rule": "always_on_success",
                    },
                },
                "plans": {
                    "sanity_fail": {
                        "enabled": True,
                        "retry_gap_type": "replication",
                        "retry_max_protocols": 1,
                        "retry_max_steps_cap": 800,
                    },
                    "velocity_drop": {
                        "enabled": True,
                        "retry_gap_type": None,
                        "retry_max_protocols_min": 2,
                        "retry_max_steps_cap": None,
                    },
                },
            },
            "consolidate": {
                "enabled": True,
                "max_retries_per_stage": 1,
                "trigger_priority": ["anomaly"],
                "adoption_rule": "success_replaces_failure",
                "trust_control": {
                    "enabled": True,
                    "min_observations_for_override": 3,
                    "low_trust_threshold": 0.35,
                    "high_trust_threshold": 0.9,
                    "confidence_scaling": {
                        "enabled": True,
                        "neutral_trust": 0.5,
                        "confidence_source": "raw",
                        "min_confidence_for_override": 0.3,
                        "min_confidence_for_low_override": 0.3,
                        "min_confidence_for_high_override": 0.3,
                        "guard_low_on_confidence_recovery": False,
                        "min_confidence_recovery_for_low_override": 0.2,
                        "guard_high_on_confidence_drop": False,
                        "max_confidence_drop_for_high_override": 0.2,
                        "guard_overrides_on_confidence_volatility": False,
                        "max_confidence_volatility_for_overrides": 0.25,
                        "require_consensus_for_overrides": False,
                        "max_effective_trust_disagreement_for_overrides": 0.15,
                        "scale_threshold_adjustment": True,
                        "min_threshold_adjustment_scale": 0.25,
                        "scale_trigger_signal": False,
                        "min_trigger_signal_scale": 0.25,
                        "scale_min_observations": False,
                        "max_min_observations": 10,
                    },
                    "adaptive_thresholds": {
                        "enabled": True,
                        "signal_mode": "max",
                        "min_signal_observations": 5,
                        "ramp_observations": 5,
                        "deadband": 0.02,
                        "high_deadband": 0.02,
                        "low_deadband": 0.02,
                        "high_trigger_rate": 0.35,
                        "low_trigger_rate": 0.05,
                        "trigger_rate_step": 0.1,
                        "threshold_step": 0.03,
                        "max_adjustment": 0.15,
                    },
                    "low_trust": {
                        "max_retries_per_stage": 0,
                    },
                },
                "plans": {
                    "anomaly": {
                        "enabled": True,
                        "strategy": "retry_same_stage",
                    }
                },
            },
            "hippocampus": {
                "enabled": True,
                "max_retries_per_stage": 1,
                "trigger_priority": ["anomaly"],
                "adoption_rule": "success_replaces_failure",
                "trust_control": {
                    "enabled": True,
                    "min_observations_for_override": 3,
                    "low_trust_threshold": 0.35,
                    "high_trust_threshold": 0.9,
                    "confidence_scaling": {
                        "enabled": True,
                        "neutral_trust": 0.5,
                        "confidence_source": "raw",
                        "min_confidence_for_override": 0.3,
                        "min_confidence_for_low_override": 0.3,
                        "min_confidence_for_high_override": 0.3,
                        "guard_low_on_confidence_recovery": False,
                        "min_confidence_recovery_for_low_override": 0.2,
                        "guard_high_on_confidence_drop": False,
                        "max_confidence_drop_for_high_override": 0.2,
                        "guard_overrides_on_confidence_volatility": False,
                        "max_confidence_volatility_for_overrides": 0.25,
                        "require_consensus_for_overrides": False,
                        "max_effective_trust_disagreement_for_overrides": 0.15,
                        "scale_threshold_adjustment": True,
                        "min_threshold_adjustment_scale": 0.25,
                        "scale_trigger_signal": False,
                        "min_trigger_signal_scale": 0.25,
                        "scale_min_observations": False,
                        "max_min_observations": 10,
                    },
                    "adaptive_thresholds": {
                        "enabled": True,
                        "signal_mode": "max",
                        "min_signal_observations": 5,
                        "ramp_observations": 5,
                        "deadband": 0.02,
                        "high_deadband": 0.02,
                        "low_deadband": 0.02,
                        "high_trigger_rate": 0.35,
                        "low_trigger_rate": 0.05,
                        "trigger_rate_step": 0.1,
                        "threshold_step": 0.03,
                        "max_adjustment": 0.15,
                    },
                    "low_trust": {
                        "max_retries_per_stage": 0,
                    },
                },
                "plans": {
                    "anomaly": {
                        "enabled": True,
                        "strategy": "retry_same_stage",
                    }
                },
            },
            "evolve": {
                "enabled": True,
                "max_retries_per_stage": 1,
                "trigger_priority": ["anomaly"],
                "adoption_rule": "success_replaces_failure",
                "trust_control": {
                    "enabled": True,
                    "min_observations_for_override": 3,
                    "low_trust_threshold": 0.35,
                    "high_trust_threshold": 0.9,
                    "confidence_scaling": {
                        "enabled": True,
                        "neutral_trust": 0.5,
                        "confidence_source": "raw",
                        "min_confidence_for_override": 0.3,
                        "min_confidence_for_low_override": 0.3,
                        "min_confidence_for_high_override": 0.3,
                        "guard_low_on_confidence_recovery": False,
                        "min_confidence_recovery_for_low_override": 0.2,
                        "guard_high_on_confidence_drop": False,
                        "max_confidence_drop_for_high_override": 0.2,
                        "guard_overrides_on_confidence_volatility": False,
                        "max_confidence_volatility_for_overrides": 0.25,
                        "require_consensus_for_overrides": False,
                        "max_effective_trust_disagreement_for_overrides": 0.15,
                        "scale_threshold_adjustment": True,
                        "min_threshold_adjustment_scale": 0.25,
                        "scale_trigger_signal": False,
                        "min_trigger_signal_scale": 0.25,
                        "scale_min_observations": False,
                        "max_min_observations": 10,
                    },
                    "adaptive_thresholds": {
                        "enabled": True,
                        "signal_mode": "max",
                        "min_signal_observations": 5,
                        "ramp_observations": 5,
                        "deadband": 0.02,
                        "high_deadband": 0.02,
                        "low_deadband": 0.02,
                        "high_trigger_rate": 0.35,
                        "low_trigger_rate": 0.05,
                        "trigger_rate_step": 0.1,
                        "threshold_step": 0.03,
                        "max_adjustment": 0.15,
                    },
                    "low_trust": {
                        "max_retries_per_stage": 0,
                    },
                },
                "plans": {
                    "anomaly": {
                        "enabled": True,
                        "strategy": "retry_same_stage",
                    }
                },
            },
        },
    }


def load_adaptive_policy(path: Path) -> dict[str, Any]:
    """Load adaptive policy from JSON path, merged over defaults."""
    base = default_adaptive_policy()
    if path.exists():
        try:
            overlay = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(overlay, dict):
                return _merge_dicts(base, overlay)
        except (json.JSONDecodeError, OSError):
            pass
    return base


def resolve_cortex_adaptive_plan(
    trigger_types: set[str],
    base_config: dict[str, Any],
    policy: dict[str, Any],
    trust_score: float = 0.5,
    stage_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve a policy-driven adaptive retry plan for cortex, if any."""
    if not policy.get("enabled", True):
        return None

    stage_policy = policy.get("stages", {}).get("cortex", {})
    context = stage_context or {}
    if "trust_score" not in context:
        context["trust_score"] = trust_score
    stage_policy, trust_meta = _apply_trust_control(stage_policy, context)
    if not stage_policy.get("enabled", True):
        return None

    if int(stage_policy.get("max_retries_per_stage", 1) or 0) <= 0:
        return None

    priority = stage_policy.get("trigger_priority", ["sanity_fail", "velocity_drop"])
    plans = stage_policy.get("plans", {})
    selected_trigger = None
    for candidate in priority:
        if candidate in trigger_types:
            selected_trigger = candidate
            break

    if not selected_trigger:
        return None

    selected_plan = plans.get(selected_trigger, {})
    if not selected_plan.get("enabled", True):
        return None

    current_protocols = int(base_config.get("cortex_max_protocols", 3) or 3)
    current_max_steps = base_config.get("cortex_max_steps")

    if selected_plan.get("retry_max_protocols") is not None:
        retry_max_protocols = int(selected_plan.get("retry_max_protocols") or current_protocols)
    else:
        retry_max_protocols = max(
            int(selected_plan.get("retry_max_protocols_min", current_protocols) or current_protocols),
            current_protocols,
        )

    retry_max_steps = selected_plan.get("retry_max_steps", current_max_steps)
    retry_max_steps_cap = selected_plan.get("retry_max_steps_cap")
    if retry_max_steps_cap is not None:
        base_steps = retry_max_steps if retry_max_steps is not None else retry_max_steps_cap
        retry_max_steps = min(int(base_steps), int(retry_max_steps_cap))

    return {
        "reason": selected_trigger,
        "retry_gap_type": selected_plan.get("retry_gap_type"),
        "retry_max_protocols": retry_max_protocols,
        "retry_max_steps": retry_max_steps,
        "adoption_rule": stage_policy.get("adoption_rule", "higher_protocols_run"),
        "policy_version": policy.get("version", "unknown"),
        "trust_score": round(float(context.get("trust_score", trust_score)), 3),
        "trust_control": trust_meta,
    }


def resolve_stage_adaptive_plan(
    stage: str,
    trigger_types: set[str],
    policy: dict[str, Any],
    trust_score: float = 0.5,
    stage_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve policy-driven adaptive plan for non-cortex stages."""
    if stage == "cortex":
        return None

    if not policy.get("enabled", True):
        return None

    stage_policy = policy.get("stages", {}).get(stage, {})
    context = stage_context or {}
    if "trust_score" not in context:
        context["trust_score"] = trust_score
    stage_policy, trust_meta = _apply_trust_control(stage_policy, context)
    if not stage_policy.get("enabled", False):
        return None

    if int(stage_policy.get("max_retries_per_stage", 1) or 0) <= 0:
        return None

    priority = stage_policy.get("trigger_priority", ["anomaly"])
    plans = stage_policy.get("plans", {})
    selected_trigger = None
    for candidate in priority:
        if candidate in trigger_types:
            selected_trigger = candidate
            break

    if not selected_trigger:
        return None

    selected_plan = plans.get(selected_trigger, {})
    if not selected_plan.get("enabled", True):
        return None

    return {
        "reason": selected_trigger,
        "strategy": selected_plan.get("strategy", "retry_same_stage"),
        "adoption_rule": stage_policy.get("adoption_rule", "success_replaces_failure"),
        "policy_version": policy.get("version", "unknown"),
        "trust_score": round(float(context.get("trust_score", trust_score)), 3),
        "trust_control": trust_meta,
    }


def evaluate_self_reconfigure_proposals(
    policy: dict[str, Any],
    trust_snapshot: dict[str, Any],
    run_audit: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate proposal-only self-reconfiguration suggestions from trust telemetry."""
    cfg = policy.get("self_reconfigure", {}) if isinstance(policy, dict) else {}
    enabled = isinstance(cfg, dict) and bool(cfg.get("enabled", False))
    proposal_only = bool(cfg.get("proposal_only", True)) if isinstance(cfg, dict) else True

    if not enabled:
        return {
            "enabled": False,
            "proposal_only": proposal_only,
            "evaluated_stages": 0,
            "proposals": [],
        }

    max_proposals_per_run_raw = cfg.get("max_proposals_per_run", 2)
    max_proposals_per_run = int(2 if max_proposals_per_run_raw is None else max_proposals_per_run_raw)
    if max_proposals_per_run < 0:
        max_proposals_per_run = 0

    min_stage_observations_raw = cfg.get("min_stage_observations", 6)
    min_stage_observations = int(6 if min_stage_observations_raw is None else min_stage_observations_raw)
    if min_stage_observations < 0:
        min_stage_observations = 0

    min_confidence_raw = cfg.get("min_confidence", 0.6)
    min_confidence = float(0.6 if min_confidence_raw is None else min_confidence_raw)
    min_confidence = max(0.0, min(1.0, min_confidence))

    tighten_when = cfg.get("tighten_when", {}) if isinstance(cfg, dict) else {}
    tighten_max_trust_raw = tighten_when.get("max_trust_score", 0.45)
    tighten_max_trust = float(0.45 if tighten_max_trust_raw is None else tighten_max_trust_raw)
    tighten_min_trigger_rate_raw = tighten_when.get("min_trigger_rate", 0.25)
    tighten_min_trigger_rate = float(0.25 if tighten_min_trigger_rate_raw is None else tighten_min_trigger_rate_raw)
    tighten_recommended_change = str(tighten_when.get("recommended_change", "tighten_retry_limits") or "tighten_retry_limits")

    relax_when = cfg.get("relax_when", {}) if isinstance(cfg, dict) else {}
    relax_min_trust_raw = relax_when.get("min_trust_score", 0.9)
    relax_min_trust = float(0.9 if relax_min_trust_raw is None else relax_min_trust_raw)
    relax_max_trigger_rate_raw = relax_when.get("max_trigger_rate", 0.05)
    relax_max_trigger_rate = float(0.05 if relax_max_trigger_rate_raw is None else relax_max_trigger_rate_raw)
    relax_recommended_change = str(relax_when.get("recommended_change", "relax_retry_limits") or "relax_retry_limits")

    # Phase 5.1: Trend gating config
    trend_cfg = cfg.get("trend_gating", {}) if isinstance(cfg, dict) else {}
    trend_enabled = isinstance(trend_cfg, dict) and bool(trend_cfg.get("enabled", False))
    trend_min_obs_raw = trend_cfg.get("min_trend_observations", 5) if isinstance(trend_cfg, dict) else 5
    trend_min_obs = int(5 if trend_min_obs_raw is None else trend_min_obs_raw)
    if trend_min_obs < 2:
        trend_min_obs = 2
    trend_min_consistency_raw = trend_cfg.get("min_trend_consistency", 0.6) if isinstance(trend_cfg, dict) else 0.6
    trend_min_consistency = float(0.6 if trend_min_consistency_raw is None else trend_min_consistency_raw)
    trend_min_consistency = max(0.0, min(1.0, trend_min_consistency))

    # Phase 5.1: Pre-compute per-stage trust trend from audit history
    audit_rows = run_audit if isinstance(run_audit, list) else []
    stage_trends: dict[str, dict[str, Any]] = {}
    if trend_enabled and audit_rows:
        for stage_name in (cfg.get("target_stages", []) if isinstance(cfg.get("target_stages"), list) else target_stages):
            scores: list[float] = []
            window = audit_rows[-trend_min_obs:] if len(audit_rows) >= trend_min_obs else audit_rows
            for row in window:
                if not isinstance(row, dict):
                    continue
                ts = row.get("trust_stages", {})
                if isinstance(ts, dict) and stage_name in ts:
                    try:
                        scores.append(float(ts[stage_name]))
                    except (TypeError, ValueError):
                        pass
            if len(scores) >= 2:
                # Compute sequential deltas
                deltas = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]
                positive = sum(1 for d in deltas if d > 0.001)
                negative = sum(1 for d in deltas if d < -0.001)
                neutral = len(deltas) - positive - negative
                total_deltas = len(deltas)

                if total_deltas > 0:
                    pos_frac = positive / total_deltas
                    neg_frac = negative / total_deltas
                else:
                    pos_frac = 0.0
                    neg_frac = 0.0

                if pos_frac >= trend_min_consistency:
                    direction = "improving"
                elif neg_frac >= trend_min_consistency:
                    direction = "declining"
                else:
                    direction = "stable"

                avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
                stage_trends[stage_name] = {
                    "direction": direction,
                    "consistency": round(max(pos_frac, neg_frac), 3),
                    "avg_delta": round(avg_delta, 4),
                    "observations": len(scores),
                    "sufficient": len(scores) >= trend_min_obs,
                }
            else:
                stage_trends[stage_name] = {
                    "direction": "insufficient_data",
                    "consistency": 0.0,
                    "avg_delta": 0.0,
                    "observations": len(scores),
                    "sufficient": False,
                }

    target_stages = cfg.get("target_stages", ["cortex", "consolidate", "hippocampus", "evolve"])
    if not isinstance(target_stages, list):
        target_stages = ["cortex", "consolidate", "hippocampus", "evolve"]

    agents = trust_snapshot.get("agents", {}) if isinstance(trust_snapshot, dict) else {}
    if not isinstance(agents, dict):
        agents = {}

    proposals: list[dict[str, Any]] = []
    evaluated_stages = 0

    for stage in target_stages:
        if len(proposals) >= max_proposals_per_run:
            break

        stats = agents.get(f"stage:{stage}", {})
        if not isinstance(stats, dict):
            continue

        evaluated_stages += 1
        total = int(stats.get("total", 0) or 0)
        if total < min_stage_observations:
            continue

        trust_score = float(stats.get("trust_score", 0.5) or 0.5)
        trigger_rate = float(stats.get("recent_trigger_rate", 0.0) or 0.0)
        confidence = float(stats.get("trust_confidence_ema", stats.get("trust_confidence", 0.0)) or 0.0)
        confidence = max(0.0, min(1.0, confidence))

        if confidence < min_confidence:
            continue

        if trust_score <= tighten_max_trust and trigger_rate >= tighten_min_trigger_rate:
            # Phase 5.1: Trend gate — skip tighten if trust is rapidly improving
            trend_info = stage_trends.get(stage, {})
            if trend_enabled and trend_info.get("sufficient", False):
                if trend_info.get("direction") == "improving":
                    continue  # Trust is recovering; tighten would be premature

            proposal_id = f"{stage}:tighten:{tighten_recommended_change}"
            proposal_entry: dict[str, Any] = {
                "proposal_id": proposal_id,
                "stage": stage,
                "mode": "tighten",
                "recommended_change": tighten_recommended_change,
                "reason": "low_trust_and_high_trigger_rate",
                "metrics": {
                    "trust_score": round(trust_score, 3),
                    "recent_trigger_rate": round(trigger_rate, 3),
                    "trust_confidence_ema": round(confidence, 3),
                    "total_observations": total,
                },
            }
            if trend_info:
                proposal_entry["trend"] = trend_info
            proposals.append(proposal_entry)
            continue

        if trust_score >= relax_min_trust and trigger_rate <= relax_max_trigger_rate:
            # Phase 5.1: Trend gate — skip relax if trust is declining
            trend_info = stage_trends.get(stage, {})
            if trend_enabled and trend_info.get("sufficient", False):
                if trend_info.get("direction") == "declining":
                    continue  # Trust is dropping; relax would be premature

            proposal_id = f"{stage}:relax:{relax_recommended_change}"
            proposal_entry = {
                "proposal_id": proposal_id,
                "stage": stage,
                "mode": "relax",
                "recommended_change": relax_recommended_change,
                "reason": "high_trust_and_low_trigger_rate",
                "metrics": {
                    "trust_score": round(trust_score, 3),
                    "recent_trigger_rate": round(trigger_rate, 3),
                    "trust_confidence_ema": round(confidence, 3),
                    "total_observations": total,
                },
            }
            if trend_info:
                proposal_entry["trend"] = trend_info
            proposals.append(proposal_entry)

    return {
        "enabled": True,
        "proposal_only": proposal_only,
        "evaluated_stages": evaluated_stages,
        "trend_gating": {
            "enabled": trend_enabled,
            "min_trend_observations": trend_min_obs,
            "min_trend_consistency": round(trend_min_consistency, 3),
            "stage_trends": stage_trends,
        },
        "proposals": proposals,
    }


def evaluate_self_reconfigure_acceptance(
    policy: dict[str, Any],
    self_reconfigure: dict[str, Any],
    approval_ledger_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Resolve explicit approvals for self-reconfigure proposals (no auto-apply)."""
    cfg = policy.get("self_reconfigure", {}) if isinstance(policy, dict) else {}
    acceptance_cfg = cfg.get("acceptance", {}) if isinstance(cfg, dict) else {}
    enabled = isinstance(acceptance_cfg, dict) and bool(acceptance_cfg.get("enabled", True))
    require_explicit_approval = bool(acceptance_cfg.get("require_explicit_approval", True)) if isinstance(acceptance_cfg, dict) else True
    if isinstance(acceptance_cfg, dict):
        max_acceptances_raw = acceptance_cfg.get("max_acceptances_per_run", 1)
        max_acceptances_per_run = int(1 if max_acceptances_raw is None else max_acceptances_raw)
    else:
        max_acceptances_per_run = 1
    if max_acceptances_per_run < 0:
        max_acceptances_per_run = 0
    use_approval_ledger_ids = bool(acceptance_cfg.get("use_approval_ledger_ids", True)) if isinstance(acceptance_cfg, dict) else True
    merge_policy_and_ledger_ids = bool(acceptance_cfg.get("merge_policy_and_ledger_ids", True)) if isinstance(acceptance_cfg, dict) else True

    approved_ids_raw = acceptance_cfg.get("approved_proposal_ids", []) if isinstance(acceptance_cfg, dict) else []
    policy_approved_ids: set[str] = set()
    if isinstance(approved_ids_raw, list):
        policy_approved_ids = {str(item) for item in approved_ids_raw if str(item)}

    ledger_approved_ids: set[str] = set()
    if use_approval_ledger_ids and isinstance(approval_ledger_ids, list):
        ledger_approved_ids = {str(item) for item in approval_ledger_ids if str(item)}

    if merge_policy_and_ledger_ids:
        approved_ids = policy_approved_ids | ledger_approved_ids
    elif use_approval_ledger_ids:
        approved_ids = ledger_approved_ids
    else:
        approved_ids = policy_approved_ids

    proposals = self_reconfigure.get("proposals", []) if isinstance(self_reconfigure, dict) else []
    if not isinstance(proposals, list):
        proposals = []

    accepted_proposals: list[dict[str, Any]] = []
    if enabled:
        for proposal in proposals:
            if len(accepted_proposals) >= max_acceptances_per_run:
                break
            if not isinstance(proposal, dict):
                continue

            proposal_id = str(proposal.get("proposal_id", "") or "")
            if not proposal_id:
                continue

            if require_explicit_approval and proposal_id not in approved_ids:
                continue

            accepted_proposals.append(
                {
                    **proposal,
                    "accepted": True,
                    "apply_now": False,
                    "acceptance_mode": "explicit_approval",
                }
            )

    return {
        "enabled": enabled,
        "require_explicit_approval": require_explicit_approval,
        "approved_proposal_ids": sorted(approved_ids),
        "approved_proposal_ids_policy": sorted(policy_approved_ids),
        "approved_proposal_ids_ledger": sorted(ledger_approved_ids),
        "use_approval_ledger_ids": use_approval_ledger_ids,
        "merge_policy_and_ledger_ids": merge_policy_and_ledger_ids,
        "max_acceptances_per_run": max_acceptances_per_run,
        "auto_apply_enabled": False,
        "accepted_proposals": accepted_proposals,
        "pending_proposals": max(0, len(proposals) - len(accepted_proposals)),
    }


def _apply_trust_control(stage_policy: dict[str, Any], stage_context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply trust-based overrides to a stage policy."""
    policy = dict(stage_policy)
    trust_cfg = policy.get("trust_control", {})
    if not isinstance(trust_cfg, dict) or not trust_cfg.get("enabled", False):
        return policy, {
            "enabled": False,
            "trust_score": round(float(stage_context.get("trust_score", 0.5)), 3),
            "effective_trust_score": round(float(stage_context.get("trust_score", 0.5)), 3),
            "trust_confidence": round(float(stage_context.get("trust_confidence", 1.0)), 3),
            "trust_confidence_ema": round(float(stage_context.get("trust_confidence_ema", stage_context.get("trust_confidence", 1.0))), 3),
            "recent_trigger_rate": round(float(stage_context.get("recent_trigger_rate", 0.0)), 3),
            "recent_trigger_load": round(float(stage_context.get("recent_trigger_load", 0.0)), 3),
        }

    trust_score = float(stage_context.get("trust_score", 0.5))
    trust_confidence = float(stage_context.get("trust_confidence", 1.0))
    trust_confidence_ema = float(stage_context.get("trust_confidence_ema", trust_confidence))
    trust_confidence = max(0.0, min(1.0, trust_confidence))
    trust_confidence_ema = max(0.0, min(1.0, trust_confidence_ema))
    recent_trigger_rate = float(stage_context.get("recent_trigger_rate", 0.0))
    recent_trigger_load = float(stage_context.get("recent_trigger_load", 0.0))
    total_observations = int(stage_context.get("total", 999999) or 0)

    confidence_cfg = trust_cfg.get("confidence_scaling", {})
    confidence_scaling_enabled = isinstance(confidence_cfg, dict) and confidence_cfg.get("enabled", True)
    confidence_source = str(confidence_cfg.get("confidence_source", "raw") or "raw").lower() if isinstance(confidence_cfg, dict) else "raw"
    if confidence_source not in {"raw", "ema"}:
        confidence_source = "raw"
    control_confidence = trust_confidence_ema if confidence_source == "ema" else trust_confidence
    neutral_trust = float(confidence_cfg.get("neutral_trust", 0.5)) if isinstance(confidence_cfg, dict) else 0.5
    neutral_trust = max(0.0, min(1.0, neutral_trust))
    min_confidence_for_override = (
        float(confidence_cfg.get("min_confidence_for_override", 0.0)) if isinstance(confidence_cfg, dict) else 0.0
    )
    min_confidence_for_override = max(0.0, min(1.0, min_confidence_for_override))
    min_confidence_for_low_override = (
        float(confidence_cfg.get("min_confidence_for_low_override", min_confidence_for_override))
        if isinstance(confidence_cfg, dict)
        else min_confidence_for_override
    )
    min_confidence_for_high_override = (
        float(confidence_cfg.get("min_confidence_for_high_override", min_confidence_for_override))
        if isinstance(confidence_cfg, dict)
        else min_confidence_for_override
    )
    min_confidence_for_low_override = max(0.0, min(1.0, min_confidence_for_low_override))
    min_confidence_for_high_override = max(0.0, min(1.0, min_confidence_for_high_override))
    guard_low_on_confidence_recovery = (
        bool(confidence_cfg.get("guard_low_on_confidence_recovery", False)) if isinstance(confidence_cfg, dict) else False
    )
    min_confidence_recovery_for_low_override = (
        float(confidence_cfg.get("min_confidence_recovery_for_low_override", 0.2)) if isinstance(confidence_cfg, dict) else 0.2
    )
    min_confidence_recovery_for_low_override = max(0.0, min(1.0, min_confidence_recovery_for_low_override))
    guard_high_on_confidence_drop = (
        bool(confidence_cfg.get("guard_high_on_confidence_drop", False)) if isinstance(confidence_cfg, dict) else False
    )
    max_confidence_drop_for_high_override = (
        float(confidence_cfg.get("max_confidence_drop_for_high_override", 0.2)) if isinstance(confidence_cfg, dict) else 0.2
    )
    max_confidence_drop_for_high_override = max(0.0, min(1.0, max_confidence_drop_for_high_override))
    guard_overrides_on_confidence_volatility = (
        bool(confidence_cfg.get("guard_overrides_on_confidence_volatility", False)) if isinstance(confidence_cfg, dict) else False
    )
    max_confidence_volatility_for_overrides = (
        float(confidence_cfg.get("max_confidence_volatility_for_overrides", 0.25)) if isinstance(confidence_cfg, dict) else 0.25
    )
    max_confidence_volatility_for_overrides = max(0.0, min(1.0, max_confidence_volatility_for_overrides))
    require_consensus_for_overrides = (
        bool(confidence_cfg.get("require_consensus_for_overrides", False)) if isinstance(confidence_cfg, dict) else False
    )
    max_effective_trust_disagreement_for_overrides = (
        float(confidence_cfg.get("max_effective_trust_disagreement_for_overrides", 0.15))
        if isinstance(confidence_cfg, dict)
        else 0.15
    )
    max_effective_trust_disagreement_for_overrides = max(0.0, min(1.0, max_effective_trust_disagreement_for_overrides))
    scale_threshold_adjustment = (
        bool(confidence_cfg.get("scale_threshold_adjustment", True)) if isinstance(confidence_cfg, dict) else True
    )
    min_threshold_adjustment_scale = (
        float(confidence_cfg.get("min_threshold_adjustment_scale", 0.25)) if isinstance(confidence_cfg, dict) else 0.25
    )
    min_threshold_adjustment_scale = max(0.0, min(1.0, min_threshold_adjustment_scale))
    scale_trigger_signal = bool(confidence_cfg.get("scale_trigger_signal", False)) if isinstance(confidence_cfg, dict) else False
    min_trigger_signal_scale = (
        float(confidence_cfg.get("min_trigger_signal_scale", 0.25)) if isinstance(confidence_cfg, dict) else 0.25
    )
    min_trigger_signal_scale = max(0.0, min(1.0, min_trigger_signal_scale))
    scale_min_observations = (
        bool(confidence_cfg.get("scale_min_observations", False)) if isinstance(confidence_cfg, dict) else False
    )
    max_min_observations = int(confidence_cfg.get("max_min_observations", 10) or 10) if isinstance(confidence_cfg, dict) else 10
    if max_min_observations < 0:
        max_min_observations = 0
    adjustment_confidence_scale = 1.0
    trigger_confidence_scale = 1.0

    if confidence_scaling_enabled:
        effective_trust_score = (control_confidence * trust_score) + ((1.0 - control_confidence) * neutral_trust)
        effective_trust_score_raw = (trust_confidence * trust_score) + ((1.0 - trust_confidence) * neutral_trust)
        effective_trust_score_ema = (trust_confidence_ema * trust_score) + ((1.0 - trust_confidence_ema) * neutral_trust)
    else:
        effective_trust_score = trust_score
        effective_trust_score_raw = trust_score
        effective_trust_score_ema = trust_score
    effective_trust_score = max(0.0, min(1.0, effective_trust_score))
    effective_trust_score_raw = max(0.0, min(1.0, effective_trust_score_raw))
    effective_trust_score_ema = max(0.0, min(1.0, effective_trust_score_ema))

    min_observations = int(trust_cfg.get("min_observations_for_override", 3) or 0)
    if min_observations < 0:
        min_observations = 0
    effective_min_observations = min_observations
    if confidence_scaling_enabled and scale_min_observations:
        if max_min_observations < min_observations:
            max_min_observations = min_observations
        confidence_gap = 1.0 - control_confidence
        effective_min_observations = min_observations + int(round(confidence_gap * (max_min_observations - min_observations)))

    sample_guard_applied = total_observations < effective_min_observations
    low_confidence_guard_applied = confidence_scaling_enabled and control_confidence < min_confidence_for_low_override
    high_confidence_guard_applied = confidence_scaling_enabled and control_confidence < min_confidence_for_high_override
    confidence_recovery = max(0.0, trust_confidence - trust_confidence_ema)
    low_confidence_recovery_guard_applied = (
        confidence_scaling_enabled
        and guard_low_on_confidence_recovery
        and confidence_recovery > min_confidence_recovery_for_low_override
    )
    confidence_drop = max(0.0, trust_confidence_ema - trust_confidence)
    high_confidence_drop_guard_applied = (
        confidence_scaling_enabled
        and guard_high_on_confidence_drop
        and confidence_drop > max_confidence_drop_for_high_override
    )
    confidence_volatility = abs(trust_confidence - trust_confidence_ema)
    confidence_volatility_guard_applied = (
        confidence_scaling_enabled
        and guard_overrides_on_confidence_volatility
        and confidence_volatility > max_confidence_volatility_for_overrides
    )
    effective_trust_disagreement = abs(effective_trust_score_raw - effective_trust_score_ema)
    consensus_guard_applied = (
        confidence_scaling_enabled
        and require_consensus_for_overrides
        and effective_trust_disagreement > max_effective_trust_disagreement_for_overrides
    )
    confidence_guard_applied = low_confidence_guard_applied or high_confidence_guard_applied

    low_threshold = float(trust_cfg.get("low_trust_threshold", 0.35))
    high_threshold = float(trust_cfg.get("high_trust_threshold", 0.9))

    # Phase 2.2: optional auto-tighten/relax of thresholds by recent trigger-rate.
    adaptive_cfg = trust_cfg.get("adaptive_thresholds", {})
    threshold_adjustment = 0.0
    adjustment_mode = "none"
    adjustment_levels = 0
    adaptive_warmup_applied = False
    signal_ramp_factor = 1.0
    signal_mode = "rate"
    trigger_signal = recent_trigger_rate
    trigger_signal_effective = trigger_signal
    if isinstance(adaptive_cfg, dict) and adaptive_cfg.get("enabled", False):
        signal_mode = str(adaptive_cfg.get("signal_mode", "rate") or "rate").lower()
        if signal_mode == "load":
            trigger_signal = recent_trigger_load
        elif signal_mode == "max":
            trigger_signal = max(recent_trigger_rate, recent_trigger_load)
        else:
            trigger_signal = recent_trigger_rate

        high_trigger_rate = float(adaptive_cfg.get("high_trigger_rate", 0.3))
        low_trigger_rate = float(adaptive_cfg.get("low_trigger_rate", 0.05))
        trigger_rate_step = float(adaptive_cfg.get("trigger_rate_step", 0.1))
        if trigger_rate_step <= 0:
            trigger_rate_step = 0.1
        threshold_step = float(adaptive_cfg.get("threshold_step", 0.05))
        max_adjustment = float(adaptive_cfg.get("max_adjustment", 0.2))
        deadband = float(adaptive_cfg.get("deadband", 0.02))
        if deadband < 0:
            deadband = 0.0
        high_deadband = float(adaptive_cfg.get("high_deadband", deadband))
        low_deadband = float(adaptive_cfg.get("low_deadband", deadband))
        if high_deadband < 0:
            high_deadband = 0.0
        if low_deadband < 0:
            low_deadband = 0.0
        min_signal_observations = int(adaptive_cfg.get("min_signal_observations", 5) or 0)
        if min_signal_observations < 0:
            min_signal_observations = 0
        ramp_observations = int(adaptive_cfg.get("ramp_observations", 5) or 0)
        if ramp_observations < 0:
            ramp_observations = 0
        adaptive_warmup_applied = total_observations < min_signal_observations

        if not adaptive_warmup_applied:
            if ramp_observations > 0:
                signal_ramp_factor = min(
                    1.0,
                    max(0.0, (total_observations - min_signal_observations + 1) / float(ramp_observations)),
                )
            trigger_signal_effective = trigger_signal * signal_ramp_factor
            if confidence_scaling_enabled and scale_trigger_signal:
                trigger_confidence_scale = max(min_trigger_signal_scale, control_confidence)
                trigger_signal_effective = trigger_signal_effective * trigger_confidence_scale

            if trigger_signal_effective >= (high_trigger_rate + high_deadband):
                adjustment_levels = 1 + int((trigger_signal_effective - (high_trigger_rate + high_deadband)) / trigger_rate_step)
                threshold_adjustment = min(max_adjustment, threshold_step * adjustment_levels)
                adjustment_mode = "tighten"
            elif trigger_signal_effective <= (low_trigger_rate - low_deadband):
                adjustment_levels = 1 + int(((low_trigger_rate - low_deadband) - trigger_signal_effective) / trigger_rate_step)
                threshold_adjustment = -min(max_adjustment, threshold_step * adjustment_levels)
                adjustment_mode = "relax"

        if confidence_scaling_enabled and scale_threshold_adjustment and threshold_adjustment != 0.0:
            adjustment_confidence_scale = max(min_threshold_adjustment_scale, control_confidence)
            threshold_adjustment = threshold_adjustment * adjustment_confidence_scale

    low_threshold_adj = max(0.0, min(1.0, low_threshold + threshold_adjustment))
    high_threshold_adj = max(0.0, min(1.0, high_threshold + threshold_adjustment))

    if high_threshold_adj < low_threshold_adj:
        high_threshold_adj = low_threshold_adj

    if not sample_guard_applied:
        if effective_trust_score < low_threshold_adj:
            if (
                not low_confidence_guard_applied
                and not low_confidence_recovery_guard_applied
                and not confidence_volatility_guard_applied
                and not consensus_guard_applied
            ):
                overrides = trust_cfg.get("low_trust", {})
                if isinstance(overrides, dict):
                    policy = _merge_dicts(policy, overrides)
        elif effective_trust_score >= high_threshold_adj:
            if (
                not high_confidence_guard_applied
                and not high_confidence_drop_guard_applied
                and not confidence_volatility_guard_applied
                and not consensus_guard_applied
            ):
                overrides = trust_cfg.get("high_trust", {})
                if isinstance(overrides, dict):
                    policy = _merge_dicts(policy, overrides)

    meta = {
        "enabled": True,
        "trust_score": round(trust_score, 3),
        "effective_trust_score": round(effective_trust_score, 3),
        "effective_trust_score_raw": round(effective_trust_score_raw, 3),
        "effective_trust_score_ema": round(effective_trust_score_ema, 3),
        "trust_confidence": round(trust_confidence, 3),
        "trust_confidence_ema": round(trust_confidence_ema, 3),
        "confidence_source": confidence_source,
        "control_confidence": round(control_confidence, 3),
        "confidence_scaling_enabled": bool(confidence_scaling_enabled),
        "neutral_trust": round(neutral_trust, 3),
        "min_confidence_for_override": round(min_confidence_for_override, 3),
        "min_confidence_for_low_override": round(min_confidence_for_low_override, 3),
        "min_confidence_for_high_override": round(min_confidence_for_high_override, 3),
        "guard_low_on_confidence_recovery": bool(guard_low_on_confidence_recovery),
        "min_confidence_recovery_for_low_override": round(min_confidence_recovery_for_low_override, 3),
        "confidence_recovery": round(confidence_recovery, 3),
        "guard_high_on_confidence_drop": bool(guard_high_on_confidence_drop),
        "max_confidence_drop_for_high_override": round(max_confidence_drop_for_high_override, 3),
        "confidence_drop": round(confidence_drop, 3),
        "guard_overrides_on_confidence_volatility": bool(guard_overrides_on_confidence_volatility),
        "max_confidence_volatility_for_overrides": round(max_confidence_volatility_for_overrides, 3),
        "confidence_volatility": round(confidence_volatility, 3),
        "require_consensus_for_overrides": bool(require_consensus_for_overrides),
        "max_effective_trust_disagreement_for_overrides": round(max_effective_trust_disagreement_for_overrides, 3),
        "effective_trust_disagreement": round(effective_trust_disagreement, 3),
        "confidence_guard_applied": bool(confidence_guard_applied),
        "low_confidence_guard_applied": bool(low_confidence_guard_applied),
        "low_confidence_recovery_guard_applied": bool(low_confidence_recovery_guard_applied),
        "high_confidence_guard_applied": bool(high_confidence_guard_applied),
        "high_confidence_drop_guard_applied": bool(high_confidence_drop_guard_applied),
        "confidence_volatility_guard_applied": bool(confidence_volatility_guard_applied),
        "consensus_guard_applied": bool(consensus_guard_applied),
        "scale_threshold_adjustment": bool(scale_threshold_adjustment),
        "min_threshold_adjustment_scale": round(min_threshold_adjustment_scale, 3),
        "adjustment_confidence_scale": round(adjustment_confidence_scale, 3),
        "scale_trigger_signal": bool(scale_trigger_signal),
        "min_trigger_signal_scale": round(min_trigger_signal_scale, 3),
        "trigger_confidence_scale": round(trigger_confidence_scale, 3),
        "scale_min_observations": bool(scale_min_observations),
        "max_min_observations": max_min_observations,
        "recent_trigger_rate": round(recent_trigger_rate, 3),
        "recent_trigger_load": round(recent_trigger_load, 3),
        "signal_mode": signal_mode,
        "trigger_signal": round(trigger_signal, 3),
        "total_observations": total_observations,
        "min_observations_for_override": min_observations,
        "effective_min_observations": effective_min_observations,
        "sample_guard_applied": sample_guard_applied,
        "adaptive_warmup_applied": adaptive_warmup_applied,
        "signal_ramp_factor": round(signal_ramp_factor, 3),
        "trigger_signal_effective": round(trigger_signal_effective, 3),
        "deadband": round(float(adaptive_cfg.get("deadband", 0.02) or 0.02), 3),
        "high_deadband": round(float(adaptive_cfg.get("high_deadband", adaptive_cfg.get("deadband", 0.02)) or 0.02), 3),
        "low_deadband": round(float(adaptive_cfg.get("low_deadband", adaptive_cfg.get("deadband", 0.02)) or 0.02), 3),
        "threshold_adjustment": round(threshold_adjustment, 3),
        "adjustment_levels": adjustment_levels,
        "adjustment_mode": adjustment_mode,
        "low_threshold": round(low_threshold_adj, 3),
        "high_threshold": round(high_threshold_adj, 3),
    }
    return policy, meta


@dataclass
class DelegationContract:
    """Contract-first specification for one delegated pipeline stage."""
    contract_id: str
    stage: str
    objective: str
    falsifier: str
    verifier: str
    criticality: str
    reversibility: str
    budget: dict[str, Any] = field(default_factory=dict)
    authority_scope: dict[str, Any] = field(default_factory=dict)
    monitoring: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_stage_contract(stage: str, run_id: str) -> DelegationContract:
    """Create a minimal stage contract with explicit verification semantics."""
    objective_map = {
        "smoke": "Verify engine loads and basic physics metrics remain valid.",
        "cortex": "Generate and execute valid protocols to reduce priority knowledge gaps.",
        "consolidate": "Convert cortex outputs into structured, auditable findings.",
        "hippocampus": "Replay and consolidate memory traces without touching core graph.",
        "evolve": "Run candidate A/B checks and detect regressions.",
        "report": "Emit final, auditable run summary.",
    }
    falsifier_map = {
        "smoke": "Engine metrics invalid (mass<=0, entropy<=0, maxRho<=0).",
        "cortex": "No executable protocol outcomes or sanity failures dominate outputs.",
        "consolidate": "No valid artifacts are produced from a non-dry cortex session.",
        "hippocampus": "Dream/replay fails to run or memory stats become inconsistent.",
        "evolve": "Candidate verdict indicates regression in core checks.",
        "report": "Pipeline summary cannot be generated or is internally inconsistent.",
    }
    verifier_map = {
        "smoke": "engine_smoke_check",
        "cortex": "protocol_summary_plus_sanity",
        "consolidate": "artifact_consolidation_result",
        "hippocampus": "dream_summary_plus_memory_stats",
        "evolve": "ab_regression_verdict",
        "report": "pipeline_summary_integrity",
    }
    criticality_map = {
        "smoke": "high",
        "cortex": "high",
        "consolidate": "medium",
        "hippocampus": "medium",
        "evolve": "low",
        "report": "medium",
    }
    reversibility_map = {
        "smoke": "reversible",
        "cortex": "reversible",
        "consolidate": "reversible",
        "hippocampus": "reversible",
        "evolve": "reversible",
        "report": "reversible",
    }
    budget_map = {
        "smoke": {"max_elapsed_sec": 120},
        "cortex": {"max_elapsed_sec": 3600},
        "consolidate": {"max_elapsed_sec": 900},
        "hippocampus": {"max_elapsed_sec": 1800},
        "evolve": {"max_elapsed_sec": 1800},
        "report": {"max_elapsed_sec": 120},
    }

    return DelegationContract(
        contract_id=f"DC-{run_id}-{stage}",
        stage=stage,
        objective=objective_map.get(stage, "Execute delegated stage safely and verifiably."),
        falsifier=falsifier_map.get(stage, "Stage output fails declared checks."),
        verifier=verifier_map.get(stage, "stage_output_validation"),
        criticality=criticality_map.get(stage, "medium"),
        reversibility=reversibility_map.get(stage, "reversible"),
        budget=budget_map.get(stage, {"max_elapsed_sec": 900}),
        authority_scope={
            "subdelegation_allowed": False,
            "core_graph_mutation": False,
            "allowed_outputs": ["stage_output", "logs", "artifacts"],
        },
        monitoring={
            "mode": "event_and_outcome",
            "cadence": "stage_boundary",
            "requires_attestation": True,
        },
    )


class AdaptiveTriggerEngine:
    """Detect runtime delegation triggers and suggest adaptive responses."""

    def evaluate(
        self,
        stage: str,
        status: str,
        output: dict[str, Any],
        elapsed_sec: float,
        contract: DelegationContract,
    ) -> list[dict[str, Any]]:
        triggers: list[dict[str, Any]] = []

        max_elapsed = contract.budget.get("max_elapsed_sec")
        if isinstance(max_elapsed, (int, float)) and elapsed_sec > max_elapsed:
            triggers.append({
                "type": "resource_overrun",
                "severity": "medium",
                "detail": f"elapsed={elapsed_sec:.2f}s > budget={max_elapsed}s",
            })

        if status == "failed":
            triggers.append({
                "type": "anomaly",
                "severity": "high",
                "detail": "stage execution failed",
            })

        if stage == "cortex":
            protocols_run = int(output.get("protocols_run", 0) or 0)
            dry_run = bool(output.get("dry_run", False))
            if protocols_run == 0 and not dry_run:
                triggers.append({
                    "type": "velocity_drop",
                    "severity": "medium",
                    "detail": "no protocols executed in non-dry cortex stage",
                })

            sanity_rows = output.get("sanity_results", []) or []
            failed_sanity = [row for row in sanity_rows if not row.get("sanity_passed", False)]
            if failed_sanity:
                triggers.append({
                    "type": "sanity_fail",
                    "severity": "high",
                    "detail": f"{len(failed_sanity)} protocol(s) failed sanity checks",
                })

            anomaly_rows = [row for row in sanity_rows if row.get("anomalies")]
            if anomaly_rows:
                triggers.append({
                    "type": "anomaly",
                    "severity": "medium",
                    "detail": f"{len(anomaly_rows)} protocol(s) reported anomalies",
                })

        for trigger in triggers:
            trigger["recommended_action"] = self.recommend_action(trigger["type"], contract)

        return triggers

    @staticmethod
    def recommend_action(trigger_type: str, contract: DelegationContract) -> str:
        if contract.criticality == "high" and contract.reversibility != "reversible":
            if trigger_type in {"sanity_fail", "anomaly"}:
                return "halt_and_escalate_human"

        if trigger_type == "sanity_fail":
            return "reassign_or_recompose"
        if trigger_type == "velocity_drop":
            return "retry_with_alt_gap_or_scope"
        if trigger_type == "resource_overrun":
            return "tighten_budget_or_reduce_steps"
        if trigger_type == "anomaly":
            return "increase_monitoring_and_verify"
        return "observe"


class TrustLedger:
    """Lightweight local trust/reputation store keyed by stage identity."""

    def __init__(self, path: Path, dynamics: dict[str, Any] | None = None):
        self.path = path
        self.dynamics = dynamics or {
            "default": {
                "alpha": 0.25,
                "success_gain": 1.0,
                "failure_penalty": 1.0,
                "min_score": 0.0,
                "max_score": 1.0,
                "dynamic_weight": 0.65,
                "lifetime_weight": 0.35,
                "confidence_k": 5.0,
                "confidence_ema_alpha": 0.3,
                "neutral_score": 0.5,
                "trigger_type_weights": {
                    "sanity_fail": 1.0,
                    "anomaly": 0.8,
                    "velocity_drop": 0.6,
                    "resource_overrun": 0.4,
                },
            },
            "stages": {},
        }
        self.data = self._load()

    def _stage_dynamics(self, stage: str) -> dict[str, Any]:
        """Resolve dynamics for one stage from defaults + stage override."""
        defaults = self.dynamics.get("default", {}) if isinstance(self.dynamics, dict) else {}
        stages = self.dynamics.get("stages", {}) if isinstance(self.dynamics, dict) else {}
        stage_override = stages.get(stage, {}) if isinstance(stages, dict) else {}
        merged = dict(defaults)
        if isinstance(stage_override, dict):
            merged.update(stage_override)
        return merged

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    def _dynamic_update(self, prior: float, status: str, stage: str) -> float:
        """Recency-weighted trust update; recent outcomes have stronger influence."""
        dyn = self._stage_dynamics(stage)
        alpha = float(dyn.get("alpha", 0.25))
        success_gain = float(dyn.get("success_gain", 1.0))
        failure_penalty = float(dyn.get("failure_penalty", 1.0))
        min_score = float(dyn.get("min_score", 0.0))
        max_score = float(dyn.get("max_score", 1.0))

        if status == "passed":
            delta = alpha * success_gain * (max_score - prior)
            updated = prior + delta
        elif status == "failed":
            delta = alpha * failure_penalty * (prior - min_score)
            updated = prior - delta
        else:
            updated = prior

        return round(self._clamp(updated, min_score, max_score), 3)

    def _history_window(self, stage: str) -> int:
        """Return history window length for recent trigger-rate estimate."""
        dyn = self._stage_dynamics(stage)
        window = int(dyn.get("history_window", 20) or 20)
        return max(3, min(200, window))

    def _trigger_load(self, stage: str, trigger_types: list[str]) -> float:
        """Weighted trigger pressure for one run (higher = more severe signal)."""
        if not trigger_types:
            return 0.0

        dyn = self._stage_dynamics(stage)
        weights = dyn.get("trigger_type_weights", {})
        if not isinstance(weights, dict):
            weights = {}

        total = 0.0
        for trigger_type in trigger_types:
            total += float(weights.get(trigger_type, 1.0))
        return round(total, 3)

    def _confidence_weight(self, stage: str, attempted: int) -> float:
        """Confidence of trust estimate as evidence grows."""
        dyn = self._stage_dynamics(stage)
        confidence_k = float(dyn.get("confidence_k", 5.0) or 5.0)
        if confidence_k < 0.0:
            confidence_k = 0.0
        if attempted <= 0:
            return 0.0
        if confidence_k == 0.0:
            return 1.0
        return round(attempted / (attempted + confidence_k), 3)

    def _blend_trust_scores(self, stage: str, dynamic_score: float, lifetime_score: float, attempted: int) -> tuple[float, float]:
        """Blend dynamic/lifetime trust, then shrink toward neutral by confidence."""
        dyn = self._stage_dynamics(stage)
        dynamic_weight = float(dyn.get("dynamic_weight", 0.65) or 0.65)
        lifetime_weight = float(dyn.get("lifetime_weight", 0.35) or 0.35)
        neutral_score = float(dyn.get("neutral_score", 0.5) or 0.5)

        weight_sum = dynamic_weight + lifetime_weight
        if weight_sum <= 0.0:
            dynamic_weight, lifetime_weight = 0.65, 0.35
            weight_sum = 1.0

        dynamic_weight = dynamic_weight / weight_sum
        lifetime_weight = lifetime_weight / weight_sum

        base_blended = self._clamp((dynamic_weight * dynamic_score) + (lifetime_weight * lifetime_score), 0.0, 1.0)
        confidence = self._confidence_weight(stage, attempted)
        final_blended = self._clamp((confidence * base_blended) + ((1.0 - confidence) * neutral_score), 0.0, 1.0)
        return round(final_blended, 3), round(confidence, 3)

    @staticmethod
    def _recent_rate(values: list[int]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 3)

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "version": 1,
            "updated": _now_iso(),
            "agents": {},
        }

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated"] = _now_iso()
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    @staticmethod
    def _compute_trust_score(stats: dict[str, Any]) -> float:
        passed = int(stats.get("passed", 0))
        failed = int(stats.get("failed", 0))
        attempted = passed + failed
        if attempted <= 0:
            return 0.5

        success_rate = float(passed) / attempted
        trigger_events = int(stats.get("trigger_events", 0))
        penalty = min(0.4, 0.1 * (trigger_events / attempted))
        return round(max(0.0, min(1.0, success_rate - penalty)), 3)

    def record(
        self,
        stage: str,
        status: str,
        elapsed_sec: float,
        trigger_types: list[str],
        run_id: str,
    ):
        key = f"stage:{stage}"
        agents = self.data.setdefault("agents", {})
        stats = agents.setdefault(
            key,
            {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "avg_elapsed_sec": 0.0,
                "trigger_events": 0,
                "trigger_counts": {},
                "last_run_id": "",
                "last_seen": "",
                "trust_score": 0.5,
                "lifetime_trust_score": 0.5,
                "dynamic_trust_score": 0.5,
                "trust_confidence": 0.0,
                "trust_confidence_ema": 0.0,
                "base_blended_trust": 0.5,
                "recent_trigger_history": [],
                "recent_trigger_rate": 0.0,
                "recent_trigger_load_history": [],
                "recent_trigger_load": 0.0,
            },
        )

        stats["total"] += 1
        if status in {"passed", "failed", "skipped"}:
            stats[status] += 1

        prev_avg = float(stats.get("avg_elapsed_sec", 0.0))
        n = int(stats["total"])
        stats["avg_elapsed_sec"] = round(((prev_avg * (n - 1)) + elapsed_sec) / n, 3)

        stats["trigger_events"] += len(trigger_types)
        trigger_counts = stats.setdefault("trigger_counts", {})
        for trigger_type in trigger_types:
            trigger_counts[trigger_type] = int(trigger_counts.get(trigger_type, 0)) + 1

        history = list(stats.get("recent_trigger_history", []))
        history.append(1 if len(trigger_types) > 0 else 0)
        window = self._history_window(stage)
        if len(history) > window:
            history = history[-window:]
        stats["recent_trigger_history"] = history
        stats["recent_trigger_rate"] = self._recent_rate(history)

        load_history = list(stats.get("recent_trigger_load_history", []))
        load_history.append(self._trigger_load(stage, trigger_types))
        if len(load_history) > window:
            load_history = load_history[-window:]
        stats["recent_trigger_load_history"] = load_history
        stats["recent_trigger_load"] = self._recent_rate(load_history)

        stats["last_run_id"] = run_id
        stats["last_seen"] = _now_iso()

        lifetime_score = self._compute_trust_score(stats)
        prior_dynamic = float(stats.get("dynamic_trust_score", stats.get("trust_score", 0.5)))
        dynamic_score = self._dynamic_update(prior_dynamic, status, stage)
        attempted = int(stats.get("passed", 0) or 0) + int(stats.get("failed", 0) or 0)

        # Phase 3.0: confidence-weighted trust blend (low evidence stays near neutral).
        blended, confidence = self._blend_trust_scores(stage, dynamic_score, lifetime_score, attempted)
        base_blended = round(self._clamp((0.65 * dynamic_score) + (0.35 * lifetime_score), 0.0, 1.0), 3)

        stats["lifetime_trust_score"] = lifetime_score
        stats["dynamic_trust_score"] = dynamic_score
        stats["trust_confidence"] = confidence
        confidence_ema_alpha = float(self._stage_dynamics(stage).get("confidence_ema_alpha", 0.3) or 0.3)
        confidence_ema_alpha = max(0.0, min(1.0, confidence_ema_alpha))
        prior_confidence_ema = float(stats.get("trust_confidence_ema", confidence))
        confidence_ema = (confidence_ema_alpha * confidence) + ((1.0 - confidence_ema_alpha) * prior_confidence_ema)
        stats["trust_confidence_ema"] = round(self._clamp(confidence_ema, 0.0, 1.0), 3)
        stats["base_blended_trust"] = base_blended
        stats["trust_score"] = blended
        self._save()

    def snapshot(self) -> dict[str, Any]:
        return self.data

    def get_stage_trust(self, stage: str) -> float:
        """Return current trust score for a stage (neutral default=0.5)."""
        stats = self.data.get("agents", {}).get(f"stage:{stage}", {})
        try:
            return float(stats.get("trust_score", 0.5))
        except (TypeError, ValueError):
            return 0.5

    def get_stage_context(self, stage: str) -> dict[str, Any]:
        """Return trust + recent trigger signal context for adaptive policy."""
        stats = self.data.get("agents", {}).get(f"stage:{stage}", {})
        try:
            trust_score = float(stats.get("trust_score", 0.5))
        except (TypeError, ValueError):
            trust_score = 0.5
        try:
            trust_confidence = float(stats.get("trust_confidence", 1.0))
        except (TypeError, ValueError):
            trust_confidence = 1.0
        try:
            trust_confidence_ema = float(stats.get("trust_confidence_ema", trust_confidence))
        except (TypeError, ValueError):
            trust_confidence_ema = trust_confidence
        try:
            recent_trigger_rate = float(stats.get("recent_trigger_rate", 0.0))
        except (TypeError, ValueError):
            recent_trigger_rate = 0.0
        try:
            recent_trigger_load = float(stats.get("recent_trigger_load", 0.0))
        except (TypeError, ValueError):
            recent_trigger_load = 0.0
        return {
            "trust_score": trust_score,
            "trust_confidence": trust_confidence,
            "trust_confidence_ema": trust_confidence_ema,
            "recent_trigger_rate": recent_trigger_rate,
            "recent_trigger_load": recent_trigger_load,
            "total": int(stats.get("total", 0) or 0),
        }