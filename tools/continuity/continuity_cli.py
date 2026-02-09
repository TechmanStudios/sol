#!/usr/bin/env python3
"""Continuity memory helper (repo-backed).

Stores:
- durable project memory in Markdown (generated)
- append-only session breadcrumbs in JSONL

Designed to be dependency-free and safe to run from VS Code Tasks.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_KNOWLEDGE_DIR = Path("knowledge") / "continuity"
DEFAULT_PROJECT_MEMORY = DEFAULT_KNOWLEDGE_DIR / "project_memory.md"
DEFAULT_SESSION_NOTES = DEFAULT_KNOWLEDGE_DIR / "session_notes.jsonl"

CURATED_START = "<!-- CONTINUITY_CURATED_START -->"
CURATED_END = "<!-- CONTINUITY_CURATED_END -->"
DRAFT_START = "<!-- CONTINUITY_NEXT_STEPS_DRAFT_START -->"
DRAFT_END = "<!-- CONTINUITY_NEXT_STEPS_DRAFT_END -->"
AUTO_START = "<!-- CONTINUITY_AUTO_START -->"
AUTO_END = "<!-- CONTINUITY_AUTO_END -->"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    _ensure_parent(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return []

    def _gen() -> Iterable[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    return _gen()


def init_memory(base_dir: Path) -> tuple[Path, Path]:
    knowledge_dir = base_dir
    project_memory = knowledge_dir / "project_memory.md"
    session_notes = knowledge_dir / "session_notes.jsonl"

    knowledge_dir.mkdir(parents=True, exist_ok=True)

    if not project_memory.exists():
        project_memory.write_text(
            """# Project Memory (Continuity)

This file is generated from repo-backed continuity notes.

Run:
- `python tools/continuity/continuity_cli.py refresh` to rebuild it
""",
            encoding="utf-8",
        )

    if not session_notes.exists():
        session_notes.write_text("", encoding="utf-8")

    return project_memory, session_notes


@dataclass
class AddArgs:
    title: str
    note: str
    tags: list[str]
    source: str


def add_note(session_notes: Path, args: AddArgs) -> None:
    entry: dict[str, Any] = {
        "ts": _utc_now_iso(),
        "title": args.title,
        "note": args.note,
        "tags": args.tags,
        "source": args.source,
    }
    _append_jsonl(session_notes, entry)


def tail_notes(session_notes: Path, limit: int) -> list[dict[str, Any]]:
    items = list(_iter_jsonl(session_notes))
    return items[-limit:]


def search_notes(session_notes: Path, query: str, limit: int) -> list[dict[str, Any]]:
    q = query.lower().strip()
    if not q:
        return []

    matches: list[dict[str, Any]] = []
    for entry in _iter_jsonl(session_notes):
        hay = json.dumps(entry, ensure_ascii=False).lower()
        if q in hay:
            matches.append(entry)

    return matches[-limit:]


def _truncate_one_line(text: str, max_len: int) -> str:
    one_line = " ".join((text or "").splitlines()).strip()
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 1].rstrip() + "…"


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        norm = " ".join(raw.lower().split())
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(raw)
    return out


def _split_candidate_phrases(text: str) -> list[str]:
    if not text:
        return []
    candidates: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(("-", "*")):
            s = s.lstrip("-* ").strip()
        if len(s) < 6:
            continue
        candidates.append(_truncate_one_line(s, 220))
    return candidates


def _extract_phrases(entries: list[dict[str, Any]]) -> list[str]:
    phrases: list[str] = []
    for e in entries:
        phrases.extend(_split_candidate_phrases(str(e.get("title") or "")))
        phrases.extend(_split_candidate_phrases(str(e.get("note") or "")))
    return _dedupe_preserve_order(phrases)


def _select_phrases(phrases: list[str], keywords: list[str], limit: int) -> list[str]:
    kws = [k.lower() for k in keywords]
    picked: list[str] = []
    for p in phrases:
        pl = p.lower()
        if any(k in pl for k in kws):
            picked.append(p)
        if len(picked) >= limit:
            break
    return picked


def _top_tags(entries: list[dict[str, Any]], limit: int = 8) -> list[tuple[str, int]]:
    counter: collections.Counter[str] = collections.Counter()
    for e in entries:
        for t in (e.get("tags") or []):
            if isinstance(t, str) and t.strip():
                counter[t.strip().lower()] += 1
    return counter.most_common(limit)


def _render_bullets(items: list[str], *, fallback: str, max_items: int) -> str:
    use = [i.strip() for i in items if i and i.strip()][:max_items]
    if not use:
        use = [fallback]
    return "\n".join([f"- {i}" for i in use]) + "\n"


def _render_curated_block(entries: list[dict[str, Any]], limit: int) -> str:
    recent = entries[-min(len(entries), limit) :]
    phrases = _extract_phrases(recent)
    tags = _top_tags(recent, 6)
    tag_hint = ", ".join([t for t, _ in tags]) if tags else "continuity"

    building = _select_phrases(
        phrases,
        keywords=["build", "building", "scaffold", "implement", "agent", "continuity", "workflow"],
        limit=4,
    )
    current = _select_phrases(
        phrases,
        keywords=["added", "working", "works", "fixed", "created", "configured", "set up", "setup", "initialized"],
        limit=5,
    )
    constraints = _select_phrases(
        phrases,
        keywords=["can't", "cannot", "must", "avoid", "prefer", "keep", "only", "do not", "don't"],
        limit=5,
    )
    next_steps = _select_phrases(
        phrases,
        keywords=["next", "todo", "to do", "need", "should", "want", "plan"],
        limit=6,
    )

    out: list[str] = []
    out.append("## What we're building")
    out.append(_render_bullets(building, fallback=f"Working on: {tag_hint}", max_items=4).rstrip())
    out.append("")
    out.append("## Current state")
    out.append(
        _render_bullets(
            current,
            fallback="Session notes are being captured; auto-refresh is enabled.",
            max_items=5,
        ).rstrip()
    )
    out.append("")
    out.append("## Constraints")
    out.append(
        _render_bullets(
            constraints,
            fallback="Keep changes small and testable; prefer reusable code in tools/.",
            max_items=5,
        ).rstrip()
    )
    out.append("")
    out.append("## Next steps")
    out.append(
        _render_bullets(
            next_steps,
            fallback="Review the latest notes and continue the highest-signal next step.",
            max_items=6,
        ).rstrip()
    )
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def _render_next_steps_draft(entries: list[dict[str, Any]], limit: int) -> str:
    recent = entries[-min(len(entries), limit) :]
    phrases = _extract_phrases(recent)
    draft = _select_phrases(
        phrases,
        keywords=["next", "todo", "to do", "need", "should", "try", "add", "wire", "update"],
        limit=10,
    )

    if not draft:
        draft = [
            "Open project memory and validate the auto sections look correct.",
            "Run the continuity shortcut after meaningful work sessions.",
        ]

    return _render_bullets(draft, fallback="(no draft items)", max_items=10)


def _render_auto_summary(entries: list[dict[str, Any]], limit: int) -> str:
    top_tags = _top_tags(entries, 8)
    top_tags_str = ", ".join([f"{t} ({c})" for t, c in top_tags]) if top_tags else "(none)"

    last = entries[-1] if entries else None
    last_line = "(no notes yet)"
    if last:
        last_ts = str(last.get("ts") or "")
        last_title = str(last.get("title") or "")
        last_line = f"{last_ts} — {last_title}".strip(" —")

    lines: list[str] = []
    lines.append(f"Generated (UTC): {_utc_now_iso()}")
    lines.append(f"Notes considered: {min(len(entries), limit)}")
    lines.append(f"Last note: {last_line}")
    lines.append(f"Top tags: {top_tags_str}")
    lines.append("")
    lines.append("Recent notes:")

    for e in entries[-min(len(entries), limit) :]:
        ts = str(e.get("ts") or "")
        title = str(e.get("title") or "")
        tags = e.get("tags") or []
        tag_str = ",".join([t for t in tags if isinstance(t, str)])
        note_preview = _truncate_one_line(str(e.get("note") or ""), 160)
        tag_suffix = f" (tags: {tag_str})" if tag_str else ""
        preview_suffix = f" — {note_preview}" if note_preview else ""
        lines.append(f"- {ts} — {title}{tag_suffix}{preview_suffix}".strip())

    return "\n".join(lines).rstrip() + "\n"


def _safe_timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _write_snapshot_if_needed(project_memory: Path, snapshot_dir: Path) -> Path | None:
    if not project_memory.exists():
        return None

    current = project_memory.read_text(encoding="utf-8").strip()
    if not current:
        return None

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snapshot_dir / f"project_memory_{_safe_timestamp_for_filename()}.md"
    snap_path.write_text(current + "\n", encoding="utf-8")
    return snap_path


def refresh_project_memory(
    project_memory: Path,
    session_notes: Path,
    limit: int,
    *,
    dry_run: bool,
    snapshot: bool,
    snapshot_dir: Path,
) -> str:
    entries = tail_notes(session_notes, limit)
    curated = _render_curated_block(entries, limit)
    draft = _render_next_steps_draft(entries, limit)
    auto_summary = _render_auto_summary(entries, limit)

    updated = (
        "# Project Memory (Continuity)\n\n"
        "This file is generated from repo-backed continuity notes.\n"
        "Use the shortcut/task to keep it updated automatically.\n\n"
        f"{CURATED_START}\n"
        f"Generated (UTC): {_utc_now_iso()}\n"
        f"Notes considered: {min(len(entries), limit)}\n\n"
        f"{curated}\n"
        f"{CURATED_END}\n\n"
        "## Auto Next Steps (Draft)\n\n"
        "Drafted from recent notes; may include duplicates or low-signal items.\n\n"
        f"{DRAFT_START}\n"
        f"{draft}"
        f"{DRAFT_END}\n\n"
        "## Auto Summary\n\n"
        "Compact trace of recent session notes.\n\n"
        f"{AUTO_START}\n"
        f"{auto_summary}"
        f"{AUTO_END}\n"
    )

    if not dry_run:
        if snapshot:
            _write_snapshot_if_needed(project_memory, snapshot_dir)
        project_memory.write_text(updated, encoding="utf-8")

    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="continuity",
        description="Repo-backed continuity memory helper (Markdown + JSONL).",
    )
    parser.add_argument(
        "--dir",
        default=str(DEFAULT_KNOWLEDGE_DIR),
        help="Knowledge directory to store continuity files (default: knowledge/continuity)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create continuity files if missing")

    p_add = sub.add_parser("add", help="Append a session note entry")
    p_add.add_argument("--title", required=True, help="Short title")
    p_add.add_argument("--note", help="Note text. If omitted, reads from STDIN.")
    p_add.add_argument("--tags", default="", help="Comma-separated tags")
    p_add.add_argument("--source", default="vscode-chat", help="Note source")

    p_search = sub.add_parser("search", help="Search session notes")
    p_search.add_argument("query", help="Search string")
    p_search.add_argument("--limit", type=int, default=20, help="Max results")

    p_tail = sub.add_parser("tail", help="Show latest entries")
    p_tail.add_argument("--limit", type=int, default=20, help="Max results")

    p_refresh = sub.add_parser("refresh", help="Refresh project_memory.md")
    p_refresh.add_argument("--limit", type=int, default=25, help="How many notes to consider")
    p_refresh.add_argument("--dry-run", action="store_true", help="Print instead of writing")
    p_refresh.add_argument(
        "--snapshot",
        action="store_true",
        help="Write a timestamped snapshot of the existing project_memory.md before overwriting",
    )
    p_refresh.add_argument(
        "--snapshot-dir",
        default="",
        help="Directory to write snapshots to (default: <dir>/snapshots)",
    )

    args = parser.parse_args()

    base_dir = Path(args.dir)
    project_memory, session_notes = init_memory(base_dir)

    if args.cmd == "init":
        print(f"Initialized:\n- {project_memory}\n- {session_notes}")
        return 0

    if args.cmd == "add":
        note_text = args.note
        if note_text is None:
            note_text = sys.stdin.read()
        tags = [t.strip() for t in str(args.tags).split(",") if t.strip()]
        add_note(session_notes, AddArgs(title=args.title, note=str(note_text).strip(), tags=tags, source=args.source))
        print("OK")
        return 0

    if args.cmd == "search":
        results = search_notes(session_notes, args.query, int(args.limit))
        for r in results:
            print(json.dumps(r, ensure_ascii=False))
        return 0

    if args.cmd == "tail":
        results = tail_notes(session_notes, int(args.limit))
        for r in results:
            print(json.dumps(r, ensure_ascii=False))
        return 0

    if args.cmd == "refresh":
        snapshot_dir = (
            Path(args.snapshot_dir)
            if str(args.snapshot_dir).strip()
            else Path(args.dir) / "snapshots"
        )
        updated = refresh_project_memory(
            project_memory,
            session_notes,
            int(args.limit),
            dry_run=bool(args.dry_run),
            snapshot=bool(args.snapshot),
            snapshot_dir=snapshot_dir,
        )
        if args.dry_run:
            print(updated)
        else:
            print("OK")
        return 0

    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
