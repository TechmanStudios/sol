"""Analyze Phase C AB/BA counterbalanced sweeps.

Reads a staged omnibus batch folder produced by generate_omnibus_commands.py and
computes a compact readout of order effects (AB vs BA) using the summary CSVs.

Outputs:
- <batch_dir>/phase_c_readout_commands.csv
- <batch_dir>/phase_c_readout_pairs.csv
- <batch_dir>/phase_c_readout.md

Designed to be lightweight and dependency-free (stdlib only).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class CommandKey:
    stem: str
    out_prefix: str
    pair_id: str
    treatment: str
    order: str
    arm: str


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON is not an object: {path}")
    return data


def _find_latest_result(results_dir: Path, stem: str) -> Path | None:
    hits = sorted(results_dir.glob(f"{stem}_result_*.json"), key=lambda p: p.stat().st_mtime)
    return hits[-1] if hits else None


def _safe_float(v: Any) -> float:
    try:
        if v is None:
            return float("nan")
        s = str(v).strip()
        if s == "":
            return float("nan")
        return float(s)
    except Exception:
        return float("nan")


def _safe_int(v: Any) -> int:
    try:
        if v is None:
            return 0
        s = str(v).strip()
        if s == "":
            return 0
        return int(float(s))
    except Exception:
        return 0


def _max_finite(xs: Iterable[float]) -> float:
    best = float("nan")
    for x in xs:
        if math.isfinite(x):
            if not math.isfinite(best) or x > best:
                best = x
    return best


def _mean_finite(xs: Iterable[float]) -> float:
    s = 0.0
    n = 0
    for x in xs:
        if math.isfinite(x):
            s += x
            n += 1
    return (s / n) if n else float("nan")


def _load_summary_metrics(summary_csv: Path) -> dict[str, Any]:
    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    n_rows = len(rows)
    failed_flags = [_safe_int(r.get("failed")) for r in rows]
    fail_rate = (sum(1 for x in failed_flags if x) / n_rows) if n_rows else float("nan")

    fail_steps = [_safe_int(r.get("failStep")) for r in rows if _safe_int(r.get("failed"))]
    mean_fail_step = (sum(fail_steps) / len(fail_steps)) if fail_steps else float("nan")

    peak_mean_p = _max_finite(_safe_float(r.get("peakMeanP")) for r in rows)
    peak_pmax = _max_finite(_safe_float(r.get("peakPMax")) for r in rows)
    peak_psivar = _max_finite(_safe_float(r.get("peakPsiVar")) for r in rows)

    # Useful “overall” readouts.
    return {
        "summaryRows": n_rows,
        "failRate": fail_rate,
        "meanFailStep": mean_fail_step,
        "peakMeanP_max": peak_mean_p,
        "peakPMax_max": peak_pmax,
        "peakPsiVar_max": peak_psivar,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], preferred: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    preferred_keys = preferred or []
    keys = list(dict.fromkeys(preferred_keys + [k for r in rows for k in r.keys()]))

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _fmt(x: Any, digits: int = 4) -> str:
    try:
        xf = float(x)
        if not math.isfinite(xf):
            return ""
        return f"{xf:.{digits}f}"
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--batch-dir",
        required=True,
        help="Path to the omnibus batch folder (contains command_done/ and command_results/).",
    )
    ap.add_argument(
        "--download-dir",
        default=str(Path(__file__).resolve().parents[2] / "solData" / "testResults"),
        help="Where summary/trace CSVs were downloaded (default: solData/testResults).",
    )

    args = ap.parse_args()

    batch_dir = Path(args.batch_dir).resolve()
    download_dir = Path(args.download_dir).resolve()

    cmd_done = batch_dir / "command_done"
    cmd_results = batch_dir / "command_results"

    if not cmd_done.exists():
        raise SystemExit(f"Missing: {cmd_done}")
    if not cmd_results.exists():
        raise SystemExit(f"Missing: {cmd_results}")

    command_rows: list[dict[str, Any]] = []
    by_pair: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}

    for cmd_path in sorted(cmd_done.glob("*.json")):
        cmd = _read_json(cmd_path)
        meta = cmd.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}

        pair_id = str(meta.get("pairId") or "")
        phase = str(meta.get("phase") or "")
        if phase.upper() != "C":
            continue

        out_prefix = str(cmd.get("outPrefix") or "")
        treatment = str(meta.get("treatment") or "")
        order = str(meta.get("order") or "")
        arm = str(meta.get("arm") or "")

        stem = cmd_path.stem
        res_path = _find_latest_result(cmd_results, stem)
        if not res_path:
            command_rows.append(
                {
                    "stem": stem,
                    "pairId": pair_id,
                    "treatment": treatment,
                    "order": order,
                    "arm": arm,
                    "outPrefix": out_prefix,
                    "ok": False,
                    "message": "missing result json",
                }
            )
            continue

        res = _read_json(res_path)
        ok = bool(res.get("ok"))
        message = str(res.get("message") or "")
        outputs = res.get("outputs")
        summary_name = ""
        trace_name = ""
        if isinstance(outputs, list) and outputs:
            o0 = outputs[0] if isinstance(outputs[0], dict) else {}
            summary_name = str((o0 or {}).get("summaryCsv") or "")
            trace_name = str((o0 or {}).get("traceCsv") or "")

        row: dict[str, Any] = {
            "stem": stem,
            "pairId": pair_id,
            "treatment": treatment,
            "order": order,
            "arm": arm,
            "outPrefix": out_prefix,
            "ok": ok,
            "message": message,
            "summaryCsv": summary_name,
            "traceCsv": trace_name,
        }

        if ok and summary_name:
            summary_path = download_dir / summary_name
            if summary_path.exists():
                row.update(_load_summary_metrics(summary_path))
            else:
                row["ok"] = False
                row["message"] = f"summary missing: {summary_path.name}"

        command_rows.append(row)

        if pair_id:
            by_pair.setdefault(pair_id, {})[(order, arm)] = row

    # Per-command output.
    commands_csv = batch_dir / "phase_c_readout_commands.csv"
    _write_csv(
        commands_csv,
        command_rows,
        preferred=[
            "stem",
            "pairId",
            "treatment",
            "order",
            "arm",
            "outPrefix",
            "ok",
            "message",
            "summaryCsv",
            "traceCsv",
            "summaryRows",
            "failRate",
            "meanFailStep",
            "peakMeanP_max",
            "peakPMax_max",
            "peakPsiVar_max",
        ],
    )

    # Pair-level order-effect calculations.
    metrics = ["failRate", "meanFailStep", "peakMeanP_max", "peakPMax_max", "peakPsiVar_max"]
    pair_rows: list[dict[str, Any]] = []

    def _val(r: dict[str, Any] | None, k: str) -> float:
        return _safe_float((r or {}).get(k))

    for pair_id, slots in sorted(by_pair.items()):
        # Expected slots:
        # - (A_then_B, A)
        # - (A_then_B, B)
        # - (B_then_A, B)
        # - (B_then_A, A)
        ab_a = slots.get(("A_then_B", "A"))
        ab_b = slots.get(("A_then_B", "B"))
        ba_b = slots.get(("B_then_A", "B"))
        ba_a = slots.get(("B_then_A", "A"))

        # Treatment label should be consistent across arms; fall back to any.
        treatment = ""
        for r in (ab_a, ab_b, ba_b, ba_a):
            t = str((r or {}).get("treatment") or "")
            if t:
                treatment = t
                break

        out: dict[str, Any] = {
            "pairId": pair_id,
            "treatment": treatment,
            "complete": all(r is not None and bool(r.get("ok")) for r in (ab_a, ab_b, ba_b, ba_a)),
        }

        for m in metrics:
            eff_ab = _val(ab_b, m) - _val(ab_a, m)
            eff_ba = _val(ba_b, m) - _val(ba_a, m)
            did = eff_ab - eff_ba
            out[f"{m}_effect_AB"] = eff_ab
            out[f"{m}_effect_BA"] = eff_ba
            out[f"{m}_orderEffect_DID"] = did

        pair_rows.append(out)

    pairs_csv = batch_dir / "phase_c_readout_pairs.csv"
    _write_csv(
        pairs_csv,
        pair_rows,
        preferred=[
            "pairId",
            "treatment",
            "complete",
            "failRate_effect_AB",
            "failRate_effect_BA",
            "failRate_orderEffect_DID",
            "meanFailStep_effect_AB",
            "meanFailStep_effect_BA",
            "meanFailStep_orderEffect_DID",
            "peakMeanP_max_effect_AB",
            "peakMeanP_max_effect_BA",
            "peakMeanP_max_orderEffect_DID",
            "peakPMax_max_effect_AB",
            "peakPMax_max_effect_BA",
            "peakPMax_max_orderEffect_DID",
            "peakPsiVar_max_effect_AB",
            "peakPsiVar_max_effect_BA",
            "peakPsiVar_max_orderEffect_DID",
        ],
    )

    # Markdown summary (compact).
    md_path = batch_dir / "phase_c_readout.md"

    # Simple flags.
    def flag_row(r: dict[str, Any]) -> str:
        flags: list[str] = []
        did_p = _safe_float(r.get("peakMeanP_max_orderEffect_DID"))
        did_fail = _safe_float(r.get("failRate_orderEffect_DID"))
        if math.isfinite(did_p) and abs(did_p) >= 0.5:
            flags.append("orderEffect_peakMeanP")
        if math.isfinite(did_fail) and abs(did_fail) >= 0.25:
            flags.append("orderEffect_failRate")
        return ", ".join(flags)

    lines: list[str] = []
    lines.append("# Phase C Readout (AB/BA order effects)")
    lines.append("")
    lines.append(f"Batch: {batch_dir}")
    lines.append(f"Downloads: {download_dir}")
    lines.append("")
    lines.append("## Pair Summary")
    lines.append("| pairId | treatment | complete | DID peakMeanP_max | DID peakPMax_max | DID failRate | flags |")
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for r in pair_rows:
        lines.append(
            "| {pair} | {treat} | {complete} | {did_p} | {did_pmax} | {did_fail} | {flags} |".format(
                pair=r.get("pairId", ""),
                treat=r.get("treatment", ""),
                complete=str(bool(r.get("complete"))),
                did_p=_fmt(r.get("peakMeanP_max_orderEffect_DID"), 4),
                did_pmax=_fmt(r.get("peakPMax_max_orderEffect_DID"), 4),
                did_fail=_fmt(r.get("failRate_orderEffect_DID"), 4),
                flags=flag_row(r),
            )
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("- DID = (AB: B−A) − (BA: B−A). Large magnitude suggests order/history effects.")
    lines.append("- Metrics come from each command’s *_summary_*.csv (aggregated over its dt×damping rows).")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {commands_csv}")
    print(f"Wrote: {pairs_csv}")
    print(f"Wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
