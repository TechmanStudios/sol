"""
SOL Evolve — PR / Report Generator
=====================================
Takes A/B test results and generates:
  - A Markdown regression report
  - A proof packet draft (if the candidate improves metrics)
  - A structured change proposal

Usage (CLI):
    python pr_gen.py report.json                     # From saved A/B report
    python pr_gen.py --candidate tune_conductance_gamma_up  # Run test + generate

Usage (Python API):
    from pr_gen import generate_report, generate_proof_packet
    md = generate_report(ab_report)
    pp = generate_proof_packet(ab_report)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
_SOL_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(ab_report: dict) -> str:
    """Generate a Markdown regression report from A/B test results."""
    candidate = ab_report["candidate"]
    verdict = ab_report["overall_verdict"]
    elapsed = ab_report.get("elapsed_sec", 0)

    lines = [
        f"# SOL Evolution Report: {candidate['name']}",
        "",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Verdict:** {verdict}",
        f"**Runtime:** {elapsed}s",
        "",
        "## Candidate Details",
        "",
        f"- **Name:** {candidate['name']}",
        f"- **Type:** {candidate['change_type']}",
        f"- **Target:** {candidate['target']}",
        f"- **Sacred Math Impact:** {candidate['sacred_math_impact']}",
        "",
        f"**Description:** {candidate['description']}",
        "",
        f"**Hypothesis:** {candidate['hypothesis']}",
        "",
        "**Parameters changed:**",
    ]
    for k, v in candidate.get("parameters", {}).items():
        lines.append(f"- `{k}` → `{v}`")

    lines.extend(["", "**Expected improvements:**"])
    for imp in candidate.get("expected_improvements", []):
        lines.append(f"- {imp}")

    lines.extend(["", "**Acceptable regressions:**"])
    for reg in candidate.get("acceptable_regressions", []):
        lines.append(f"- {reg}")

    # Per-protocol results
    lines.extend(["", "---", "", "## Regression Results", ""])

    protocols = ab_report.get("protocols", {})
    for proto_name, proto_result in protocols.items():
        if proto_result.get("status") != "COMPLETE":
            lines.append(f"### {proto_name}: {proto_result.get('status', 'UNKNOWN')}")
            lines.append(f"> {proto_result.get('reason', '')}")
            continue

        lines.append(f"### {proto_name}")
        lines.append("")

        for cond_label, cond_result in proto_result.get("conditions", {}).items():
            v = cond_result.get("verdict", {})
            lines.append(f"#### Condition: `{cond_label}`")
            lines.append(f"**Verdict:** {v.get('verdict', '?')} — {v.get('reason', '')}")
            lines.append("")

            # Comparison table at final checkpoint
            comparisons = cond_result.get("comparisons", [])
            if comparisons:
                final = comparisons[-1]
                lines.append(f"**Final checkpoint (step {final['step']}):**")
                lines.append("")
                lines.append("| Metric | Golden | Candidate | Delta | Within Tol |")
                lines.append("|--------|--------|-----------|-------|-----------|")
                for m in final["metrics"]:
                    tol_mark = "✓" if m["within_tolerance"] else "✗"
                    lines.append(
                        f"| {m['metric']} | {m['golden']:.6f} | {m['candidate']:.6f} | "
                        f"{m['rel_delta']} | {tol_mark} |")
                lines.append("")

                # RhoMaxId
                lines.append(f"**RhoMaxId:** golden={final['rhoMaxId_golden']}, "
                             f"candidate={final['rhoMaxId_candidate']} "
                             f"({'match ✓' if final['rhoMaxId_match'] else 'MISMATCH ✗'})")
                lines.append("")

    # Summary
    verdicts = ab_report.get("per_condition_verdicts", [])
    lines.extend([
        "---",
        "",
        "## Summary",
        "",
        f"- **Overall Verdict:** {verdict}",
        f"- **Conditions tested:** {len(verdicts)}",
        f"- **PASS:** {verdicts.count('PASS')}",
        f"- **IMPROVE:** {verdicts.count('IMPROVE')}",
        f"- **REGRESS:** {verdicts.count('REGRESS')}",
        f"- **MIXED:** {verdicts.count('MIXED')}",
    ])

    if verdict == "IMPROVE":
        lines.extend([
            "",
            "> **RECOMMENDATION:** This candidate shows improvement without regression. "
            "Consider promoting to a proof-packet-backed claim.",
        ])
    elif verdict == "REGRESS":
        lines.extend([
            "",
            "> **RECOMMENDATION:** This candidate introduces regressions. "
            "Do NOT merge without further investigation.",
        ])

    return "\n".join(lines)


def generate_proof_packet(ab_report: dict) -> str | None:
    """Generate a proof packet draft if the candidate shows improvement.

    Returns None if the candidate doesn't merit a proof packet (REGRESS/PASS).
    """
    verdict = ab_report.get("overall_verdict", "")
    if verdict not in ("IMPROVE", "MIXED"):
        return None

    candidate = ab_report["candidate"]
    now = datetime.now(timezone.utc)
    pp_id = f"PP-{now.strftime('%Y-%m-%d')}-evolve-{candidate['name']}"

    lines = [
        f"# {pp_id}",
        "",
        f"## CLAIM",
        f"Modifying `{candidate['target']}` via `{candidate['name']}` "
        f"({candidate['description']}) improves SOL engine behavior.",
        "",
        "## EVIDENCE",
        f"- A/B test run on {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Overall verdict: **{verdict}**",
        f"- Change type: {candidate['change_type']}",
        f"- Parameters: {json.dumps(candidate.get('parameters', {}), indent=2)}",
    ]

    # Add per-protocol evidence
    protocols = ab_report.get("protocols", {})
    for proto_name, proto_result in protocols.items():
        if proto_result.get("status") != "COMPLETE":
            continue
        for cond_label, cond_result in proto_result.get("conditions", {}).items():
            v = cond_result.get("verdict", {})
            lines.append(f"- Protocol `{proto_name}/{cond_label}`: {v.get('verdict', '?')} "
                         f"({v.get('improvements', 0)} improvements, {v.get('regressions', 0)} regressions)")

    lines.extend([
        "",
        "## ASSUMPTIONS / INVARIANTS",
        "- Sacred math: UNCHANGED (param_tune only)",
        "- Golden baselines generated from unmodified sol_engine.py",
        f"- Engine version: sol_engine.py-phase0",
        "",
        "## FALSIFICATION CRITERIA",
        f"- {candidate['name']} produces worse results than golden on any canonical protocol",
        "- The improvement is an artifact of specific initial conditions (test with different seeds)",
        "",
        "## STATUS",
        f"**Provisional** — generated by sol-evolve A/B test, pending human review.",
        "",
        "## SOURCES",
        f"- A/B test report: `tools/sol-evolve/` run output",
        f"- Golden baselines: `tests/regression/golden/`",
        f"- Candidate definition: `tools/sol-evolve/candidates.py::{candidate['name']}`",
    ])

    return "\n".join(lines)


def generate_change_proposal(ab_report: dict) -> dict:
    """Generate a structured change proposal from A/B results.

    Returns a dict suitable for machine consumption.
    """
    candidate = ab_report["candidate"]
    verdict = ab_report.get("overall_verdict", "UNKNOWN")

    proposal = {
        "proposal_id": f"EVO-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "candidate": candidate["name"],
        "verdict": verdict,
        "approved": verdict in ("PASS", "IMPROVE"),
        "requires_review": verdict == "MIXED",
        "rejected": verdict == "REGRESS",
        "change": {
            "type": candidate["change_type"],
            "target": candidate["target"],
            "parameters": candidate.get("parameters", {}),
        },
        "evidence": {
            "protocols_tested": list(ab_report.get("protocols", {}).keys()),
            "per_condition_verdicts": ab_report.get("per_condition_verdicts", []),
        },
        "action": _recommend_action(verdict),
    }

    return proposal


def _recommend_action(verdict: str) -> str:
    actions = {
        "PASS": "Safe to merge — no behavioral change detected",
        "IMPROVE": "Recommend merge — improvement detected with no regression",
        "REGRESS": "Do NOT merge — regression detected",
        "MIXED": "Requires human review — mixed results",
        "UNKNOWN": "Insufficient data — re-run with more protocols",
    }
    return actions.get(verdict, "Unknown verdict")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SOL Evolve — PR/Report Generator")
    parser.add_argument("report_json", nargs="?", type=str,
                        help="Path to A/B test report JSON")
    parser.add_argument("--candidate", type=str, default=None,
                        help="Run A/B test for this candidate and generate report")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Output directory for generated files")
    args = parser.parse_args()

    if args.candidate:
        # Run A/B test first
        from ab_test import ABTest
        test = ABTest(args.candidate)
        print(f"Running A/B test for {args.candidate}...")
        ab_report = test.run()
    elif args.report_json:
        ab_report = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
    else:
        parser.error("Provide either --candidate or a report JSON path")
        return

    out_dir = Path(args.out_dir) if args.out_dir else _SOL_ROOT / "data" / "evolve_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate_name = ab_report["candidate"]["name"]

    # Generate regression report
    report_md = generate_report(ab_report)
    report_path = out_dir / f"{candidate_name}_regression_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"Regression report: {report_path}")

    # Generate proof packet if applicable
    pp_md = generate_proof_packet(ab_report)
    if pp_md:
        pp_path = out_dir / f"{candidate_name}_proof_packet.md"
        pp_path.write_text(pp_md, encoding="utf-8")
        print(f"Proof packet draft: {pp_path}")

    # Generate change proposal
    proposal = generate_change_proposal(ab_report)
    proposal_path = out_dir / f"{candidate_name}_proposal.json"
    proposal_path.write_text(json.dumps(proposal, indent=2, default=str), encoding="utf-8")
    print(f"Change proposal: {proposal_path}")

    # Save full A/B report
    ab_path = out_dir / f"{candidate_name}_ab_report.json"
    ab_path.write_text(json.dumps(ab_report, indent=2, default=str), encoding="utf-8")

    print(f"\nVerdict: {ab_report['overall_verdict']}")
    print(f"Action:  {proposal['action']}")


if __name__ == "__main__":
    main()
