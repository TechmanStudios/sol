"""
Report generation for SOL experiments.
=======================================
Generates Markdown run bundles and summary reports matching the
templates in .github/prompts/.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def generate_run_bundle(protocol: dict, run_results: dict,
                         sanity_report: dict | None = None) -> str:
    """Generate a Markdown run bundle from protocol + results.
    
    Maps to .github/prompts/run-bundle-template.md fields.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    series = protocol.get("seriesName", "unnamed")
    inv = protocol.get("invariants", {})

    lines = [
        f"# RUN BUNDLE — {series} ({now})",
        "",
        "## Identity",
        f"- seriesName: {series}",
        f"- engine: sol-core (headless Python)",
        f"- baselineModeUsed: {protocol.get('baseline', 'fresh')}",
        f"- operator: sol-core auto_run",
        f"- rng_seed: {inv.get('rng_seed', 42)}",
        "",
        "## Question",
        protocol.get("question", "(not specified)"),
        "",
        "## Invariants",
    ]
    for k, v in inv.items():
        lines.append(f"- {k}: {v}")

    # Knobs
    knobs = protocol.get("knobs", {})
    lines += ["", "## Knobs (independent variables)"]
    if knobs:
        for k, vals in knobs.items():
            lines.append(f"- {k}: {vals}")
    else:
        lines.append("- (none — single-condition run)")

    # Injections
    inj = protocol.get("injections", [])
    lines += ["", "## Injections"]
    for entry in inj:
        step = entry.get("at_step", 0)
        lines.append(f"- {entry['label']}: {entry['amount']} at step {step}")

    # Protocol
    lines += [
        "", "## Protocol",
        f"- Steps per condition: {protocol.get('steps', '?')}",
        f"- Reps per condition: {protocol.get('reps', 1)}",
        f"- Metrics every: {protocol.get('metrics_every', 1)} steps",
        f"- Baseline: {protocol.get('baseline', 'fresh')}",
    ]

    # Results summary
    summary = run_results.get("summary", {})
    lines += ["", "## Results Summary"]
    lines.append(f"- Total conditions: {summary.get('total_conditions', '?')}")
    lines.append(f"- Total reps: {summary.get('total_reps', '?')}")
    lines.append(f"- Total steps simulated: {summary.get('total_steps', '?')}")
    lines.append(f"- Runtime: {summary.get('runtime_sec', '?'):.2f}s")

    # Per-condition finals
    conditions = run_results.get("conditions", {})
    if conditions:
        lines += ["", "## Final Metrics by Condition", ""]
        # Table header
        cols = ["Condition", "Entropy", "Flux", "Mass", "Active", "RhoMax", "RhoMaxNode"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for label, data in conditions.items():
            final = data.get("final_metrics", {})
            row = [
                label,
                f"{final.get('entropy', 0):.6f}",
                f"{final.get('totalFlux', 0):.4f}",
                f"{final.get('mass', 0):.4f}",
                str(final.get("activeCount", 0)),
                f"{final.get('maxRho', 0):.4f}",
                str(final.get("rhoMaxId", "")),
            ]
            lines.append("| " + " | ".join(row) + " |")

    # Sanity checks
    if sanity_report:
        lines += ["", "## Sanity Checks"]
        lines.append(f"- Overall: {'PASS' if sanity_report.get('all_passed') else 'FAIL'}")
        for check in sanity_report.get("checks", []):
            status = "✓" if check["passed"] else "✗"
            lines.append(f"- {status} {check['name']}: {check['detail']}")

    # Falsifiers
    falsifiers = protocol.get("falsifiers", [])
    if falsifiers:
        lines += ["", "## Falsifiers"]
        for f in falsifiers:
            lines.append(f"- {f}")

    # Notes
    notes = protocol.get("notes", "")
    if notes:
        lines += ["", "## Notes", notes]

    # Exports
    exports = run_results.get("exports", {})
    if exports:
        lines += ["", "## Exports"]
        for name, path in exports.items():
            lines.append(f"- {name}: `{path}`")

    lines += ["", "## Deviations / Incidents", "- (none — automated run)", ""]

    return "\n".join(lines)


def generate_comparison_table(comparison: dict) -> str:
    """Generate a Markdown comparison table from metrics.compare_conditions output."""
    lines = []
    for metric_name, conditions in comparison.items():
        lines.append(f"### {metric_name}")
        labels = list(conditions.keys())
        if not labels:
            continue
        sub_keys = list(conditions[labels[0]].keys())
        header = ["Condition"] + sub_keys
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for label in labels:
            vals = conditions[label]
            row = [label] + [_fmt(vals.get(k)) for k in sub_keys]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    return "\n".join(lines)


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.6f}"
    return str(v)
