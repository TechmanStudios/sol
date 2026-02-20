#!/usr/bin/env python3
"""Manage self-reconfigure approval ledger IDs.

Phase 4.4 helper for explicit approval workflows:
  - list approved proposal IDs
  - add approved proposal IDs
  - remove approved proposal IDs
  - clear approved proposal IDs (with explicit --yes)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_approval_ledger_path() -> Path:
    this_dir = Path(__file__).resolve().parent
    sol_root = this_dir.parent.parent
    return sol_root / "data" / "pipeline_runs" / "_self_reconfigure_approvals.json"


def _normalize_ids(values: list[str]) -> list[str]:
    unique = {str(v).strip() for v in values if str(v).strip()}
    return sorted(unique)


def load_approval_ledger(path: Path) -> dict[str, Any]:
    default = {
        "version": 1,
        "updated": _now_iso(),
        "approved_proposal_ids": [],
        "run_audit": [],
    }
    if not path.exists():
        return default

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default

    if not isinstance(payload, dict):
        return default

    approved = payload.get("approved_proposal_ids", [])
    if not isinstance(approved, list):
        approved = []
    run_audit = payload.get("run_audit", [])
    if not isinstance(run_audit, list):
        run_audit = []

    return {
        "version": int(payload.get("version", 1) or 1),
        "updated": str(payload.get("updated", _now_iso())),
        "approved_proposal_ids": _normalize_ids([str(item) for item in approved]),
        "run_audit": run_audit,
    }


def save_approval_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": int(ledger.get("version", 1) or 1),
        "updated": _now_iso(),
        "approved_proposal_ids": _normalize_ids(
            [str(item) for item in ledger.get("approved_proposal_ids", [])]
        ),
        "run_audit": ledger.get("run_audit", []),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return

    print(f"ledger: {payload.get('ledger_path', '')}")
    print(f"approved_count: {payload.get('approved_count', 0)}")
    for item in payload.get("approved_proposal_ids", []):
        print(f"- {item}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage self-reconfigure approval ledger IDs")
    parser.add_argument(
        "--ledger-path",
        type=Path,
        default=default_approval_ledger_path(),
        help="Path to _self_reconfigure_approvals.json",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List approved proposal IDs")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    add_parser = subparsers.add_parser("add", help="Add approved proposal IDs")
    add_parser.add_argument("proposal_ids", nargs="+", help="Proposal IDs to approve")
    add_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    remove_parser = subparsers.add_parser("remove", help="Remove approved proposal IDs")
    remove_parser.add_argument("proposal_ids", nargs="+", help="Proposal IDs to remove")
    remove_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    clear_parser = subparsers.add_parser("clear", help="Clear all approved proposal IDs")
    clear_parser.add_argument("--yes", action="store_true", help="Required confirmation flag")
    clear_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    args = parser.parse_args(argv)
    ledger_path: Path = args.ledger_path
    ledger = load_approval_ledger(ledger_path)
    approved = _normalize_ids([str(item) for item in ledger.get("approved_proposal_ids", [])])

    if args.command == "list":
        payload = {
            "command": "list",
            "ledger_path": str(ledger_path),
            "approved_count": len(approved),
            "approved_proposal_ids": approved,
        }
        _emit(payload, args.json)
        return 0

    if args.command == "add":
        requested = _normalize_ids(args.proposal_ids)
        before = set(approved)
        after = sorted(before | set(requested))
        added = sorted(set(after) - before)
        ledger["approved_proposal_ids"] = after
        save_approval_ledger(ledger_path, ledger)
        payload = {
            "command": "add",
            "ledger_path": str(ledger_path),
            "requested": requested,
            "added": added,
            "approved_count": len(after),
            "approved_proposal_ids": after,
        }
        _emit(payload, args.json)
        return 0

    if args.command == "remove":
        requested = _normalize_ids(args.proposal_ids)
        before = set(approved)
        remaining = sorted(before - set(requested))
        removed = sorted(before - set(remaining))
        missing = sorted(set(requested) - before)
        ledger["approved_proposal_ids"] = remaining
        save_approval_ledger(ledger_path, ledger)
        payload = {
            "command": "remove",
            "ledger_path": str(ledger_path),
            "requested": requested,
            "removed": removed,
            "missing": missing,
            "approved_count": len(remaining),
            "approved_proposal_ids": remaining,
        }
        _emit(payload, args.json)
        return 0

    if args.command == "clear":
        if not args.yes:
            print("Refusing to clear approvals without --yes")
            return 2
        ledger["approved_proposal_ids"] = []
        save_approval_ledger(ledger_path, ledger)
        payload = {
            "command": "clear",
            "ledger_path": str(ledger_path),
            "approved_count": 0,
            "approved_proposal_ids": [],
        }
        _emit(payload, args.json)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
