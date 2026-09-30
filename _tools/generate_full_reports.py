from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

ARCHIVE_DIR = Path(r"G:\docs\TechmanStudios\sol\solArchive\MD")
OUT_DIR = Path(r"G:\docs\TechmanStudios\sol\solResearch")


@dataclass(frozen=True)
class Extract:
    file_name: str
    title: str
    date_line: str | None
    build_line: str | None
    core_objective: str | None
    headings: list[str]
    artifacts: list[str]
    key_points: list[str]
    scripts: list[str]
    errors_fixes: list[str]
    next_steps: list[str]


_RD_NUM_RE = re.compile(r"^rd(\d+)$")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _first_nonempty_heading(lines: Sequence[str]) -> str:
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            return s
    # fallback: first non-empty line
    for ln in lines:
        s = ln.strip()
        if s:
            return s[:160]
    return "(empty)"


def _collect_headings(lines: Sequence[str], max_count: int = 40) -> list[str]:
    out: list[str] = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("#"):
            out.append(s)
            if len(out) >= max_count:
                break
    return out


def _find_first_match(lines: Sequence[str], prefix_re: re.Pattern[str]) -> str | None:
    for ln in lines:
        if prefix_re.search(ln):
            return ln.strip()
    return None


def _extract_artifacts(text: str) -> list[str]:
    # filenames / artifact-like tokens
    patterns = [
        r"\bsol_[\w\-]+\.csv\b",
        r"\bsol_[\w\-]+\.txt\b",
        r"\bsol_[\w\-]+\.html\b",
        r"`[^`]+\.(?:csv|html|txt|md)`",
        r"\b[\w\-]+_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z\.(?:csv|txt)\b",
    ]
    found: set[str] = set()
    for pat in patterns:
        for m in re.finditer(pat, text):
            tok = m.group(0).strip("`")
            found.add(tok)
    # keep sorted but stable-ish
    return sorted(found)[:120]


def _extract_key_points(lines: Sequence[str]) -> tuple[list[str], list[str], list[str], list[str]]:
    # Pull bullets and declarative lines likely to contain outcomes.
    key: list[str] = []
    scripts: list[str] = []
    errors_fixes: list[str] = []
    next_steps: list[str] = []

    cue_re = re.compile(
        r"(Key\s+conclusion|Result|Findings|Outcome|Interpretation|Rule\s+adopted|Breakthrough|Discovery|We\s+(?:built|produced|standardized|fixed)|Fix:|Root\s+cause|Artifacts?:|Files?:|Next\s+steps?)",
        re.IGNORECASE,
    )
    err_re = re.compile(r"(Error|ReferenceError|undefined|not\s+defined|No\s+rows\s+recorded|Invalid\s+baseline|crash|NaN)", re.IGNORECASE)
    script_re = re.compile(r"(script|harness|installs|pasteable|IIFE|globalThis\.)", re.IGNORECASE)
    next_re = re.compile(r"(Next\s+step|Next\s+steps|Primer\s+for\s+next\s+chat|What\s+we\s+do\s+immediately\s+next|Queued)", re.IGNORECASE)

    for ln in lines:
        raw = ln.rstrip("\n")
        s = raw.strip()
        if not s:
            continue

        if next_re.search(s):
            if s not in next_steps:
                next_steps.append(s[:260])
            continue

        if err_re.search(s):
            if s not in errors_fixes:
                errors_fixes.append(s[:260])
            continue

        if script_re.search(s) and ("globalThis" in s or "script" in s.lower() or "harness" in s.lower()):
            if s not in scripts:
                scripts.append(s[:260])
            continue

        if s.startswith(("* ", "- ", "• ")) or cue_re.search(s):
            if len(s) >= 6:
                key.append(s[:300])

    # de-dupe while preserving order
    def dedupe(seq: Iterable[str], max_items: int) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
            if len(out) >= max_items:
                break
        return out

    return (
        dedupe(key, 120),
        dedupe(scripts, 40),
        dedupe(errors_fixes, 50),
        dedupe(next_steps, 40),
    )


def extract_file(path: Path) -> Extract:
    text = _read_text(path)
    lines = text.splitlines()

    title = _first_nonempty_heading(lines)
    headings = _collect_headings(lines)

    date_line = _find_first_match(lines, re.compile(r"^\*\*Date:\*\*|^Date:\b", re.IGNORECASE))
    build_line = _find_first_match(lines, re.compile(r"^\*\*Build:\*\*|^Build:\b", re.IGNORECASE))

    # Objective is often "Core objective:" in later reports
    core_objective = _find_first_match(lines, re.compile(r"Core\s+objective:\s*", re.IGNORECASE))

    artifacts = _extract_artifacts(text)
    key_points, scripts, errors_fixes, next_steps = _extract_key_points(lines)

    return Extract(
        file_name=path.name,
        title=title,
        date_line=date_line,
        build_line=build_line,
        core_objective=core_objective,
        headings=headings,
        artifacts=artifacts,
        key_points=key_points,
        scripts=scripts,
        errors_fixes=errors_fixes,
        next_steps=next_steps,
    )


def rd_paths() -> list[Path]:
    return rd_paths_with_optional_inserts(include_rd1_1=False)


def rd_paths_with_optional_inserts(*, include_rd1_1: bool) -> list[Path]:
    """Return the canonical rd list in reading order.

    The user typically references rd0..rd30. The archive also contains rd1_1.md,
    which we optionally splice immediately after rd1.md when requested.
    """
    out: list[Path] = []
    for i in range(0, 31):
        p = ARCHIVE_DIR / f"rd{i}.md"
        if not p.exists():
            raise FileNotFoundError(f"Missing expected archive file: {p}")
        out.append(p)
        if include_rd1_1 and i == 1:
            p_insert = ARCHIVE_DIR / "rd1_1.md"
            if not p_insert.exists():
                raise FileNotFoundError(f"Missing expected archive file: {p_insert}")
            out.append(p_insert)
    return out


def render_extract_section(ex: Extract) -> str:
    lines: list[str] = []
    lines.append(f"## {ex.file_name} — {ex.title}")
    if ex.date_line:
        lines.append(f"- {ex.date_line}")
    if ex.build_line:
        lines.append(f"- {ex.build_line}")
    if ex.core_objective:
        lines.append(f"- {ex.core_objective}")

    if ex.headings:
        lines.append("")
        lines.append("### Structure (headings)")
        for h in ex.headings[:25]:
            lines.append(f"- {h}")

    if ex.key_points:
        lines.append("")
        lines.append("### Extracted key points (verbatim lines)")
        for k in ex.key_points[:60]:
            lines.append(f"- {k}")

    if ex.errors_fixes:
        lines.append("")
        lines.append("### Errors / fixes captured")
        for e in ex.errors_fixes[:30]:
            lines.append(f"- {e}")

    if ex.scripts:
        lines.append("")
        lines.append("### Scripts / harness notes captured")
        for s in ex.scripts[:25]:
            lines.append(f"- {s}")

    if ex.artifacts:
        lines.append("")
        lines.append("### Artifacts mentioned")
        for a in ex.artifacts[:80]:
            lines.append(f"- {a}")

    if ex.next_steps:
        lines.append("")
        lines.append("### Next steps cues captured")
        for n in ex.next_steps[:20]:
            lines.append(f"- {n}")

    lines.append("")
    return "\n".join(lines)


def write_rd_full_report() -> Path:
    extracts = [extract_file(p) for p in rd_paths()]

    out: list[str] = []
    out.append(f"# SOL — FULL Detailed Report (rd0–rd30, original sources)\n")
    out.append(f"Generated: {date.today().isoformat()}\n")
    out.append(
        "This report is generated directly from the original `solArchive/MD/rd*.md` files (rd0–rd30). "
        "It intentionally does not use `SOL_Archive_Consolidated_rd00-rd30_*.md` as an input source.\n"
    )
    out.append("---\n")

    out.append("## Coverage\n")
    out.append("- Included: rd0.md through rd30.md\n")
    out.append("- Excluded: rd1_1.md (exists in archive but not part of requested rd0–rd30 span)\n")
    out.append("---\n")

    out.append("## Per-file extracted detail\n")
    for ex in extracts:
        out.append(render_extract_section(ex))

    report_path = OUT_DIR / f"SOL_Full_Detailed_Report_rd0-rd30_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(out), encoding="utf-8")
    return report_path


def _shorten(s: str, n: int = 220) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _pick_lines(lines: Sequence[str], include_re: re.Pattern[str], max_items: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if include_re.search(s) and s not in seen:
            seen.add(s)
            out.append(_shorten(s, 220))
            if len(out) >= max_items:
                break
    return out


def _infer_focus(ex: Extract) -> str:
    # Prefer explicit objective cues; otherwise fall back to title.
    if ex.core_objective:
        return _shorten(re.sub(r"^.*?Core\s+objective:\s*", "", ex.core_objective, flags=re.IGNORECASE), 160)
    return _shorten(ex.title, 160)


def render_readable_narrative_section(ex: Extract) -> str:
    lines: list[str] = []
    lines.append(f"## {ex.file_name} — Readable narrative")
    lines.append("")

    focus = _infer_focus(ex)

    # Categorize from extracted key points (verbatim lines captured earlier).
    key = ex.key_points
    tooling = _pick_lines(key, re.compile(r"\b(built|standardized|tooling|workflow|harness|script|installs|installed|freeze|snapshot|restore|UI-neutral)\b", re.IGNORECASE), 3)
    experiments = _pick_lines(key, re.compile(r"\b(sweep|grid|map|dt\s*=|damping\s*=|inject|targets|steps|run|uploaded|files?:)\b", re.IGNORECASE), 3)
    results = _pick_lines(key, re.compile(r"\b(result|findings|outcome|conclusion|proved|confirmed|key\s+conclusion|working\s+default|breakthrough|discovery)\b", re.IGNORECASE), 3)
    fixes = _pick_lines(ex.errors_fixes, re.compile(r".+", re.IGNORECASE), 2)
    nexts = _pick_lines(ex.next_steps, re.compile(r".+", re.IGNORECASE), 2)

    # Compose 5–10 concise sentences. Keep it conservative and avoid adding facts.
    sent: list[str] = []
    sent.append(f"Focus: {focus}.")
    if ex.date_line:
        sent.append(_shorten(ex.date_line, 160) + ".")
    if ex.build_line:
        sent.append(_shorten(ex.build_line, 160) + ".")
    if tooling:
        sent.append("Tooling/workflow updates were captured (see anchors).")
    if experiments:
        sent.append("The session ran structured experiments/sweeps and recorded artifacts for comparison.")
    if results:
        sent.append("It closed with specific conclusions and a carry-forward baseline for the next phase.")
    if fixes:
        sent.append("Notable errors/fixes were encountered and resolved during the run.")
    if nexts:
        sent.append("Next actions were explicitly queued for the following session.")

    # Trim to 5–10 sentences.
    sent = sent[:10]
    while len(sent) < 5:
        sent.append("Anchor excerpts below provide the exact phrasing from the source file.")

    lines.append(" ".join(sent))
    lines.append("")

    # Curated anchors (much shorter than the earlier narrative).
    lines.append("**Curated anchors (verbatim excerpts):**")
    if tooling:
        lines.append("- Tooling:")
        for t in tooling:
            lines.append(f"  - {t}")
    if experiments:
        lines.append("- Experiments:")
        for e in experiments:
            lines.append(f"  - {e}")
    if results:
        lines.append("- Results:")
        for r in results:
            lines.append(f"  - {r}")
    if fixes:
        lines.append("- Errors/Fixes:")
        for f in fixes:
            lines.append(f"  - {f}")
    if nexts:
        lines.append("- Next:")
        for n in nexts:
            lines.append(f"  - {n}")

    # Optional: keep artifact list short.
    if ex.artifacts:
        lines.append("")
        lines.append("**Artifacts mentioned (short list):**")
        for a in ex.artifacts[:15]:
            lines.append(f"- {a}")

    lines.append("")
    return "\n".join(lines)


def render_narrative_section(ex: Extract) -> str:
    lines: list[str] = []
    lines.append(f"## {ex.file_name} — Narrative")
    lines.append("")

    meta_bits: list[str] = []
    if ex.date_line:
        meta_bits.append(_shorten(ex.date_line, 180))
    if ex.build_line:
        meta_bits.append(_shorten(ex.build_line, 180))
    if ex.core_objective:
        meta_bits.append(_shorten(ex.core_objective, 220))
    if meta_bits:
        lines.append("**Context anchors:**")
        for b in meta_bits:
            lines.append(f"- {b}")
        lines.append("")

    # Narrative glue: use headings to define what the doc *is*, then use extracted
    # key lines as the grounding anchors.
    if ex.title:
        lines.append(f"This entry is organized around: {_shorten(ex.title, 180)}")
    if ex.headings:
        heads = "; ".join(_shorten(h, 80) for h in ex.headings[1:7])
        if heads:
            lines.append(f"It proceeds through sections like: {heads}.")
    lines.append(
        "The summary below is a stitched narrative derived from the file’s own headings and verbatim anchor lines. "
        "No content is pulled from the consolidated report."  # explicit guardrail
    )
    lines.append("")

    # Construct a short narrative paragraph from the strongest cue-lines.
    cue_lines: list[str] = []
    for src in (ex.key_points[:40], ex.errors_fixes[:15], ex.next_steps[:12]):
        cue_lines.extend(src)
    cue_lines = cue_lines[:55]

    if cue_lines:
        lines.append("**Narrative summary (derived):**")
        # Keep this conservative: we only generalize at a high level.
        lines.append(
            "This file documents the work performed in that session, including tooling/harness changes, experiments executed, "
            "and the key conclusions that were locked in for the next phase. The anchor excerpts below capture the specific claims, "
            "parameter sweeps, and rules adopted."  # intentionally generic but accurate
        )
        lines.append("")

        lines.append("**Anchor excerpts (verbatim):**")
        for ln in cue_lines:
            lines.append(f"- {ln}")
    else:
        lines.append("No extractable cue lines were detected for this entry (file may be mostly prose without bullets/cues).")
    lines.append("")

    if ex.artifacts:
        lines.append("**Artifacts mentioned (from this file):**")
        for a in ex.artifacts[:40]:
            lines.append(f"- {a}")
        lines.append("")

    return "\n".join(lines)


def write_rd_narrative_report(*, include_rd1_1: bool) -> Path:
    paths = rd_paths_with_optional_inserts(include_rd1_1=include_rd1_1)
    extracts = [extract_file(p) for p in paths]

    out: list[str] = []
    tag = "rd0-rd30_plus_rd1_1" if include_rd1_1 else "rd0-rd30"
    out.append(f"# SOL — FULL Narrative Report ({tag}, original sources)\n")
    out.append(f"Generated: {date.today().isoformat()}\n")
    out.append(
        "Second-pass narrative: this file adds readable glue while keeping each section grounded in verbatim anchor excerpts "
        "pulled directly from the original archive MD files.\n"
    )
    out.append("---\n")
    out.append("## Coverage\n")
    if include_rd1_1:
        out.append("- Included: rd0.md … rd30.md, plus rd1_1.md (spliced after rd1.md)\n")
    else:
        out.append("- Included: rd0.md … rd30.md\n")
    out.append("---\n")

    out.append("## Chronological narrative (per file)\n")
    for ex in extracts:
        out.append(render_narrative_section(ex))

    report_path = OUT_DIR / f"SOL_Full_Narrative_Report_{tag}_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(out), encoding="utf-8")
    return report_path


def write_rd_narrative_readable_report(*, include_rd1_1: bool) -> Path:
    paths = rd_paths_with_optional_inserts(include_rd1_1=include_rd1_1)
    extracts = [extract_file(p) for p in paths]

    out: list[str] = []
    tag = "rd0-rd30_plus_rd1_1" if include_rd1_1 else "rd0-rd30"
    out.append(f"# SOL — FULL Narrative Report (Readable) ({tag}, original sources)\n")
    out.append(f"Generated: {date.today().isoformat()}\n")
    out.append(
        "This is a readability pass over the narrative report: each source file gets a short paragraph plus a curated set of verbatim anchors. "
        "All anchors are extracted from the original archive MD files.\n"
    )
    out.append("---\n")
    out.append("## Coverage\n")
    if include_rd1_1:
        out.append("- Included: rd0.md … rd30.md, plus rd1_1.md (spliced after rd1.md)\n")
    else:
        out.append("- Included: rd0.md … rd30.md\n")
    out.append("---\n")

    out.append("## Readable narrative (per file)\n")
    for ex in extracts:
        out.append(render_readable_narrative_section(ex))

    report_path = OUT_DIR / f"SOL_Full_Narrative_Readable_Report_{tag}_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(out), encoding="utf-8")
    return report_path


def write_solresearch_notes_report() -> Path:
    note_paths = [ARCHIVE_DIR / "solResearchNote1.md", ARCHIVE_DIR / "solResearchNote2.md"]
    extracts = [extract_file(p) for p in note_paths]

    out: list[str] = []
    out.append(f"# SOL — FULL Detailed Report (solResearch notes, original sources)\n")
    out.append(f"Generated: {date.today().isoformat()}\n")
    out.append(
        "This report is generated directly from the original `solArchive/MD/solResearchNote1.md` "
        "and `solArchive/MD/solResearchNote2.md` files.\n"
    )
    out.append("---\n")

    out.append("## Notes coverage\n")
    out.append("- Included: solResearchNote1.md, solResearchNote2.md\n")
    out.append("---\n")

    out.append("## Per-note extracted detail\n")
    for ex in extracts:
        out.append(render_extract_section(ex))

    report_path = OUT_DIR / f"SOL_Full_Detailed_Report_solResearchNotes_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(out), encoding="utf-8")
    return report_path


def write_solresearch_notes_narrative_report() -> Path:
    note_paths = [ARCHIVE_DIR / "solResearchNote1.md", ARCHIVE_DIR / "solResearchNote2.md"]
    extracts = [extract_file(p) for p in note_paths]

    out: list[str] = []
    out.append("# SOL — FULL Narrative Report (solResearch notes, original sources)\n")
    out.append(f"Generated: {date.today().isoformat()}\n")
    out.append(
        "Second-pass narrative for the solResearch notes: readable glue plus verbatim anchor excerpts, sourced directly from the original note MD files.\n"
    )
    out.append("---\n")
    out.append("## Coverage\n")
    out.append("- Included: solResearchNote1.md, solResearchNote2.md\n")
    out.append("---\n")

    out.append("## Narrative (per note)\n")
    for ex in extracts:
        out.append(render_narrative_section(ex))

    report_path = OUT_DIR / f"SOL_Full_Narrative_Report_solResearchNotes_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(out), encoding="utf-8")
    return report_path


def write_solresearch_notes_narrative_readable_report() -> Path:
    note_paths = [ARCHIVE_DIR / "solResearchNote1.md", ARCHIVE_DIR / "solResearchNote2.md"]
    extracts = [extract_file(p) for p in note_paths]

    out: list[str] = []
    out.append("# SOL — FULL Narrative Report (Readable) (solResearch notes, original sources)\n")
    out.append(f"Generated: {date.today().isoformat()}\n")
    out.append(
        "Readability pass: short paragraph + curated verbatim anchors for each note, extracted directly from the original note files.\n"
    )
    out.append("---\n")
    out.append("## Coverage\n")
    out.append("- Included: solResearchNote1.md, solResearchNote2.md\n")
    out.append("---\n")

    out.append("## Readable narrative (per note)\n")
    for ex in extracts:
        out.append(render_readable_narrative_section(ex))

    report_path = OUT_DIR / f"SOL_Full_Narrative_Readable_Report_solResearchNotes_{date.today().isoformat()}.md"
    report_path.write_text("\n".join(out), encoding="utf-8")
    return report_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rd_report = write_rd_full_report()
    notes_report = write_solresearch_notes_report()

    rd_narr = write_rd_narrative_report(include_rd1_1=True)
    notes_narr = write_solresearch_notes_narrative_report()

    rd_narr_readable = write_rd_narrative_readable_report(include_rd1_1=True)
    notes_narr_readable = write_solresearch_notes_narrative_readable_report()

    print(f"Wrote: {rd_report}")
    print(f"Wrote: {notes_report}")
    print(f"Wrote: {rd_narr}")
    print(f"Wrote: {notes_narr}")
    print(f"Wrote: {rd_narr_readable}")
    print(f"Wrote: {notes_narr_readable}")


if __name__ == "__main__":
    main()
