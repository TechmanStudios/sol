#!/usr/bin/env python3
"""
SOL Cortex — Memory Consolidation

Reads cortex session output, extracts findings, generates candidate proof
packets, and updates the consolidation index.

Usage:
    python consolidate.py <session_dir>
    python consolidate.py data/cortex_sessions/CX-20260208-040833
    python consolidate.py --all          # consolidate all un-processed sessions
    python consolidate.py --list         # list sessions and consolidation status
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent  # tools/sol-cortex -> sol/
_SESSIONS_DIR = _SOL_ROOT / "data" / "cortex_sessions"
_PROOF_PACKETS_DIR = _SOL_ROOT / "solKnowledge" / "proof_packets"
_CONSOLIDATED_DIR = _SOL_ROOT / "solKnowledge" / "consolidated"
_CONSOLIDATION_LOG = _SOL_ROOT / "data" / "consolidation_log.jsonl"

# Optional hippocampus integration
_HIPPOCAMPUS_AVAILABLE = False
try:
    _HIPPO_DIR = str(_SOL_ROOT / "tools" / "sol-hippocampus")
    if _HIPPO_DIR not in sys.path:
        sys.path.insert(0, _HIPPO_DIR)
    from memory_store import write_trace, compact as memory_compact
    from meta_learner import MetaLearner
    _HIPPOCAMPUS_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    """Load JSON, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return None


def _load_jsonl(path: Path) -> list[dict]:
    """Load JSONL, return list of dicts."""
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return entries


def _write_markdown(path: Path, content: str):
    """Write markdown file, creating dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [OK] Wrote {path.relative_to(_SOL_ROOT)}")


def _append_jsonl(path: Path, entry: dict):
    """Append a dict as a JSONL line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _is_consolidated(session_id: str) -> bool:
    """Check if a session has already been consolidated."""
    if not _CONSOLIDATION_LOG.exists():
        return False
    with open(_CONSOLIDATION_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("session_id") == session_id:
                    return True
            except json.JSONDecodeError:
                continue
    return False


# ---------------------------------------------------------------------------
# Proof Packet Generation
# ---------------------------------------------------------------------------

def _generate_proof_packet(session_id: str, hypothesis: dict,
                           run_bundle_md: str, sanity: dict) -> str:
    """Generate a candidate proof packet from a cortex hypothesis + results."""

    h_id = hypothesis.get("id", "H-???")
    question = hypothesis.get("question", "Unknown question")
    knob = hypothesis.get("knob", "unknown")
    knob_values = hypothesis.get("knob_values", [])
    template = hypothesis.get("template", "unknown")
    falsifiers = hypothesis.get("falsifiers", [])
    source_gap = hypothesis.get("source_gap", {})
    gap_desc = source_gap.get("description", "No gap description")
    claim_id = source_gap.get("claim_id", None)

    injection = hypothesis.get("injection", {})
    inj_label = injection.get("label", "none")
    inj_amount = injection.get("amount", 0)

    sanity_passed = sanity.get("sanity_passed", False)
    anomalies = sanity.get("anomalies", [])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pp_name = f"PP-{now}-cortex-{session_id}-{h_id.lower()}-{knob}"

    lines = [
        f"# Proof Packet: {pp_name}",
        "",
        f"**Generated:** {now}  ",
        f"**Source:** Cortex session `{session_id}`, hypothesis `{h_id}`  ",
        f"**Status:** CANDIDATE (auto-generated, requires review)  ",
        "",
        "---",
        "",
        "## Claim Anchors",
        "",
    ]

    if claim_id:
        lines.append(f"- **Primary claim:** {claim_id}")
    else:
        lines.append("- **Primary claim:** _(no claim anchor — exploratory)_")

    lines.extend([
        f"- **Gap addressed:** {gap_desc}",
        "",
        "## Hypothesis",
        "",
        f"- **Type:** {template}",
        f"- **Question:** {question}",
        f"- **Independent variable:** `{knob}` at {knob_values}",
        f"- **Injection:** {inj_label} → {inj_amount}",
        "",
        "## Falsifiers",
        "",
    ])

    for f_item in falsifiers:
        lines.append(f"- {f_item}")

    lines.extend([
        "",
        "## Results",
        "",
        f"- **Sanity:** {'PASS' if sanity_passed else 'FAIL'}",
    ])

    if anomalies:
        lines.append("- **Anomalies:**")
        for a in anomalies:
            lines.append(f"  - {a}")

    lines.extend([
        "",
        "### Run Bundle (embedded)",
        "",
        run_bundle_md,
        "",
        "---",
        "",
        "## Promotion Checklist",
        "",
        "- [ ] Results reviewed by operator",
        "- [ ] Sanity checks confirmed",
        "- [ ] Falsifiers evaluated — none triggered",
        "- [ ] Linked to claim ledger entry",
        "- [ ] Proof packet moved from CANDIDATE to PROMOTED",
        "",
        "---",
        f"_Auto-generated by `consolidate.py` from session `{session_id}`_",
    ])

    return "\n".join(lines), pp_name


# ---------------------------------------------------------------------------
# Session Consolidation
# ---------------------------------------------------------------------------

def consolidate_session(session_dir: Path) -> dict:
    """
    Consolidate a single cortex session.

    Returns a consolidation summary dict.
    """
    session_id = session_dir.name
    print(f"\n{'='*60}")
    print(f"Consolidating session: {session_id}")
    print(f"{'='*60}")

    if _is_consolidated(session_id):
        print(f"  [SKIP] Already consolidated")
        return {"session_id": session_id, "status": "skipped", "reason": "already_consolidated"}

    # Load session data
    summary = _load_json(session_dir / "summary.json")
    hypotheses = _load_json(session_dir / "hypotheses.json")
    session_log = _load_jsonl(session_dir / "session.jsonl")

    if not summary:
        print("  [ERROR] No summary.json found")
        return {"session_id": session_id, "status": "error", "reason": "no_summary"}

    if not hypotheses:
        print("  [WARN] No hypotheses.json found")
        hypotheses = []

    if summary.get("dry_run", False):
        print("  [SKIP] Dry-run session — no results to consolidate")
        return {"session_id": session_id, "status": "skipped", "reason": "dry_run"}

    # Process each hypothesis with results
    sanity_map = {}
    for sr in summary.get("sanity_results", []):
        sanity_map[sr["hypothesis"]] = sr

    proof_packets_generated = []
    findings = []

    for hyp in hypotheses:
        h_id = hyp.get("id", "")
        h_key = h_id.lower().replace("-", "-")

        # Find the run bundle
        run_dir = session_dir / "runs" / h_key
        bundle_path = run_dir / f"{h_key}_run_bundle.md"

        if not bundle_path.exists():
            print(f"  [WARN] No run bundle for {h_id} at {bundle_path}")
            continue

        run_bundle_md = bundle_path.read_text(encoding="utf-8")
        sanity = sanity_map.get(h_id, {"sanity_passed": False, "anomalies": ["no sanity data"]})

        # Generate candidate proof packet
        pp_content, pp_name = _generate_proof_packet(session_id, hyp, run_bundle_md, sanity)

        pp_path = _PROOF_PACKETS_DIR / f"{pp_name}.md"
        _write_markdown(pp_path, pp_content)
        proof_packets_generated.append(pp_name)

        # Extract finding summary
        finding = {
            "hypothesis_id": h_id,
            "question": hyp.get("question", ""),
            "knob": hyp.get("knob", ""),
            "sanity_passed": sanity.get("sanity_passed", False),
            "proof_packet": pp_name,
            "source_gap": hyp.get("source_gap", {}).get("description", ""),
            "claim_id": hyp.get("source_gap", {}).get("claim_id"),
        }
        findings.append(finding)

    # Update consolidation index
    _update_consolidation_index(session_id, findings, proof_packets_generated)

    # Log consolidation
    log_entry = {
        "session_id": session_id,
        "consolidated_at": datetime.now(timezone.utc).isoformat(),
        "protocols_run": summary.get("protocols_run", 0),
        "total_steps": summary.get("total_steps", 0),
        "hypotheses_processed": len(findings),
        "proof_packets_generated": proof_packets_generated,
        "status": "consolidated",
    }
    _append_jsonl(_CONSOLIDATION_LOG, log_entry)

    # Hippocampus: write memory traces for each finding
    if _HIPPOCAMPUS_AVAILABLE and proof_packets_generated:
        try:
            for f in findings:
                # write_trace(session_id, action, node=None, edges=None)
                # Action = "finding" with metadata encoded in the action string
                # for now, we pass the finding as a JSON-encoded action tag
                action = f"finding:{f['hypothesis_id']}:{f['knob']}"
                write_trace(session_id, action)

            # Update meta-learner with proof_packet = True
            ml = MetaLearner()
            for hyp in hypotheses:
                h_id = hyp.get("id", "")
                sr = sanity_map.get(h_id, {})
                interp = {
                    "sanity_passed": sr.get("sanity_passed", False),
                    "proof_packet_promoted": True,
                    "novel_basin_discovered": False,
                    "informative_variation": False,
                }
                ml.record(session_id, hyp, interp)

            # Compact memory graph
            memory_compact()
            print(f"  [HIPPO] Memory traces written and compacted for {session_id}")
        except Exception as e:
            print(f"  [HIPPO WARN] Memory integration error: {e}")

    print(f"\n  Summary:")
    print(f"    Hypotheses processed: {len(findings)}")
    print(f"    Proof packets generated: {len(proof_packets_generated)}")
    for pp in proof_packets_generated:
        print(f"      - {pp}")

    return log_entry


# ---------------------------------------------------------------------------
# Consolidation Index Update
# ---------------------------------------------------------------------------

def _update_consolidation_index(session_id: str, findings: list[dict],
                                proof_packets: list[str]):
    """
    Append a section to the consolidation index documenting newly generated
    proof packets from a cortex session.
    """
    if not findings:
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Find the latest consolidation index
    index_files = sorted(_CONSOLIDATED_DIR.glob("SOL_Knowledge_Consolidation_Index_*.md"))
    if not index_files:
        print("  [WARN] No consolidation index found — creating new one")
        index_path = _CONSOLIDATED_DIR / f"SOL_Knowledge_Consolidation_Index_{now}.md"
        _write_markdown(index_path, f"# SOL Knowledge — Consolidation Index (as of {now})\n\n")
        index_files = [index_path]

    index_path = index_files[-1]

    # Build the appendix section
    lines = [
        "",
        f"## Cortex Session: {session_id} (consolidated {now})",
        "",
    ]

    for f in findings:
        pp_name = f["proof_packet"]
        claim = f["claim_id"] or "exploratory"
        status = "PASS" if f["sanity_passed"] else "FAIL"
        lines.append(f"- [{pp_name}.md](solKnowledge/proof_packets/{pp_name}.md)")
        lines.append(f"  - Question: {f['question']}")
        lines.append(f"  - Claim: {claim} | Sanity: {status}")
        lines.append(f"  - Gap: {f['source_gap']}")
        lines.append("")

    # Append to index
    with open(index_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"  [OK] Updated consolidation index: {index_path.name}")


# ---------------------------------------------------------------------------
# List Sessions
# ---------------------------------------------------------------------------

def list_sessions():
    """List all cortex sessions and their consolidation status."""
    if not _SESSIONS_DIR.exists():
        print("No cortex sessions found.")
        return

    sessions = sorted(d for d in _SESSIONS_DIR.iterdir() if d.is_dir())
    if not sessions:
        print("No cortex sessions found.")
        return

    print(f"\n{'Session ID':<30} {'Protocols':>10} {'Steps':>10} {'Status':<15}")
    print("-" * 70)

    for sd in sessions:
        sid = sd.name
        summary = _load_json(sd / "summary.json")
        consolidated = _is_consolidated(sid)

        if summary:
            protocols = summary.get("protocols_run", "?")
            steps = summary.get("total_steps", "?")
            dry = " (dry-run)" if summary.get("dry_run") else ""
        else:
            protocols = "?"
            steps = "?"
            dry = ""

        status = "consolidated" if consolidated else "pending"
        print(f"{sid:<30} {str(protocols):>10} {str(steps):>10} {status + dry:<15}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SOL Cortex — Memory Consolidation",
        epilog="Reads cortex session output and generates candidate proof packets.",
    )
    parser.add_argument(
        "session_dir", nargs="?", default=None,
        help="Path to a cortex session directory (e.g., data/cortex_sessions/CX-20260208-040833)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Consolidate all un-processed sessions",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_sessions",
        help="List sessions and consolidation status",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-consolidate even if already processed",
    )

    args = parser.parse_args()

    if args.list_sessions:
        list_sessions()
        return

    if args.all:
        if not _SESSIONS_DIR.exists():
            print("No cortex sessions directory found.")
            sys.exit(1)

        sessions = sorted(d for d in _SESSIONS_DIR.iterdir() if d.is_dir())
        results = []
        for sd in sessions:
            if args.force or not _is_consolidated(sd.name):
                results.append(consolidate_session(sd))
            else:
                print(f"[SKIP] {sd.name} — already consolidated (use --force to re-process)")

        # Summary
        consolidated = [r for r in results if r.get("status") == "consolidated"]
        skipped = [r for r in results if r.get("status") == "skipped"]
        errors = [r for r in results if r.get("status") == "error"]
        print(f"\nBatch complete: {len(consolidated)} consolidated, {len(skipped)} skipped, {len(errors)} errors")
        return

    if args.session_dir:
        session_path = Path(args.session_dir).resolve()
        if not session_path.exists():
            # Try relative to SOL root
            session_path = _SOL_ROOT / args.session_dir
        if not session_path.exists():
            print(f"Session directory not found: {args.session_dir}")
            sys.exit(1)

        consolidate_session(session_path)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
