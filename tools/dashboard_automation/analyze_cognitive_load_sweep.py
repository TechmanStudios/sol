"""Analyze cognitive-load sweep batches.

Reads a staged batch folder produced by generate_cognitive_load_commands.py and
computes a compact readout keyed by the chosen load knob.

Outputs:
- <batch_dir>/cognitive_load_readout.csv
- <batch_dir>/cognitive_load_readout.md

Notes:
- This script assumes the dashboard sweep harness exports telemetry fields like
  rhoSum / rhoEntropy / rhoActiveCount / rhoEffN in the trace CSV.
- Designed to be dependency-free (stdlib only).
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
class CommandRow:
    stem: str
    out_prefix: str
    inject_amount: float
    ok: bool
    message: str
    summary_csv: str
    trace_csv: str


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


def _min_pos_int(xs: Iterable[int]) -> int:
    best = 0
    for x in xs:
        if x > 0 and (best == 0 or x < best):
            best = x
    return best


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _summary_metrics(summary_csv: Path) -> dict[str, Any]:
    rows = _load_csv_rows(summary_csv)
    n = len(rows)

    failed_flags = [_safe_int(r.get("failed")) for r in rows]
    fail_rate = (sum(1 for x in failed_flags if x) / n) if n else float("nan")

    fail_steps = [_safe_int(r.get("failStep")) for r in rows if _safe_int(r.get("failed"))]
    mean_fail_step = (sum(fail_steps) / len(fail_steps)) if fail_steps else float("nan")
    min_fail_step = _min_pos_int(fail_steps)

    peak_mean_p = _max_finite(_safe_float(r.get("peakMeanP")) for r in rows)
    peak_pmax = _max_finite(_safe_float(r.get("peakPMax")) for r in rows)
    peak_psivar = _max_finite(_safe_float(r.get("peakPsiVar")) for r in rows)

    return {
        "summaryRows": n,
        "failRate": fail_rate,
        "meanFailStep": mean_fail_step,
        "minFailStep": min_fail_step if min_fail_step else "",
        "peakMeanP_max": peak_mean_p,
        "peakPMax_max": peak_pmax,
        "peakPsiVar_max": peak_psivar,
    }


def _trace_metrics(trace_csv: Path) -> dict[str, Any]:
    rows = _load_csv_rows(trace_csv)
    if not rows:
        return {}

    peak_rho_sum = _max_finite(_safe_float(r.get("rhoSum")) for r in rows)
    peak_rho_entropy = _max_finite(_safe_float(r.get("rhoEntropy")) for r in rows)
    peak_rho_effn = _max_finite(_safe_float(r.get("rhoEffN")) for r in rows)
    peak_active = _max_finite(_safe_float(r.get("rhoActiveCount")) for r in rows)

    peak_rho_max = _max_finite(_safe_float(r.get("rhoMax")) for r in rows)

    # Approx: pick the rhoMaxId at the step where rhoMax hits its peak.
    best_id = ""
    best = float("nan")
    for r in rows:
        v = _safe_float(r.get("rhoMax"))
        if math.isfinite(v) and (not math.isfinite(best) or v > best):
            best = v
            best_id = str(r.get("rhoMaxId") or "")

    # Time to "hot" (adaptive trace) if present.
    hot_step = ""
    for r in rows:
        if _safe_int(r.get("hot")):
            hot_step = _safe_int(r.get("step"))
            break

    return {
        "traceRows": len(rows),
        "peakRhoSum": peak_rho_sum,
        "peakRhoEntropy": peak_rho_entropy,
        "peakRhoEffN": peak_rho_effn,
        "peakRhoActiveCount": peak_active,
        "peakRhoMax": peak_rho_max,
        "peakRhoMaxId": best_id,
        "hotStep": hot_step,
    }


def _safe_str(v: Any) -> str:
    try:
        return str(v or "")
    except Exception:
        return ""


def _load_sort_key(row: dict[str, Any]) -> float:
    knob = _safe_str(row.get("knob")).strip()
    if knob == "pulseEvery":
        pe = _safe_float(row.get("pulseEvery"))
        return 1.0 / pe if pe > 0 else float("inf")
    if knob == "agentCount":
        return _safe_float(row.get("agentCount"))
    if knob == "damping":
        return _safe_float(row.get("damping"))
    # default: injectAmount
    return _safe_float(row.get("injectAmount"))


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
        help="Path to the cognitive_load_batches/<stamp> folder (contains command_done/ and command_results/).",
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

    rows_out: list[dict[str, Any]] = []

    for cmd_path in sorted(cmd_done.glob("*.json")):
        cmd = _read_json(cmd_path)
        meta = cmd.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}

        phase = str(meta.get("phase") or "")
        if phase.upper() != "COGLOAD":
            continue

        stem = cmd_path.stem
        out_prefix = str(cmd.get("outPrefix") or "")

        knob = _safe_str(meta.get("knob") or "")
        scenario = _safe_str(meta.get("scenario") or "")

        inject_amount = float(meta.get("injectAmount") or 0.0)
        agent_count = int(meta.get("agentCount") or 0)
        targets_per_pulse = int(meta.get("targetsPerPulse") or 0)
        pulse_every = int(meta.get("pulseEvery") or 0)
        dt = _safe_float(meta.get("dt"))
        damping = _safe_float(meta.get("damping"))
        steps = _safe_int(meta.get("steps"))
        press_slider_val = _safe_float(meta.get("pressSliderVal"))
        approx_rate = _safe_float(meta.get("approxInjectRate"))

        if not inject_amount or not agent_count or not targets_per_pulse or not pulse_every:
            params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
            inject_amount = inject_amount or float((params or {}).get("injectAmount") or 0.0)
            agent_count = agent_count or len((params or {}).get("targetIds") or [])
            targets_per_pulse = targets_per_pulse or int((params or {}).get("targetsPerPulse") or 0)
            pulse_every = pulse_every or int((params or {}).get("pulseEvery") or 0)
            if not math.isfinite(dt) or dt == 0:
                dts = (params or {}).get("dts") or []
                dt = _safe_float(dts[0]) if isinstance(dts, list) and dts else dt
            if not math.isfinite(damping) or damping == 0:
                ds = (params or {}).get("dampings") or []
                damping = _safe_float(ds[0]) if isinstance(ds, list) and ds else damping
            steps = steps or _safe_int((params or {}).get("steps"))
            if not math.isfinite(press_slider_val) or press_slider_val == 0:
                press_slider_val = _safe_float((params or {}).get("pressSliderVal"))
            if not math.isfinite(approx_rate) or approx_rate == 0:
                approx_rate = float(inject_amount) * float(max(1, targets_per_pulse)) / float(max(1, pulse_every))

        res_path = _find_latest_result(cmd_results, stem)
        if not res_path:
            rows_out.append(
                {
                    "stem": stem,
                    "outPrefix": out_prefix,
                    "injectAmount": inject_amount,
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
            "outPrefix": out_prefix,
            "scenario": scenario,
            "knob": knob,
            "dt": dt if math.isfinite(dt) else "",
            "damping": damping if math.isfinite(damping) else "",
            "steps": steps if steps else "",
            "pressSliderVal": press_slider_val if math.isfinite(press_slider_val) else "",
            "injectAmount": inject_amount,
            "agentCount": agent_count,
            "targetsPerPulse": targets_per_pulse,
            "pulseEvery": pulse_every,
            "approxInjectRate": approx_rate,
            "ok": ok,
            "message": message,
            "summaryCsv": summary_name,
            "traceCsv": trace_name,
        }

        if ok and summary_name:
            sp = download_dir / summary_name
            tp = download_dir / trace_name if trace_name else None
            if sp.exists():
                row.update(_summary_metrics(sp))
            else:
                row["ok"] = False
                row["message"] = f"summary missing: {sp.name}"

            if tp and tp.exists():
                row.update(_trace_metrics(tp))
            elif trace_name:
                row["ok"] = False
                row["message"] = f"trace missing: {trace_name}"

        rows_out.append(row)

    rows_out.sort(key=_load_sort_key)

    out_csv = batch_dir / "cognitive_load_readout.csv"
    _write_csv(
        out_csv,
        rows_out,
        preferred=[
            "scenario",
            "knob",
            "dt",
            "damping",
            "steps",
            "pressSliderVal",
            "approxInjectRate",
            "injectAmount",
            "agentCount",
            "targetsPerPulse",
            "pulseEvery",
            "ok",
            "message",
            "summaryRows",
            "failRate",
            "minFailStep",
            "peakMeanP_max",
            "peakPMax_max",
            "peakPsiVar_max",
            "peakRhoSum",
            "peakRhoActiveCount",
            "peakRhoEntropy",
            "peakRhoEffN",
            "peakRhoMax",
            "peakRhoMaxId",
            "hotStep",
            "summaryCsv",
            "traceCsv",
            "stem",
            "outPrefix",
        ],
    )

    # Markdown synopsis
    ok_rows = [r for r in rows_out if r.get("ok")]
    first_fail = next((r for r in ok_rows if _safe_int(r.get("failRate")) or _safe_int(r.get("minFailStep"))), None)

    md_lines: list[str] = []
    md_lines.append("# Cognitive Load Sweep Readout\n")
    md_lines.append(f"Commands analyzed: {len(rows_out)}")
    md_lines.append(f"OK: {len(ok_rows)}\n")

    if first_fail:
        md_lines.append("## First observed failure")
        md_lines.append(f"- injectAmount: {first_fail.get('injectAmount')}")
        md_lines.append(f"- minFailStep: {first_fail.get('minFailStep')}")
        md_lines.append(f"- peakMeanP_max: {_fmt(first_fail.get('peakMeanP_max'))}")
        md_lines.append(f"- peakPMax_max: {_fmt(first_fail.get('peakPMax_max'))}\n")

    # Quick table (small)
    md_lines.append("## Summary (selected points)\n")
    md_lines.append("| scenario | knob | damping | approxRate | injectAmount | agents | perPulse | pulseEvery | ok | minFailStep | peakMeanP | peakPMax | peakRhoSum | rhoEffN | rhoActive |")
    md_lines.append("|:--|:--|---:|---:|---:|---:|---:|---:|:--:|---:|---:|---:|---:|---:|---:|")

    # Keep table short: first 5 + last 5
    head = ok_rows[:5]
    tail = ok_rows[-5:] if len(ok_rows) > 10 else []
    for r in head + tail:
        md_lines.append(
            "| "
            f"{r.get('scenario') or ''} | "
            f"{r.get('knob') or ''} | "
            f"{_fmt(r.get('damping'))} | "
            f"{_fmt(r.get('approxInjectRate'))} | "
            f"{r.get('injectAmount')} | "
            f"{r.get('agentCount') or ''} | "
            f"{r.get('targetsPerPulse') or ''} | "
            f"{r.get('pulseEvery') or ''} | "
            f"{('Y' if r.get('ok') else 'N')} | "
            f"{r.get('minFailStep') or ''} | "
            f"{_fmt(r.get('peakMeanP_max'))} | "
            f"{_fmt(r.get('peakPMax_max'))} | "
            f"{_fmt(r.get('peakRhoSum'))} | "
            f"{_fmt(r.get('peakRhoEffN'))} | "
            f"{_fmt(r.get('peakRhoActiveCount'), digits=0)} |"
        )

    out_md = batch_dir / "cognitive_load_readout.md"
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
