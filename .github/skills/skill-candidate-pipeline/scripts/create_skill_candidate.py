import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_slug_re = re.compile(r"[^a-z0-9\-]+")


def normalize_slug(value: str) -> str:
    raw = (value or "").strip().lower().replace("_", "-").replace(" ", "-")
    raw = _slug_re.sub("-", raw)
    raw = raw.strip("-")
    return raw[:80] or "unnamed"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class CandidateInput:
    slug: str
    title: str
    description: str
    domain: str
    tags: List[str]
    evidence: List[str]
    triggers: List[str]
    source_runs: List[str]


def render_skill_md(title: str, description: str) -> str:
    return (
        f"name: {title}\n"
        f"description: {description}\n\n"
        "Status\n"
        "- This is a *candidate* skill draft.\n"
        "- Do not treat as authoritative until promoted.\n\n"
        "Intended use\n"
        "- When: <fill in>\n"
        "- Inputs: <fill in>\n"
        "- Outputs: <fill in>\n\n"
        "Guardrails\n"
        "- Requires evidence links in EVIDENCE.md\n"
        "- Requires a crisp trigger in TRIGGER.md\n"
    )


def render_evidence_md(evidence: Iterable[str]) -> str:
    lines = [
        "# Evidence\n",
        "This candidate must be backed by *traceable* artifacts (raw bundles, manifests, tables).\n",
        "\n",
        "## Links\n",
    ]
    ev = [e for e in evidence if str(e).strip()]
    if not ev:
        lines.append("- <add links to run bundles / files>\n")
    else:
        for e in ev:
            lines.append(f"- {e}\n")

    lines += [
        "\n",
        "## Minimal reproducibility\n",
        "- Dataset(s): <path(s)>\n",
        "- How to reproduce: <steps/command>\n",
        "- Expected result: <what should happen>\n",
    ]
    return "".join(lines)


def render_trigger_md(triggers: Iterable[str]) -> str:
    lines = [
        "# Trigger\n",
        "Define the *data-based* condition that caused this candidate to be proposed.\n",
        "\n",
        "A good trigger is specific, testable, and mentions counterexamples.\n",
        "\n",
        "## Proposed trigger\n",
    ]

    t = [x for x in triggers if str(x).strip()]
    if not t:
        lines.append("- <condition expressed in metrics/thresholds>\n")
    else:
        for x in t:
            lines.append(f"- {x}\n")

    lines += [
        "\n",
        "## Counterexamples / limits\n",
        "- <where it fails>\n",
        "\n",
        "## Acceptance criteria (for promotion)\n",
        "- Replicates agree (N>=?)\n",
        "- Stable across baselines / versions (if applicable)\n",
        "- Traceable evidence links\n",
    ]

    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a candidate skill folder with evidence + trigger templates.")
    parser.add_argument("--dest", required=True, help="Destination root (will create _candidates/<slug>/ under it).")
    parser.add_argument("--slug", required=True, help="Folder slug (kebab-case recommended).")
    parser.add_argument("--title", required=True, help="Human title/name for the candidate.")
    parser.add_argument("--description", required=True, help="One-line description.")
    parser.add_argument("--domain", default="general", help="Domain label (e.g., general, sol, youtube).")
    parser.add_argument("--tag", action="append", default=[], help="Tag (repeatable).")
    parser.add_argument("--evidence", action="append", default=[], help="Evidence link/path (repeatable).")
    parser.add_argument("--trigger", action="append", default=[], help="Trigger line (repeatable).")
    parser.add_argument("--source-run", action="append", default=[], help="Run ID / manifest path (repeatable).")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files if present.")

    args = parser.parse_args()

    slug = normalize_slug(args.slug)
    dest_root = Path(args.dest).expanduser().resolve()
    out_dir = dest_root / "_candidates" / slug

    ensure_dir(out_dir)

    ci = CandidateInput(
        slug=slug,
        title=str(args.title).strip(),
        description=str(args.description).strip(),
        domain=str(args.domain).strip() or "general",
        tags=[str(t).strip() for t in (args.tag or []) if str(t).strip()],
        evidence=[str(e).strip() for e in (args.evidence or []) if str(e).strip()],
        triggers=[str(t).strip() for t in (args.trigger or []) if str(t).strip()],
        source_runs=[str(s).strip() for s in (args.source_run or []) if str(s).strip()],
    )

    manifest = {
        "kind": "skill_candidate",
        "slug": ci.slug,
        "title": ci.title,
        "description": ci.description,
        "domain": ci.domain,
        "tags": ci.tags,
        "createdAt": _utc_now_iso(),
        "sourceRuns": ci.source_runs,
        "evidence": ci.evidence,
        "triggers": ci.triggers,
        "status": "candidate",
    }

    files = {
        "skill.md": render_skill_md(ci.title, ci.description),
        "EVIDENCE.md": render_evidence_md(ci.evidence),
        "TRIGGER.md": render_trigger_md(ci.triggers),
        "candidate_manifest.json": json.dumps(manifest, indent=2) + "\n",
    }

    for name, content in files.items():
        p = out_dir / name
        if p.exists() and not args.force:
            raise SystemExit(f"Refusing to overwrite existing file: {p} (use --force)")
        p.write_text(content, encoding="utf-8")

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
