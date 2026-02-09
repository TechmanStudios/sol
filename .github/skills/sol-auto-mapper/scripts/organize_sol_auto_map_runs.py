from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


FILE_RE_LEGACY = re.compile(
    r"^solAutoMap__(?P<plan>[^_].*?)__(?P<iso>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z)__(?P<kind>summary|trace|manifest)\.(?P<ext>csv|json)$"
)

# Master/sweep naming:
# solAutoMap__<master>__<iso>__<sweep>__summary.csv
FILE_RE_MASTER = re.compile(
    r"^solAutoMap__(?P<master>[^_].*?)__(?P<iso>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z)__(?P<sweep>[^_].*?)__(?P<kind>summary|trace|manifest)\.(?P<ext>csv|json)$"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class RunKey:
    plan: str
    iso: str


def iter_matching_files(src: Path) -> Iterable[Path]:
    for p in src.iterdir():
        if not p.is_file():
            continue
        if FILE_RE_LEGACY.match(p.name) or FILE_RE_MASTER.match(p.name):
            yield p


def parse_key(path: Path) -> tuple[RunKey, dict]:
    m = FILE_RE_MASTER.match(path.name)
    if m:
        d = m.groupdict()
        d["plan"] = d["master"]
        return RunKey(plan=d["master"], iso=d["iso"]), d

    m = FILE_RE_LEGACY.match(path.name)
    if m:
        d = m.groupdict()
        d["sweep"] = "SINGLE"
        return RunKey(plan=d["plan"], iso=d["iso"]), d

    raise ValueError(f"Not a solAutoMap artifact: {path.name}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


_slug_re = re.compile(r"[^a-z0-9\-]+")


def _slugify(value: str) -> str:
    raw = (value or "").strip().lower().replace("_", "-").replace(" ", "-")
    raw = _slug_re.sub("-", raw).strip("-")
    return raw[:80] or "unnamed"


def _find_candidate_cli() -> Path:
    # This file lives at:
    #   .github/skills/sol-auto-mapper/scripts/organize_sol_auto_map_runs.py
    # Candidate CLI lives at:
    #   .github/skills/skill-candidate-pipeline/scripts/create_skill_candidate.py
    here = Path(__file__).resolve()
    skills_dir = here.parents[2]  # .../.github/skills
    p = skills_dir / "skill-candidate-pipeline" / "scripts" / "create_skill_candidate.py"
    return p


def _collect_evidence_paths(run_dir: Path) -> list[str]:
    out: list[str] = []
    out.append(str(run_dir))
    rm = run_dir / "run_manifest.json"
    if rm.exists():
        out.append(str(rm))

    # Add any per-sweep manifest files (useful anchor points).
    for m in sorted(run_dir.glob("**/*__manifest.json")):
        out.append(str(m))

    return out


def _create_candidate(
    *,
    candidate_dest: Path,
    candidate_domain: str,
    candidate_tags: list[str],
    candidate_title: str,
    candidate_description: str,
    run_dir: Path,
    plan: str,
    iso: str,
) -> Path:
    cli = _find_candidate_cli()
    if not cli.exists():
        raise SystemExit(f"candidate CLI not found at: {cli}")

    slug = _slugify(f"sol-auto-map-{plan}-{iso}")
    evidence = _collect_evidence_paths(run_dir)

    args = [
        sys.executable,
        str(cli),
        "--dest",
        str(candidate_dest),
        "--slug",
        slug,
        "--title",
        candidate_title,
        "--description",
        candidate_description,
        "--domain",
        candidate_domain,
        "--tag",
        "sol-auto-map",
        "--tag",
        _slugify(plan),
    ]
    for t in candidate_tags:
        if str(t).strip():
            args += ["--tag", str(t).strip()]
    for e in evidence:
        args += ["--evidence", e]

    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(
            "candidate creation failed\n"
            f"cmd: {' '.join(args)}\n"
            f"stdout: {proc.stdout}\n"
            f"stderr: {proc.stderr}\n"
        )

    out_dir = Path(proc.stdout.strip()).resolve() if proc.stdout.strip() else candidate_dest / "_candidates" / slug
    return out_dir


def organize(
    src: Path,
    dest: Path,
    move: bool,
    *,
    candidate_dest: Path | None = None,
    candidate_domain: str = "sol",
    candidate_title: str | None = None,
    candidate_description: str | None = None,
    candidate_tags: list[str] | None = None,
) -> dict:
    files = list(iter_matching_files(src))
    grouped: dict[RunKey, list[Path]] = {}
    for f in files:
        key, _ = parse_key(f)
        grouped.setdefault(key, []).append(f)

    report = {
        "src": str(src),
        "dest": str(dest),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "runs": [],
    }

    for key, paths in sorted(grouped.items(), key=lambda kv: (kv[0].plan, kv[0].iso)):
        # If master/sweep files are present, separate by sweep under the run dir.
        # Legacy files land in sweep=SINGLE.
        root_run_dir = dest / "raw" / key.plan / key.iso
        ensure_dir(root_run_dir)

        moved = []
        manifest_entries = []
        for p in sorted(paths, key=lambda x: x.name):
            _, meta = parse_key(p)
            sweep = str(meta.get("sweep") or "SINGLE")
            run_dir = root_run_dir / sweep
            ensure_dir(run_dir)

            target = run_dir / p.name
            if move:
                shutil.move(str(p), str(target))
            else:
                shutil.copy2(str(p), str(target))

            moved.append(str(target))
            manifest_entries.append(
                {
                    "file": p.name,
                    "dest": str(target),
                    "bytes": target.stat().st_size,
                    "sha256": sha256_file(target),
                }
            )

        run_manifest = {
            "planName": key.plan,
            "iso": key.iso,
            "files": manifest_entries,
        }
        (root_run_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")

        candidate_out: str | None = None
        if candidate_dest is not None:
            ensure_dir(candidate_dest)
            c_title = candidate_title or f"SOL Auto Map Run: {key.plan} {key.iso}"
            c_desc = candidate_description or "Candidate generated from organized SOL Auto Mapper run bundle(s)."
            c_tags = candidate_tags or []
            candidate_dir = _create_candidate(
                candidate_dest=candidate_dest,
                candidate_domain=candidate_domain,
                candidate_tags=c_tags,
                candidate_title=c_title,
                candidate_description=c_desc,
                run_dir=root_run_dir,
                plan=key.plan,
                iso=key.iso,
            )
            candidate_out = str(candidate_dir)

        report["runs"].append(
            {
                "plan": key.plan,
                "iso": key.iso,
                "dir": str(root_run_dir),
                "files": moved,
                "candidate": candidate_out,
            }
        )

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Organize SOL Auto Mapper downloads into raw run bundles.")
    ap.add_argument("--src", type=Path, required=True, help="Downloads/source folder containing solAutoMap__* files")
    ap.add_argument("--dest", type=Path, required=True, help="Destination root; writes into <dest>/raw/<plan>/<iso>/")
    ap.add_argument("--move", action="store_true", help="Move files (default copies)")
    ap.add_argument("--report", type=Path, default=None, help="Optional JSON report output path")
    ap.add_argument(
        "--candidate-dest",
        type=Path,
        default=None,
        help=(
            "Optional: create a candidate skill folder for each organized run, writing to <candidate-dest>/_candidates/<slug>/. "
            "Example: knowledge/skill_candidates or solKnowledge/working/skill_candidates"
        ),
    )
    ap.add_argument("--candidate-domain", default="sol", help="Candidate domain label (default: sol)")
    ap.add_argument("--candidate-title", default=None, help="Override candidate title (default includes plan+iso)")
    ap.add_argument("--candidate-description", default=None, help="Override candidate description")
    ap.add_argument("--candidate-tag", action="append", default=[], help="Candidate tag (repeatable)")
    args = ap.parse_args()

    if not args.src.exists():
        raise SystemExit(f"src not found: {args.src}")

    ensure_dir(args.dest)
    rep = organize(
        args.src,
        args.dest,
        move=args.move,
        candidate_dest=args.candidate_dest,
        candidate_domain=str(args.candidate_domain or "sol"),
        candidate_title=args.candidate_title,
        candidate_description=args.candidate_description,
        candidate_tags=[str(t).strip() for t in (args.candidate_tag or []) if str(t).strip()],
    )

    if args.report:
        args.report.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    else:
        print(json.dumps(rep, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
