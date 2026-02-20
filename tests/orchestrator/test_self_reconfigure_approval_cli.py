from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_CLI = _SOL_ROOT / "tools" / "sol-orchestrator" / "self_reconfigure_approval_cli.py"


def _run_cli(ledger_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(_CLI),
        "--ledger-path",
        str(ledger_path),
        *args,
        "--json",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_cli_add_list_remove_roundtrip(tmp_path: Path):
    ledger = tmp_path / "_self_reconfigure_approvals.json"

    add = _run_cli(
        ledger,
        "add",
        "cortex:relax:relax_retry_limits",
        "cortex:relax:relax_retry_limits",
        "consolidate:tighten:tighten_retry_limits",
    )
    assert add.returncode == 0
    add_payload = json.loads(add.stdout)
    assert add_payload["approved_count"] == 2

    listed = _run_cli(ledger, "list")
    assert listed.returncode == 0
    list_payload = json.loads(listed.stdout)
    assert list_payload["approved_proposal_ids"] == [
        "consolidate:tighten:tighten_retry_limits",
        "cortex:relax:relax_retry_limits",
    ]

    remove = _run_cli(
        ledger,
        "remove",
        "cortex:relax:relax_retry_limits",
        "missing:proposal:id",
    )
    assert remove.returncode == 0
    remove_payload = json.loads(remove.stdout)
    assert remove_payload["removed"] == ["cortex:relax:relax_retry_limits"]
    assert remove_payload["missing"] == ["missing:proposal:id"]
    assert remove_payload["approved_count"] == 1


def test_cli_clear_requires_confirmation(tmp_path: Path):
    ledger = tmp_path / "_self_reconfigure_approvals.json"

    add = _run_cli(ledger, "add", "cortex:relax:relax_retry_limits")
    assert add.returncode == 0

    no_confirm = subprocess.run(
        [
            sys.executable,
            str(_CLI),
            "--ledger-path",
            str(ledger),
            "clear",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert no_confirm.returncode == 2

    clear = _run_cli(ledger, "clear", "--yes")
    assert clear.returncode == 0
    clear_payload = json.loads(clear.stdout)
    assert clear_payload["approved_count"] == 0

    listed = _run_cli(ledger, "list")
    assert listed.returncode == 0
    list_payload = json.loads(listed.stdout)
    assert list_payload["approved_proposal_ids"] == []
