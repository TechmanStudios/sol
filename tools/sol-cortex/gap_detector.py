"""
SOL Cortex — Knowledge-Gap Detector
====================================
Scans the knowledge base (proof packets, claim ledger, consolidation index)
to identify:
  1. Unpromoted claims (claims without proof packets)
  2. Weak evidence (claims with UNKNOWN invariants)
  3. Unfalsified claims (claims whose falsifiers haven't been tested)
  4. Unexplored parameter regions (knobs mentioned but not swept)
  5. Replication opportunities (dashboard results not yet reproduced headless)

Usage:
    from gap_detector import scan_knowledge, rank_gaps
    gaps = scan_knowledge()
    ranked = rank_gaps(gaps)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Paths relative to sol workspace root
_SOL_ROOT = Path(__file__).parent.parent.parent  # tools/sol-cortex → sol/
_KNOWLEDGE = _SOL_ROOT / "solKnowledge"
_PROOF_PACKETS = _KNOWLEDGE / "proof_packets"
_WORKING = _KNOWLEDGE / "working"
_CONSOLIDATED = _KNOWLEDGE / "consolidated"

# The claim ledger lives inside the master research doc
_MASTER_PROOF = _WORKING / "sol_fullResearch_MASTER_PROOF_CLEAN.md"
_CONSOLIDATION_INDEX = _CONSOLIDATED / "SOL_Knowledge_Consolidation_Index_2026-01-24.md"


@dataclass
class Claim:
    """A claim from the claim ledger."""
    id: str                     # e.g. "CL-1"
    status: str                 # "Robust", "Supported", "Provisional"
    text: str                   # One-line claim
    evidence: str = ""          # Evidence summary
    falsifier: str = ""         # Falsification criterion
    proof_packets: list[str] = field(default_factory=list)  # Associated PP filenames
    unknowns: list[str] = field(default_factory=list)       # Things marked [UNKNOWN]


@dataclass
class ProofPacket:
    """Parsed proof packet metadata."""
    filename: str
    claim_text: str = ""
    status: str = ""            # "robust", "provisional", etc.
    has_unknowns: bool = False
    unknown_fields: list[str] = field(default_factory=list)
    falsifier: str = ""
    sources: list[str] = field(default_factory=list)


@dataclass
class Gap:
    """A detected knowledge gap."""
    gap_type: str               # "unpromoted", "weak_evidence", "unfalsified",
                                # "unexplored_param", "replication", "headless_baseline"
    priority: int               # 1 (highest) to 5 (lowest)
    claim_id: str | None = None
    description: str = ""
    suggested_action: str = ""
    metadata: dict = field(default_factory=dict)


def parse_claim_ledger(master_path: Path | None = None) -> list[Claim]:
    """Parse CL-1..CL-N entries from the master research document."""
    path = master_path or _MASTER_PROOF
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8", errors="replace")
    claims = []

    # Pattern: **CL-N (Status): Claim text.**
    pattern = re.compile(
        r'\*\*(?P<id>CL-\d+)\s*\((?P<status>[^)]+)\):\s*(?P<text>.+?)\*\*',
        re.MULTILINE
    )

    for m in pattern.finditer(text):
        claim = Claim(
            id=m.group("id"),
            status=m.group("status").strip(),
            text=m.group("text").strip().rstrip("."),
        )

        # Grab the lines after the claim until the next CL- or ## heading
        start = m.end()
        next_claim = pattern.search(text, start)
        next_heading = re.search(r'^## ', text[start:], re.MULTILINE)
        end = len(text)
        if next_claim:
            end = min(end, next_claim.start())
        if next_heading:
            end = min(end, start + next_heading.start())

        block = text[start:end]

        # Extract evidence
        ev_match = re.search(r'- Evidence:\s*(.+)', block)
        if ev_match:
            claim.evidence = ev_match.group(1).strip()

        # Extract falsifier
        fa_match = re.search(r'- Falsif[yi]:\s*(.+)', block)
        if fa_match:
            claim.falsifier = fa_match.group(1).strip()

        # Find [UNKNOWN] markers
        unknowns = re.findall(r'\[UNKNOWN\]', block, re.IGNORECASE)
        claim.unknowns = [f"[UNKNOWN] in {claim.id} evidence block"] * len(unknowns)

        # Find linked proof packets
        pp_refs = re.findall(r'PP-[\w-]+\.md', block)
        claim.proof_packets = pp_refs

        claims.append(claim)

    return claims


def scan_proof_packets(pp_dir: Path | None = None) -> list[ProofPacket]:
    """Scan all proof packet files and extract metadata."""
    directory = pp_dir or _PROOF_PACKETS
    if not directory.exists():
        return []

    packets = []
    for pp_file in sorted(directory.glob("PP-*.md")):
        text = pp_file.read_text(encoding="utf-8", errors="replace")
        pp = ProofPacket(filename=pp_file.name)

        # Claim
        claim_match = re.search(r'## CLAIM\s*\n(.+?)(?=\n## |\Z)', text, re.DOTALL)
        if claim_match:
            pp.claim_text = claim_match.group(1).strip()

        # Status
        status_match = re.search(r'## STATUS\s*\n(.+)', text)
        if status_match:
            pp.status = status_match.group(1).strip().lower()

        # Unknowns
        unknown_lines = re.findall(r'.*\[UNKNOWN\].*|.*unknown.*|.*not recorded.*',
                                    text, re.IGNORECASE)
        pp.has_unknowns = len(unknown_lines) > 0
        pp.unknown_fields = [line.strip() for line in unknown_lines[:5]]

        # Falsifier
        falsify_match = re.search(r'## FALSIFY\s*\n(.+?)(?=\n## |\Z)', text, re.DOTALL)
        if falsify_match:
            pp.falsifier = falsify_match.group(1).strip()

        # Sources
        source_match = re.search(r'## SOURCES?\s*\n(.+?)(?=\n## |\Z)', text, re.DOTALL)
        if source_match:
            pp.sources = [s.strip() for s in source_match.group(1).strip().split("\n") if s.strip()]

        packets.append(pp)

    return packets


def _link_claims_to_packets(claims: list[Claim],
                             packets: list[ProofPacket]) -> dict[str, list[str]]:
    """Build a map from claim ID to proof packet filenames.
    Uses both explicit references and text-matching heuristics."""
    pp_names = {pp.filename for pp in packets}
    cl_to_pp: dict[str, list[str]] = {c.id: list(c.proof_packets) for c in claims}

    # Also scan consolidation index for additional links
    idx_path = _CONSOLIDATION_INDEX
    if idx_path.exists():
        idx_text = idx_path.read_text(encoding="utf-8", errors="replace")
        for c in claims:
            # Find any PP references near this claim's keywords
            keywords = c.text.lower().split()[:3]
            for pp_name in pp_names:
                if pp_name in idx_text and pp_name not in cl_to_pp.get(c.id, []):
                    # Heuristic: check if any keyword appears near the PP reference
                    for kw in keywords:
                        if len(kw) > 3 and kw in pp_name.lower():
                            cl_to_pp.setdefault(c.id, []).append(pp_name)
                            break

    return cl_to_pp


def scan_knowledge() -> list[Gap]:
    """Main entry point: scan the full knowledge base and return detected gaps."""
    claims = parse_claim_ledger()
    packets = scan_proof_packets()
    cl_to_pp = _link_claims_to_packets(claims, packets)

    gaps: list[Gap] = []

    # --- Gap Type 1: Unpromoted claims ---
    for c in claims:
        associated = cl_to_pp.get(c.id, [])
        if not associated:
            gaps.append(Gap(
                gap_type="unpromoted",
                priority=2,
                claim_id=c.id,
                description=f"{c.id} ({c.status}): {c.text} — no proof packet found",
                suggested_action=f"Design and run a protocol to test: {c.text}",
                metadata={"claim_status": c.status, "falsifier": c.falsifier},
            ))

    # --- Gap Type 2: Weak evidence (UNKNOWN invariants in proof packets) ---
    for pp in packets:
        if pp.has_unknowns:
            gaps.append(Gap(
                gap_type="weak_evidence",
                priority=3,
                description=f"{pp.filename}: has UNKNOWN fields — {pp.unknown_fields[:3]}",
                suggested_action=f"Re-run {pp.filename}'s protocol with full invariant recording",
                metadata={"packet": pp.filename, "unknowns": pp.unknown_fields},
            ))

    # --- Gap Type 3: Unfalsified claims (falsifiers exist but haven't been tested) ---
    for c in claims:
        if c.falsifier and c.status != "Robust":
            gaps.append(Gap(
                gap_type="unfalsified",
                priority=3,
                claim_id=c.id,
                description=f"{c.id}: falsifier not yet tested — {c.falsifier[:100]}",
                suggested_action=f"Design a protocol to explicitly test falsifier for {c.id}",
                metadata={"falsifier": c.falsifier},
            ))

    # --- Gap Type 4: Headless replication opportunities ---
    # All existing proof packets were from Selenium/dashboard runs.
    # None have been replicated with headless sol-core.
    for pp in packets:
        gaps.append(Gap(
            gap_type="replication",
            priority=4,
            description=f"{pp.filename}: not yet replicated with headless sol-core",
            suggested_action=f"Replicate {pp.filename} protocol using auto_run.py",
            metadata={"packet": pp.filename, "original_claim": pp.claim_text[:80]},
        ))

    # --- Gap Type 5: Headless baseline establishment ---
    # We need golden baselines from sol-core for regression testing
    gaps.append(Gap(
        gap_type="headless_baseline",
        priority=2,
        description="No golden baselines exist for headless sol-core regression testing",
        suggested_action="Run standard injection protocols and save as golden reference outputs",
        metadata={"needed_for": "Phase 3 (sol-evolve) regression suite"},
    ))

    # --- Gap Type 6: Unexplored parameter regions ---
    # Known knobs that haven't been swept in headless mode
    unexplored = [
        ("c_press", "Pressure coefficient — not swept in headless", [0.01, 0.05, 0.1, 0.2, 0.5]),
        ("dt", "Time step — proven in dashboard, not headless", [0.08, 0.10, 0.12, 0.16]),
        ("psi_diffusion", "Psi diffusion rate — never swept systematically", [0.2, 0.4, 0.6, 0.8, 1.0]),
        ("conductance_gamma", "Conductance psi-sensitivity — never swept", [0.25, 0.5, 0.75, 1.0]),
    ]
    for param, desc, suggested_range in unexplored:
        gaps.append(Gap(
            gap_type="unexplored_param",
            priority=4,
            description=f"{param}: {desc}",
            suggested_action=f"Sweep {param} across {suggested_range}",
            metadata={"param": param, "range": suggested_range},
        ))

    # --- Gap Type 7: Open questions from proof packets (Phase 4) ---
    # Parse open questions and create high-priority gaps so the cortex
    # directly targets them instead of waiting for random selection.
    oq_gaps = _scan_open_questions()
    gaps.extend(oq_gaps)

    return gaps


def _scan_open_questions() -> list[Gap]:
    """Scan proof packets for open questions and convert to gaps.

    Open questions in domain packets and raw proof packets represent
    specific, already-identified research threads.  Turning them into
    priority-1 gaps ensures the cortex directly designs experiments
    to address them, closing the question → experiment → answer cycle.
    """
    questions: list[Gap] = []
    seen_qs: set[str] = set()  # dedup by first 80 chars

    # Scan domain packets
    _domains = _PROOF_PACKETS / "domains"
    scan_dirs: list[Path] = []
    if _domains.is_dir():
        scan_dirs.append(_domains)
    if _PROOF_PACKETS.is_dir():
        scan_dirs.append(_PROOF_PACKETS)

    for sdir in scan_dirs:
        for pp_path in sorted(sdir.glob("*.md")):
            try:
                text = pp_path.read_text(encoding="utf-8")
            except Exception:
                continue

            in_q_section = False
            for line in text.split("\n"):
                if "Remaining Open Questions" in line or "Open Questions" in line:
                    in_q_section = True
                    continue
                if in_q_section:
                    stripped = line.strip()
                    # End of section
                    if stripped.startswith("---") or (
                        stripped.startswith("#") and "Open" not in stripped
                    ):
                        break
                    # Numbered item
                    if stripped and stripped[0].isdigit() and "." in stripped[:4]:
                        if "[RESOLVED]" in stripped:
                            continue
                        # Remove number prefix
                        q_text = re.sub(r'^\d+\.\s*', '', stripped)
                        q_key = q_text[:80].lower()
                        if q_key in seen_qs:
                            continue
                        seen_qs.add(q_key)

                        # Infer parameter from question text
                        param = None
                        for p in ("damping", "c_press", "dt", "psi",
                                  "w0", "injection", "topology", "entropy"):
                            if p.lower() in q_text.lower():
                                param = p
                                break

                        questions.append(Gap(
                            gap_type="open_question",
                            priority=1,  # highest priority
                            description=f"Open Q: {q_text[:150]}",
                            suggested_action=(
                                f"Design an experiment to answer: {q_text[:120]}"
                            ),
                            metadata={
                                "source": pp_path.name,
                                "question": q_text,
                                "param": param,
                            },
                        ))

    return questions


def rank_gaps(gaps: list[Gap]) -> list[Gap]:
    """Rank gaps by priority (ascending = most important first).
    Within same priority, order: open_question > unpromoted > headless_baseline >
    weak_evidence > unfalsified > replication > unexplored.
    """
    type_order = {
        "open_question": 0,
        "unpromoted": 1,
        "headless_baseline": 2,
        "weak_evidence": 3,
        "unfalsified": 4,
        "replication": 5,
        "unexplored_param": 6,
    }
    return sorted(gaps, key=lambda g: (g.priority, type_order.get(g.gap_type, 99)))


def summarize_gaps(gaps: list[Gap]) -> str:
    """Human-readable summary of detected gaps."""
    lines = [f"=== Knowledge Gap Scan ({len(gaps)} gaps detected) ===", ""]

    by_type: dict[str, list[Gap]] = {}
    for g in gaps:
        by_type.setdefault(g.gap_type, []).append(g)

    for gtype, glist in by_type.items():
        lines.append(f"[{gtype}] ({len(glist)} gaps)")
        for g in glist[:5]:  # Show top 5 per type
            lines.append(f"  P{g.priority}: {g.description}")
            lines.append(f"       → {g.suggested_action}")
        if len(glist) > 5:
            lines.append(f"  ... and {len(glist) - 5} more")
        lines.append("")

    return "\n".join(lines)


# ---- CLI ---------------------------------------------------------------

if __name__ == "__main__":
    gaps = scan_knowledge()
    ranked = rank_gaps(gaps)
    print(summarize_gaps(ranked))
    print(f"\nTop 5 next actions:")
    for i, g in enumerate(ranked[:5], 1):
        print(f"  {i}. [{g.gap_type}] P{g.priority}: {g.suggested_action}")
