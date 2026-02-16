from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SyncConfig:
    repo: str
    limit: int
    include_workflow_regex: str
    include_artifact_regex: str
    archive_root: Path
    self_train_root: Path
    state_path: Path
    temp_root: Path
    skip_ledgers: bool
    force_redownload: bool
    required_run_source: str
    stop_flag_path: Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "workflow"


def _run_command(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _require_gh() -> None:
    _run_command(["gh", "--version"], check=True)


def _load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {"synced_artifacts": {}}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {"synced_artifacts": {}}


def _save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _list_runs(config: SyncConfig) -> list[dict[str, Any]]:
    run = _run_command(
        [
            "gh",
            "run",
            "list",
            "-R",
            config.repo,
            "--limit",
            str(config.limit),
            "--json",
            "databaseId,workflowName,status,conclusion,headBranch,event,displayTitle,startedAt,updatedAt,url",
        ],
        check=True,
    )
    payload = json.loads(run.stdout or "[]")
    if not isinstance(payload, list):
        return []

    workflow_re = re.compile(config.include_workflow_regex)
    filtered: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        workflow_name = str(row.get("workflowName", ""))
        if not workflow_re.search(workflow_name):
            continue
        if str(row.get("status", "")).lower() != "completed":
            continue
        if str(row.get("conclusion", "")).lower() != "success":
            continue
        filtered.append(row)

    filtered.sort(key=lambda r: int(r.get("databaseId", 0)))
    return filtered


def _list_run_artifacts(repo: str, run_id: int) -> list[dict[str, Any]]:
    result = _run_command(
        ["gh", "api", f"repos/{repo}/actions/runs/{run_id}/artifacts"],
        check=True,
    )
    payload = json.loads(result.stdout or "{}")
    artifacts = payload.get("artifacts", []) if isinstance(payload, dict) else []
    if not isinstance(artifacts, list):
        return []
    return [a for a in artifacts if isinstance(a, dict)]


def _download_artifact(repo: str, run_id: int, artifact_name: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    _run_command(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "-R",
            repo,
            "-D",
            str(destination),
            "-n",
            artifact_name,
        ],
        check=True,
    )
    extracted = destination / artifact_name
    if extracted.exists():
        return extracted

    if any(destination.glob("gen_*")) or (destination / "summary.json").exists() or (destination / "policy_current.json").exists():
        return destination

    candidates = [p for p in destination.iterdir() if p.is_dir()]
    if len(candidates) == 1:
        return candidates[0]

    nested_with_gens = [p for p in candidates if any(p.glob("gen_*"))]
    if len(nested_with_gens) == 1:
        return nested_with_gens[0]

    raise FileNotFoundError(f"Could not locate extracted artifact folder for {artifact_name}")


def _copy_tree_contents(source_dir: Path, destination_dir: Path, overwrite: bool = True) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for child in source_dir.iterdir():
        target = destination_dir / child.name
        if child.is_dir():
            if target.exists() and overwrite:
                shutil.rmtree(target)
            if not target.exists():
                shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def _parse_self_train_artifact(artifact_name: str, fallback_run_id: int) -> tuple[str, str] | None:
    if not artifact_name.startswith("self-train-"):
        return None

    tokens = artifact_name.split("-")
    if len(tokens) < 4:
        return None

    mode = tokens[2]
    run_token = tokens[-1]
    run_id = run_token if run_token.isdigit() else str(fallback_run_id)
    return mode, run_id


def _artifact_matches_required_source(artifact_name: str, required_run_source: str) -> bool:
    if required_run_source == "any":
        return True

    normalized_name = artifact_name.lower()
    token = f"-{required_run_source.lower()}-"
    return token in normalized_name


def _refresh_ledgers(repo_root: Path, self_train_root: Path) -> None:
    _run_command(
        [
            sys.executable,
            "tools/sol-evolve/self_train_consolidate.py",
            "--root",
            str(self_train_root),
            "--out-dir",
            str(self_train_root / "_ledger"),
        ],
        cwd=repo_root,
        check=True,
    )
    _run_command(
        [
            sys.executable,
            "tools/analysis/experiment_ledger.py",
            "--self-train-root",
            str(self_train_root),
            "--out-dir",
            "data/experiment_ledger",
        ],
        cwd=repo_root,
        check=True,
    )


def sync_once(config: SyncConfig, repo_root: Path) -> dict[str, Any]:
    state = _load_state(config.state_path)
    synced_artifacts = state.setdefault("synced_artifacts", {})

    artifact_re = re.compile(config.include_artifact_regex)
    runs = _list_runs(config)

    downloaded_count = 0
    archived_count = 0
    self_train_ingested_count = 0
    errors: list[str] = []

    for run in runs:
        run_id = int(run.get("databaseId", 0) or 0)
        if run_id <= 0:
            continue

        workflow_name = str(run.get("workflowName", ""))
        workflow_slug = _slug(workflow_name)

        try:
            artifacts = _list_run_artifacts(config.repo, run_id)
        except Exception as exc:
            errors.append(f"run={run_id} artifact_list_error={exc}")
            continue

        for artifact in artifacts:
            name = str(artifact.get("name", "")).strip()
            expired = bool(artifact.get("expired", False))
            if not name or expired:
                continue
            if not artifact_re.search(name):
                continue
            if not _artifact_matches_required_source(name, config.required_run_source):
                continue

            artifact_key = f"{run_id}:{name}"
            if artifact_key in synced_artifacts and not config.force_redownload:
                continue

            tmp_dir = config.temp_root / str(run_id) / _slug(name)
            if tmp_dir.exists() and config.force_redownload:
                shutil.rmtree(tmp_dir)

            try:
                extracted_dir = _download_artifact(config.repo, run_id, name, tmp_dir)
                downloaded_count += 1

                archive_dir = config.archive_root / workflow_slug / str(run_id) / name
                if archive_dir.exists() and config.force_redownload:
                    shutil.rmtree(archive_dir)
                if not archive_dir.exists():
                    _copy_tree_contents(extracted_dir, archive_dir, overwrite=True)
                    archived_count += 1

                ingested_paths: list[str] = [str(archive_dir).replace("\\", "/")]

                self_train_meta = _parse_self_train_artifact(name, run_id)
                if self_train_meta is not None:
                    mode, canonical_run_id = self_train_meta
                    canonical_dir = config.self_train_root / "github-actions" / mode / canonical_run_id
                    if canonical_dir.exists() and config.force_redownload:
                        shutil.rmtree(canonical_dir)
                    if not canonical_dir.exists():
                        _copy_tree_contents(extracted_dir, canonical_dir, overwrite=True)
                        self_train_ingested_count += 1
                    ingested_paths.append(str(canonical_dir).replace("\\", "/"))

                synced_artifacts[artifact_key] = {
                    "run_id": run_id,
                    "workflow": workflow_name,
                    "artifact": name,
                    "synced_at": _utc_now_iso(),
                    "paths": ingested_paths,
                }
            except Exception as exc:
                errors.append(f"run={run_id} artifact={name} error={exc}")
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    if self_train_ingested_count > 0 and not config.skip_ledgers:
        _refresh_ledgers(repo_root=repo_root, self_train_root=config.self_train_root)

    state["last_synced_at"] = _utc_now_iso()
    _save_state(config.state_path, state)

    return {
        "runs_considered": len(runs),
        "downloaded": downloaded_count,
        "archived": archived_count,
        "self_train_ingested": self_train_ingested_count,
        "errors": errors,
        "state_path": str(config.state_path).replace("\\", "/"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync GitHub Actions artifacts into local SOL data roots")
    parser.add_argument("--repo", default="TechmanStudios/sol", help="GitHub repo in owner/name format")
    parser.add_argument("--limit", type=int, default=60, help="How many recent runs to inspect")
    parser.add_argument(
        "--include-workflow-regex",
        default=r"^SOL ",
        help="Regex applied to workflowName for selecting runs",
    )
    parser.add_argument(
        "--include-artifact-regex",
        default=r".",
        help="Regex applied to artifact names for selecting downloads",
    )
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=Path("data") / "pipeline_runs" / "github_actions_artifacts",
        help="Local archive root for downloaded artifacts",
    )
    parser.add_argument(
        "--self-train-root",
        type=Path,
        default=Path("data") / "sol_self_train_runs",
        help="Canonical self-train run root",
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data") / "pipeline_runs" / "github_artifact_sync_state.json",
        help="State file tracking synced artifact ids",
    )
    parser.add_argument(
        "--temp-root",
        type=Path,
        default=Path("data") / "pipeline_runs" / "_github_artifact_sync_tmp",
        help="Temporary download directory",
    )
    parser.add_argument("--skip-ledgers", action="store_true", help="Do not regenerate ledgers after self-train ingest")
    parser.add_argument("--force-redownload", action="store_true", help="Redownload and overwrite already-synced artifacts")
    parser.add_argument(
        "--required-run-source",
        choices=["any", "phone", "desktop"],
        default="any",
        help="Only sync artifacts tagged with this run source in artifact name (e.g. self-train-full-phone-<run_id>)",
    )
    parser.add_argument("--watch", action="store_true", help="Keep polling and syncing on an interval")
    parser.add_argument("--interval-sec", type=int, default=600, help="Watch interval in seconds")
    parser.add_argument(
        "--stop-flag-path",
        type=Path,
        default=Path("data") / "pipeline_runs" / "github_artifact_sync.stop",
        help="Path to stop-flag file used to terminate watch mode gracefully",
    )
    parser.add_argument(
        "--clear-stop-flag",
        action="store_true",
        help="Delete stop-flag file before starting (useful for watch task startup)",
    )
    return parser.parse_args()


def _print_summary(summary: dict[str, Any]) -> None:
    print("[github-artifact-sync] summary")
    print(f"- runs_considered: {summary['runs_considered']}")
    print(f"- downloaded: {summary['downloaded']}")
    print(f"- archived: {summary['archived']}")
    print(f"- self_train_ingested: {summary['self_train_ingested']}")
    print(f"- state: {summary['state_path']}")
    errors = summary.get("errors", [])
    if errors:
        print(f"- errors: {len(errors)}")
        for err in errors[:10]:
            print(f"  - {err}")


def main() -> int:
    args = parse_args()
    _require_gh()

    repo_root = Path(__file__).resolve().parents[2]
    config = SyncConfig(
        repo=args.repo,
        limit=args.limit,
        include_workflow_regex=args.include_workflow_regex,
        include_artifact_regex=args.include_artifact_regex,
        archive_root=(repo_root / args.archive_root).resolve(),
        self_train_root=(repo_root / args.self_train_root).resolve(),
        state_path=(repo_root / args.state_path).resolve(),
        temp_root=(repo_root / args.temp_root).resolve(),
        skip_ledgers=bool(args.skip_ledgers),
        force_redownload=bool(args.force_redownload),
        required_run_source=str(args.required_run_source),
        stop_flag_path=(repo_root / args.stop_flag_path).resolve(),
    )

    if bool(args.clear_stop_flag):
        try:
            config.stop_flag_path.unlink(missing_ok=True)
        except Exception:
            pass

    if not args.watch:
        summary = sync_once(config=config, repo_root=repo_root)
        _print_summary(summary)
        return 0

    print(
        "[github-artifact-sync] watch enabled, "
        f"interval={args.interval_sec}s, stop_flag={config.stop_flag_path}"
    )
    while True:
        if config.stop_flag_path.exists():
            print("[github-artifact-sync] stop flag detected, exiting watch mode")
            break
        summary = sync_once(config=config, repo_root=repo_root)
        _print_summary(summary)

        sleep_remaining = max(5, int(args.interval_sec))
        while sleep_remaining > 0:
            if config.stop_flag_path.exists():
                print("[github-artifact-sync] stop flag detected, exiting watch mode")
                return 0
            time.sleep(min(5, sleep_remaining))
            sleep_remaining -= 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
