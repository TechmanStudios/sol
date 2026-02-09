"""Analyze per-run trace CSVs around phase-layer boundaries.

This script is intended to complement the existing cognitive-load sweep analyzers.
Instead of focusing on per-point summary readouts, it scans the raw *_trace_*.csv
files (one per run) and extracts step-resolved "mass jump" characteristics.

Outputs (written to --out-dir):
- phase_layer_trace_runs.csv   (one row per trace file)
- phase_layer_trace_agg.csv    (aggregated by damping)
- phase_layer_trace_report.md  (compact, audit-friendly report)

Design goals:
- Dependency-free (stdlib only)
- Deterministic ordering
- Works on existing batch directories produced by run_dashboard_sweep.py

Typical usage:
  python tools/dashboard_automation/analyze_phase_layer_traces.py \
    --batch-dir solData/testResults/cogload_replications/<stamp>/window_B_1869_budget
"""

from __future__ import annotations

import argparse
import csv
import decimal
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


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


def _isfinite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _stdev(xs: list[float]) -> float:
    xs = [float(x) for x in xs if _isfinite(x)]
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def _as_decimal_str(raw: Any) -> str:
    s = str(raw).strip() if raw is not None else ""
    return s


def _safe_decimal(raw: Any) -> decimal.Decimal | None:
    s = _as_decimal_str(raw)
    if not s:
        return None
    try:
        return decimal.Decimal(s)
    except Exception:
        # Fall back to float parse to handle odd strings like "1e-3".
        try:
            return decimal.Decimal(str(float(s)))
        except Exception:
            return None


def _quantile(xs: list[float], q: float) -> float:
    """Deterministic quantile with linear interpolation.

    q in [0, 1]. Returns NaN if no finite values.
    """
    vals = sorted(float(x) for x in xs if _isfinite(float(x)))
    if not vals:
        return float("nan")
    if q <= 0:
        return vals[0]
    if q >= 1:
        return vals[-1]
    # Position in [0, n-1]
    pos = q * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


@dataclass(frozen=True)
class RunRow:
    trace_file: str
    summary_file: str
    run_id: str
    dt: float
    damping: float
    damping_raw: str
    damping_dec: decimal.Decimal | None
    steps_recorded: int

    failed: bool
    fail_step: float
    peak_mean_p: float
    peak_pmax: float
    peak_psi_var: float

    rho_base: float
    rho_tail: float
    rho_delta: float
    rho_mid: float
    jump_step: float

    rho_max: float
    rho_max_step: float

    rho_slope_max: float
    rho_slope_step: float

    pmax_max: float
    pmax_step: float


def _read_summary(path: Path) -> dict[str, float] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    r0 = rows[0]
    failed = _safe_int(r0.get("failed"))
    return {
        "failed": float(failed),
        "fail_step": _safe_float(r0.get("failStep")),
        "peak_mean_p": _safe_float(r0.get("peakMeanP")),
        "peak_pmax": _safe_float(r0.get("peakPMax")),
        "peak_psi_var": _safe_float(r0.get("peakPsiVar")),
    }


def _read_trace(path: Path, *, baseline_n: int, tail_n: int) -> RunRow | None:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return None

    run_id = str(rows[0].get("runId") or "")
    dt = _safe_float(rows[0].get("dt"))
    damping_raw = _as_decimal_str(rows[0].get("damping"))
    damping_dec = _safe_decimal(damping_raw)
    damping = _safe_float(damping_raw)

    summary_path = path.with_name(path.name.replace("_trace_", "_summary_"))
    summary = _read_summary(summary_path) or {}
    failed = bool(_safe_int(summary.get("failed")))
    fail_step = _safe_float(summary.get("fail_step"))
    peak_mean_p = _safe_float(summary.get("peak_mean_p"))
    peak_pmax = _safe_float(summary.get("peak_pmax"))
    peak_psi_var = _safe_float(summary.get("peak_psi_var"))

    steps: list[int] = []
    rho: list[float] = []
    pmax: list[float] = []

    for r in rows:
        steps.append(_safe_int(r.get("step")))
        rho.append(_safe_float(r.get("rhoSum")))
        pmax.append(_safe_float(r.get("pMax")))

    n = len(steps)

    # Baseline: first baseline_n samples with step > 0 (skip step 0 if present)
    base_samples: list[float] = []
    for s, v in zip(steps, rho, strict=False):
        if s <= 0:
            continue
        if _isfinite(v):
            base_samples.append(v)
        if len(base_samples) >= baseline_n:
            break
    if not base_samples:
        base_samples = [v for v in rho[:baseline_n] if _isfinite(v)]

    rho_base = mean(base_samples) if base_samples else float("nan")

    tail_candidates = [v for v in rho[-tail_n:] if _isfinite(v)]
    rho_tail = mean(tail_candidates) if tail_candidates else float("nan")

    rho_delta = rho_tail - rho_base if (_isfinite(rho_tail) and _isfinite(rho_base)) else float("nan")
    rho_mid = rho_base + 0.5 * rho_delta if _isfinite(rho_delta) and _isfinite(rho_base) else float("nan")

    # Jump step: first step where rho crosses midpoint between base and tail.
    jump_step = float("nan")
    if _isfinite(rho_mid):
        for s, v in zip(steps, rho, strict=False):
            if _isfinite(v) and v >= rho_mid:
                jump_step = float(s)
                break

    # Max rho and its step.
    rho_max = float("nan")
    rho_max_step = float("nan")
    for s, v in zip(steps, rho, strict=False):
        if not _isfinite(v):
            continue
        if (not _isfinite(rho_max)) or v > rho_max:
            rho_max = float(v)
            rho_max_step = float(s)

    # Max rho slope.
    rho_slope_max = float("nan")
    rho_slope_step = float("nan")
    for i in range(1, n):
        s0, s1 = steps[i - 1], steps[i]
        v0, v1 = rho[i - 1], rho[i]
        if s1 <= s0:
            continue
        if not (_isfinite(v0) and _isfinite(v1)):
            continue
        slope = (v1 - v0) / float(s1 - s0)
        if (not _isfinite(rho_slope_max)) or slope > rho_slope_max:
            rho_slope_max = float(slope)
            rho_slope_step = float(s1)

    # Max pMax and its step.
    pmax_max = float("nan")
    pmax_step = float("nan")
    for s, v in zip(steps, pmax, strict=False):
        if not _isfinite(v):
            continue
        if (not _isfinite(pmax_max)) or v > pmax_max:
            pmax_max = float(v)
            pmax_step = float(s)

    return RunRow(
        trace_file=path.name,
        summary_file=summary_path.name if summary_path.exists() else "",
        run_id=run_id,
        dt=dt,
        damping=damping,
        damping_raw=damping_raw,
        damping_dec=damping_dec,
        steps_recorded=n,

        failed=failed,
        fail_step=fail_step,
        peak_mean_p=peak_mean_p,
        peak_pmax=peak_pmax,
        peak_psi_var=peak_psi_var,
        rho_base=rho_base,
        rho_tail=rho_tail,
        rho_delta=rho_delta,
        rho_mid=rho_mid,
        jump_step=jump_step,
        rho_max=rho_max,
        rho_max_step=rho_max_step,
        rho_slope_max=rho_slope_max,
        rho_slope_step=rho_slope_step,
        pmax_max=pmax_max,
        pmax_step=pmax_step,
    )


def _fmt_num(x: float, digits: int = 6) -> str:
    if not _isfinite(x):
        return ""
    return f"{float(x):.{digits}f}"


def _fmt_dec(d: decimal.Decimal | None, digits: int = 12) -> str:
    if d is None:
        return ""
    try:
        q = decimal.Decimal(1).scaleb(-digits)  # 10^-digits
        return format(d.quantize(q), "f")
    except Exception:
        return str(d)


def _fmt_int(x: float) -> str:
    if not _isfinite(x):
        return ""
    return str(int(round(float(x))))


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", required=True, help="Batch directory containing *_trace_*.csv files.")
    ap.add_argument(
        "--out-dir",
        default="",
        help="Output directory (default: <batch-dir>/phase_layer).",
    )
    ap.add_argument("--baseline-n", type=int, default=3, help="Samples for baseline mean (skip step 0).")
    ap.add_argument("--tail-n", type=int, default=3, help="Samples for tail mean.")
    ap.add_argument(
        "--budget",
        type=int,
        default=0,
        help="Optional step budget (e.g., 1200). If set, reports pass-rate per damping.",
    )
    ap.add_argument(
        "--report-digits",
        type=int,
        default=9,
        help="Digits to display for damping in the markdown report.",
    )
    ap.add_argument(
        "--agg-digits",
        type=int,
        default=6,
        help="Default decimal digits for aggregate float columns.",
    )
    ap.add_argument(
        "--plateau-eps",
        type=float,
        default=0.0,
        help=(
            "If >0, flag adjacent damping rows as a potential plateau when key aggregate means match within this epsilon. "
            "Use 0 to only flag exact-string matches in the fingerprint."
        ),
    )

    args = ap.parse_args()

    batch_dir = Path(args.batch_dir).resolve()
    if not batch_dir.exists():
        raise SystemExit(f"batch dir not found: {batch_dir}")

    out_dir = Path(args.out_dir).resolve() if str(args.out_dir).strip() else (batch_dir / "phase_layer")
    out_dir.mkdir(parents=True, exist_ok=True)

    trace_files = sorted(batch_dir.glob("*_trace_*.csv"), key=lambda p: p.name)
    if not trace_files:
        raise SystemExit(f"No trace files found under: {batch_dir}")

    run_rows: list[RunRow] = []
    for tf in trace_files:
        rr = _read_trace(tf, baseline_n=int(args.baseline_n), tail_n=int(args.tail_n))
        if rr is not None:
            run_rows.append(rr)

    run_rows.sort(key=lambda r: (r.damping, r.trace_file))

    runs_csv_headers = [
        "traceFile",
        "summaryFile",
        "runId",
        "dt",
        "damping",
        "dampingRaw",
        "stepsRecorded",

        "failed",
        "failStep",
        "peakMeanP",
        "peakPMax",
        "peakPsiVar",
        "rhoBase",
        "rhoTail",
        "rhoDelta",
        "rhoMid",
        "jumpStep",
        "rhoMax",
        "rhoMaxStep",
        "rhoSlopeMax",
        "rhoSlopeStep",
        "pMaxMax",
        "pMaxStep",
    ]

    runs_csv_rows: list[dict[str, Any]] = []
    for r in run_rows:
        runs_csv_rows.append(
            {
                "traceFile": r.trace_file,
                "summaryFile": r.summary_file,
                "runId": r.run_id,
                "dt": "" if not _isfinite(r.dt) else r.dt,
                "damping": "" if not _isfinite(r.damping) else r.damping,
                "dampingRaw": r.damping_raw,
                "stepsRecorded": r.steps_recorded,

                "failed": bool(r.failed),
                "failStep": "" if not _isfinite(r.fail_step) else int(r.fail_step),
                "peakMeanP": "" if not _isfinite(r.peak_mean_p) else r.peak_mean_p,
                "peakPMax": "" if not _isfinite(r.peak_pmax) else r.peak_pmax,
                "peakPsiVar": "" if not _isfinite(r.peak_psi_var) else r.peak_psi_var,
                "rhoBase": "" if not _isfinite(r.rho_base) else r.rho_base,
                "rhoTail": "" if not _isfinite(r.rho_tail) else r.rho_tail,
                "rhoDelta": "" if not _isfinite(r.rho_delta) else r.rho_delta,
                "rhoMid": "" if not _isfinite(r.rho_mid) else r.rho_mid,
                "jumpStep": "" if not _isfinite(r.jump_step) else int(r.jump_step),
                "rhoMax": "" if not _isfinite(r.rho_max) else r.rho_max,
                "rhoMaxStep": "" if not _isfinite(r.rho_max_step) else int(r.rho_max_step),
                "rhoSlopeMax": "" if not _isfinite(r.rho_slope_max) else r.rho_slope_max,
                "rhoSlopeStep": "" if not _isfinite(r.rho_slope_step) else int(r.rho_slope_step),
                "pMaxMax": "" if not _isfinite(r.pmax_max) else r.pmax_max,
                "pMaxStep": "" if not _isfinite(r.pmax_step) else int(r.pmax_step),
            }
        )

    runs_csv_path = out_dir / "phase_layer_trace_runs.csv"
    _write_csv(runs_csv_path, runs_csv_headers, runs_csv_rows)

    # Aggregate by damping.
    by_damping: dict[str, list[RunRow]] = {}
    for r in run_rows:
        if not r.damping_raw:
            continue
        by_damping.setdefault(r.damping_raw, []).append(r)

    def _damping_sort_key(raw: str) -> tuple[int, str]:
        d = _safe_decimal(raw)
        if d is None:
            return (1, raw)
        return (0, str(d))

    agg_headers = [
        "damping",
        "dampingRaw",
        "runs",
        "budget",
        "budgetPassRate",
        "failStep_max",
        "failStep_mean",
        "failStep_sd",
        "failStep_p10",
        "failStep_p50",
        "failStep_p90",
        "peakMeanP_mean",
        "peakMeanP_sd",
        "peakPMax_max",
        "peakPMax_mean",
        "peakPMax_sd",
        "peakPMax_p90",
        "jumpStep_mean",
        "jumpStep_sd",
        "jumpStep_p10",
        "jumpStep_p50",
        "jumpStep_p90",
        "rhoDelta_mean",
        "rhoDelta_sd",
        "rhoDelta_p90",
        "rhoTail_mean",
        "rhoTail_sd",
        "pMaxMax_mean",
        "pMaxMax_sd",
    ]

    agg_rows: list[dict[str, Any]] = []
    agg_digits = int(args.agg_digits)
    report_digits = int(args.report_digits)
    for d_raw in sorted(by_damping.keys(), key=_damping_sort_key):
        rs = by_damping[d_raw]
        d_dec = _safe_decimal(d_raw)
        d_float = _safe_float(d_raw)
        fail_steps = [r.fail_step for r in rs if _isfinite(r.fail_step)]
        peak_mean_ps = [r.peak_mean_p for r in rs if _isfinite(r.peak_mean_p)]
        peak_pmaxs = [r.peak_pmax for r in rs if _isfinite(r.peak_pmax)]
        js = [r.jump_step for r in rs if _isfinite(r.jump_step)]
        deltas = [r.rho_delta for r in rs if _isfinite(r.rho_delta)]
        tails = [r.rho_tail for r in rs if _isfinite(r.rho_tail)]
        pmaxs = [r.pmax_max for r in rs if _isfinite(r.pmax_max)]

        budget = int(args.budget)
        pass_rate = ""
        if budget > 0 and fail_steps:
            passed = sum(1 for fs in fail_steps if float(fs) >= float(budget))
            pass_rate = _fmt_num(passed / float(len(fail_steps)), 4)

        fail_step_max = ""
        if fail_steps:
            fail_step_max = _fmt_int(max(fail_steps))

        peak_pmax_max = ""
        if peak_pmaxs:
            peak_pmax_max = _fmt_num(max(peak_pmaxs), agg_digits)

        agg_rows.append(
            {
                # Display-friendly damping formatted from the exact raw token.
                # Keep dampingRaw alongside it so consumers can choose identity vs display.
                "damping": "" if d_dec is None else _fmt_dec(d_dec, digits=max(agg_digits, report_digits)),
                "dampingRaw": d_raw,
                "runs": len(rs),
                "budget": budget if budget > 0 else "",
                "budgetPassRate": pass_rate,
                "failStep_max": fail_step_max,
                "failStep_mean": _fmt_num(mean(fail_steps), 3) if fail_steps else "",
                "failStep_sd": _fmt_num(_stdev(fail_steps), 3) if fail_steps else "",
                "failStep_p10": _fmt_num(_quantile(fail_steps, 0.10), 1) if fail_steps else "",
                "failStep_p50": _fmt_num(_quantile(fail_steps, 0.50), 1) if fail_steps else "",
                "failStep_p90": _fmt_num(_quantile(fail_steps, 0.90), 1) if fail_steps else "",
                "peakMeanP_mean": _fmt_num(mean(peak_mean_ps), agg_digits) if peak_mean_ps else "",
                "peakMeanP_sd": _fmt_num(_stdev(peak_mean_ps), agg_digits) if peak_mean_ps else "",
                "peakPMax_max": peak_pmax_max,
                "peakPMax_mean": _fmt_num(mean(peak_pmaxs), agg_digits) if peak_pmaxs else "",
                "peakPMax_sd": _fmt_num(_stdev(peak_pmaxs), agg_digits) if peak_pmaxs else "",
                "peakPMax_p90": _fmt_num(_quantile(peak_pmaxs, 0.90), agg_digits) if peak_pmaxs else "",
                "jumpStep_mean": _fmt_num(mean(js), 3) if js else "",
                "jumpStep_sd": _fmt_num(_stdev(js), 3) if js else "",
                "jumpStep_p10": _fmt_num(_quantile(js, 0.10), 1) if js else "",
                "jumpStep_p50": _fmt_num(_quantile(js, 0.50), 1) if js else "",
                "jumpStep_p90": _fmt_num(_quantile(js, 0.90), 1) if js else "",
                "rhoDelta_mean": _fmt_num(mean(deltas), agg_digits) if deltas else "",
                "rhoDelta_sd": _fmt_num(_stdev(deltas), agg_digits) if deltas else "",
                "rhoDelta_p90": _fmt_num(_quantile(deltas, 0.90), agg_digits) if deltas else "",
                "rhoTail_mean": _fmt_num(mean(tails), agg_digits) if tails else "",
                "rhoTail_sd": _fmt_num(_stdev(tails), agg_digits) if tails else "",
                "pMaxMax_mean": _fmt_num(mean(pmaxs), agg_digits) if pmaxs else "",
                "pMaxMax_sd": _fmt_num(_stdev(pmaxs), agg_digits) if pmaxs else "",
            }
        )

    agg_csv_path = out_dir / "phase_layer_trace_agg.csv"
    _write_csv(agg_csv_path, agg_headers, agg_rows)

    # MD report.
    lines: list[str] = []
    lines.append(f"# Phase-layer trace report")
    lines.append("")
    lines.append(f"Batch: `{batch_dir}`")
    lines.append(f"Traces: {len(run_rows)}")
    lines.append("")

    lines.append("## Aggregated by damping")
    lines.append("")
    lines.append(
        "| damping | runs | pass@budget | failStep max | failStep μ | failStep p10/p90 | peakPMax max | peakPMax μ | peakPMax p90 | jumpStep μ | jumpStep p10/p90 |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in agg_rows:
        pass_cell = str(r.get("budgetPassRate") or "")
        if str(r.get("budget") or ""):
            pass_cell = f"{pass_cell} @≥{r.get('budget')}" if pass_cell else f"@≥{r.get('budget')}"
        d_disp = str(r.get("dampingRaw") or "")
        if d_disp:
            # Trim display digits for markdown readability, but base it on the exact raw string.
            d_val = _safe_decimal(d_disp)
            if d_val is not None:
                d_disp = _fmt_dec(d_val, digits=report_digits)
        else:
            d_disp = str(r.get("damping") or "")
        lines.append(
            "| "
            + " | ".join(
                [
                    d_disp,
                    str(r.get("runs")),
                    pass_cell,
                    str(r.get("failStep_max") or ""),
                    str(r.get("failStep_mean") or ""),
                    (str(r.get("failStep_p10") or "") + "/" + str(r.get("failStep_p90") or "")).strip("/"),
                    str(r.get("peakPMax_max") or ""),
                    str(r.get("peakPMax_mean") or ""),
                    str(r.get("peakPMax_p90") or ""),
                    str(r.get("jumpStep_mean") or ""),
                    (str(r.get("jumpStep_p10") or "") + "/" + str(r.get("jumpStep_p90") or "")).strip("/"),
                ]
            )
            + " |"
        )

    # Plateau detection (adjacent rows only).
    eps = float(args.plateau_eps)
    def _f(x: Any) -> float:
        return _safe_float(x)
    def _close(a: Any, b: Any) -> bool:
        if eps <= 0:
            return str(a) == str(b)
        aa = _f(a)
        bb = _f(b)
        if not (_isfinite(aa) and _isfinite(bb)):
            return False
        return abs(aa - bb) <= eps

    # Tight plateau fingerprint: include multiple high-resolution aggregates
    # so we don't over-flag regimes that only match on a few coarse means.
    plateau_fields = [
        "budgetPassRate",
        "failStep_mean",
        "failStep_p50",
        "peakMeanP_mean",
        "peakPMax_mean",
        "peakPMax_p90",
        "jumpStep_mean",
        "jumpStep_p50",
        "rhoDelta_mean",
        "rhoDelta_p90",
        "rhoTail_mean",
    ]

    plateaus: list[tuple[str, str]] = []
    for i in range(1, len(agg_rows)):
        prev = agg_rows[i - 1]
        cur = agg_rows[i]
        same = True
        for k in plateau_fields:
            if not _close(prev.get(k), cur.get(k)):
                same = False
                break
        if same:
            plateaus.append((str(prev.get("dampingRaw") or prev.get("damping") or ""), str(cur.get("dampingRaw") or cur.get("damping") or "")))

    if plateaus:
        lines.append("")
        lines.append("## Potential plateaus")
        lines.append("")
        lines.append(
            "Adjacent damping rows with matching aggregate fingerprints "
            + (f"(epsilon={eps})" if eps > 0 else "(exact-string match)")
            + ":"
        )
        for a, b in plateaus:
            lines.append(f"- {a} -> {b}")

    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append(f"- Runs CSV: `{runs_csv_path}`")
    lines.append(f"- Aggregates CSV: `{agg_csv_path}`")

    report_path = out_dir / "phase_layer_trace_report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {runs_csv_path}")
    print(f"Wrote: {agg_csv_path}")
    print(f"Wrote: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
