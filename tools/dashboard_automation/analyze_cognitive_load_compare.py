"""Compare multiple cognitive-load sweep batches.

This reads per-batch outputs produced by analyze_cognitive_load_sweep.py
(i.e., <batch_dir>/cognitive_load_readout.csv) and produces a combined
comparison table plus an SVG plot.

Outputs (written to --out-dir):
- cognitive_load_compare.csv
- cognitive_load_compare.md
- cognitive_load_compare_minFailStep.svg
- cognitive_load_compare_peakPMax.svg
- cognitive_load_compare_peakMeanP.svg
- cognitive_load_compare_rhoEffN.svg
- cognitive_load_compare_peakRhoSum.svg

Design goals:
- Dependency-free (stdlib only)
- Deterministic ordering
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class Row:
    scenario: str
    knob: str
    dt: float
    damping: float
    approx_inject_rate: float
    inject_amount: float
    agent_count: int
    targets_per_pulse: int
    pulse_every: int
    ok: bool
    min_fail_step: float
    peak_mean_p: float
    peak_pmax: float
    peak_rho_sum: float
    rho_eff_n: float
    batch_dir: str


def _safe_str(v: Any) -> str:
    try:
        return str(v or "")
    except Exception:
        return ""


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


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _read_row(r: dict[str, str], batch_dir: Path) -> Row:
    return Row(
        scenario=_safe_str(r.get("scenario")),
        knob=_safe_str(r.get("knob")),
        dt=_safe_float(r.get("dt")),
        damping=_safe_float(r.get("damping")),
        approx_inject_rate=_safe_float(r.get("approxInjectRate")),
        inject_amount=_safe_float(r.get("injectAmount")),
        agent_count=_safe_int(r.get("agentCount")),
        targets_per_pulse=_safe_int(r.get("targetsPerPulse")),
        pulse_every=_safe_int(r.get("pulseEvery")),
        ok=str(r.get("ok") or "").strip().lower() in {"true", "1", "y", "yes"},
        min_fail_step=_safe_float(r.get("minFailStep")),
        peak_mean_p=_safe_float(r.get("peakMeanP_max")),
        peak_pmax=_safe_float(r.get("peakPMax_max")),
        peak_rho_sum=_safe_float(r.get("peakRhoSum")),
        rho_eff_n=_safe_float(r.get("peakRhoEffN")),
        batch_dir=str(batch_dir),
    )


def _isfinite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _write_csv(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "scenario",
        "knob",
        "dt",
        "damping",
        "approxInjectRate",
        "injectAmount",
        "agentCount",
        "targetsPerPulse",
        "pulseEvery",
        "ok",
        "minFailStep",
        "peakMeanP_max",
        "peakPMax_max",
        "peakRhoSum",
        "peakRhoEffN",
        "batchDir",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for row in rows:
            w.writerow(
                {
                    "scenario": row.scenario,
                    "knob": row.knob,
                    "dt": "" if not _isfinite(row.dt) else row.dt,
                    "damping": "" if not _isfinite(row.damping) else row.damping,
                    "approxInjectRate": row.approx_inject_rate,
                    "injectAmount": row.inject_amount,
                    "agentCount": row.agent_count,
                    "targetsPerPulse": row.targets_per_pulse,
                    "pulseEvery": row.pulse_every,
                    "ok": row.ok,
                    "minFailStep": "" if not _isfinite(row.min_fail_step) else int(row.min_fail_step),
                    "peakMeanP_max": "" if not _isfinite(row.peak_mean_p) else row.peak_mean_p,
                    "peakPMax_max": "" if not _isfinite(row.peak_pmax) else row.peak_pmax,
                    "peakRhoSum": "" if not _isfinite(row.peak_rho_sum) else row.peak_rho_sum,
                    "peakRhoEffN": "" if not _isfinite(row.rho_eff_n) else row.rho_eff_n,
                    "batchDir": row.batch_dir,
                }
            )


def _fmt_num(x: float, digits: int = 4) -> str:
    if not _isfinite(x):
        return ""
    return f"{float(x):.{digits}f}"


def _fmt_int(x: float) -> str:
    if not _isfinite(x):
        return ""
    return str(int(round(float(x))))


def _render_md_table(rows: list[Row]) -> str:
    cols = [
        ("scenario", lambda r: r.scenario),
        ("damping", lambda r: _fmt_num(r.damping, 4)),
        ("approxRate", lambda r: _fmt_num(r.approx_inject_rate, 4)),
        ("pulseEvery", lambda r: str(r.pulse_every)),
        ("agents", lambda r: str(r.agent_count)),
        ("perPulse", lambda r: str(r.targets_per_pulse)),
        ("minFailStep", lambda r: _fmt_int(r.min_fail_step)),
        ("peakMeanP", lambda r: _fmt_num(r.peak_mean_p, 4)),
        ("peakPMax", lambda r: _fmt_num(r.peak_pmax, 4)),
        ("peakRhoSum", lambda r: _fmt_num(r.peak_rho_sum, 2)),
        ("rhoEffN", lambda r: _fmt_num(r.rho_eff_n, 2)),
    ]

    header = "| " + " | ".join(c[0] for c in cols) + " |"
    sep = "|" + "|".join(":--" if i == 0 else "---:" for i in range(len(cols))) + "|"

    lines = [header, sep]
    for r in rows:
        lines.append("| " + " | ".join(fn(r) for _, fn in cols) + " |")
    return "\n".join(lines)


def _render_capacity_table(rows: list[Row], step_budgets: list[int]) -> str:
    """For each scenario, report the max approxInjectRate that still lasts >= N steps."""

    by_scenario: dict[str, list[Row]] = {}
    for r in rows:
        if not (_isfinite(r.approx_inject_rate) and _isfinite(r.min_fail_step)):
            continue
        by_scenario.setdefault(r.scenario or "(unknown)", []).append(r)

    scenarios = sorted(by_scenario.keys())

    def max_rate_at_budget(sc: str, budget: int) -> float:
        best = float("nan")
        for r in by_scenario.get(sc, []):
            if float(r.min_fail_step) >= float(budget):
                rate = float(r.approx_inject_rate)
                if not _isfinite(best) or rate > best:
                    best = rate
        return best

    header = "| scenario | " + " | ".join(f"maxRate @≥{b}" for b in step_budgets) + " |"
    sep = "|:--|" + "|".join("---:" for _ in step_budgets) + "|"
    lines = [header, sep]
    for sc in scenarios:
        cells = [sc]
        for b in step_budgets:
            v = max_rate_at_budget(sc, b)
            cells.append(_fmt_num(v, 4) if _isfinite(v) else "")
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _render_operating_point_table(
    rows: list[Row],
    *,
    step_budgets: list[int],
    peak_mean_p_caps: list[float],
) -> str:
    """Pick best 'operating point' per scenario under constraints.

    Objective (compute-substrate oriented):
    - Must survive at least `budget` steps (minFailStep >= budget)
    - Must keep sustained pressure under cap (peakMeanP_max <= cap), if cap is finite
    - Among feasible points: maximize rhoEffN (spread), tie-break by higher approxInjectRate

    Returns a markdown table.
    """

    def feasible(r: Row, budget: int, cap: float) -> bool:
        if not (_isfinite(r.approx_inject_rate) and _isfinite(r.min_fail_step) and _isfinite(r.rho_eff_n)):
            return False
        if float(r.min_fail_step) < float(budget):
            return False
        if _isfinite(cap):
            if not _isfinite(r.peak_mean_p) or float(r.peak_mean_p) > float(cap):
                return False
        return True

    scenarios = sorted({r.scenario or "(unknown)" for r in rows})

    def pick(sc: str, budget: int, cap: float) -> Row | None:
        best: Row | None = None
        for r in rows:
            if (r.scenario or "(unknown)") != sc:
                continue
            if not feasible(r, budget, cap):
                continue
            if best is None:
                best = r
                continue
            # maximize rhoEffN, then approxRate
            if float(r.rho_eff_n) > float(best.rho_eff_n) + 1e-9:
                best = r
            elif abs(float(r.rho_eff_n) - float(best.rho_eff_n)) <= 1e-9:
                if float(r.approx_inject_rate) > float(best.approx_inject_rate) + 1e-12:
                    best = r
        return best

    def cap_label(cap: float) -> str:
        return "(no cap)" if not _isfinite(cap) else f"≤{cap:g}"

    # Build a wide table: rows = scenario + budget, cols = each cap.
    header = "| scenario | budget | " + " | ".join(f"best rhoEffN @peakMeanP {cap_label(c)}" for c in peak_mean_p_caps) + " |"
    sep = "|:--|---:|" + "|".join("---:" for _ in peak_mean_p_caps) + "|"
    lines = [header, sep]

    for sc in scenarios:
        for budget in step_budgets:
            cells: list[str] = [sc, str(budget)]
            for cap in peak_mean_p_caps:
                r = pick(sc, budget, cap)
                if r is None:
                    cells.append("")
                else:
                    cells.append(f"{_fmt_num(r.rho_eff_n, 2)} @rate={_fmt_num(r.approx_inject_rate, 4)}")
            lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _render_frontier_table(rows: list[Row], *, budget: int, cap: float) -> str:
    """Non-dominated points in (approxRate, rhoEffN) for each scenario under constraints."""

    def feasible(r: Row) -> bool:
        if not (_isfinite(r.approx_inject_rate) and _isfinite(r.min_fail_step) and _isfinite(r.rho_eff_n)):
            return False
        if float(r.min_fail_step) < float(budget):
            return False
        if _isfinite(cap):
            if not _isfinite(r.peak_mean_p) or float(r.peak_mean_p) > float(cap):
                return False
        return True

    scenarios = sorted({r.scenario or "(unknown)" for r in rows})

    def nondominated(points: list[Row]) -> list[Row]:
        # Keep points where no other point has both rate>= and effN>= with at least one strict.
        pts = [p for p in points if feasible(p)]
        out: list[Row] = []
        for p in pts:
            dominated = False
            for q in pts:
                if q is p:
                    continue
                if float(q.approx_inject_rate) >= float(p.approx_inject_rate) and float(q.rho_eff_n) >= float(p.rho_eff_n):
                    if float(q.approx_inject_rate) > float(p.approx_inject_rate) or float(q.rho_eff_n) > float(p.rho_eff_n):
                        dominated = True
                        break
            if not dominated:
                out.append(p)
        # Sort for readability.
        out.sort(key=lambda r: (float(r.approx_inject_rate), float(r.rho_eff_n)))
        return out

    header = "| scenario | approxRate | rhoEffN | minFailStep | peakMeanP | peakPMax | pulseEvery |"
    sep = "|:--|---:|---:|---:|---:|---:|---:|"
    lines = [header, sep]

    for sc in scenarios:
        pts = [r for r in rows if (r.scenario or "(unknown)") == sc]
        frontier = nondominated(pts)
        for r in frontier:
            lines.append(
                "| "
                + " | ".join(
                    [
                        sc,
                        _fmt_num(r.approx_inject_rate, 4),
                        _fmt_num(r.rho_eff_n, 2),
                        _fmt_int(r.min_fail_step),
                        _fmt_num(r.peak_mean_p, 4),
                        _fmt_num(r.peak_pmax, 4),
                        str(r.pulse_every),
                    ]
                )
                + " |"
            )

    return "\n".join(lines)


def _minmax_norm(value: float, vmin: float, vmax: float) -> float:
    if not (_isfinite(value) and _isfinite(vmin) and _isfinite(vmax)):
        return float("nan")
    if vmax <= vmin:
        return 0.0
    return (float(value) - float(vmin)) / (float(vmax) - float(vmin))


def _decision_ready_recommendations(
    rows: list[Row],
    *,
    budget: int,
    peak_mean_p_cap: float,
    top_n: int,
    per_scenario_top_k: int,
    w_spread: float,
    w_rate: float,
    w_mean_p: float,
    w_pmax: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (global_top, per_scenario_top) recommendation rows.

    Feasibility:
    - minFailStep >= budget
    - peakMeanP <= cap (if cap finite)

    Score (min-max normalized over the feasible set):
    score = wSpread*norm(rhoEffN) + wRate*norm(approxRate)
            - wMeanP*norm(peakMeanP) - wPMax*norm(peakPMax)
    """

    feasible: list[Row] = []
    for r in rows:
        if not (_isfinite(r.approx_inject_rate) and _isfinite(r.rho_eff_n) and _isfinite(r.min_fail_step)):
            continue
        if float(r.min_fail_step) < float(budget):
            continue
        if _isfinite(peak_mean_p_cap):
            if not _isfinite(r.peak_mean_p) or float(r.peak_mean_p) > float(peak_mean_p_cap):
                continue
        if not (_isfinite(r.peak_mean_p) and _isfinite(r.peak_pmax)):
            continue
        feasible.append(r)

    if not feasible:
        return ([], [])

    rate_min = min(float(r.approx_inject_rate) for r in feasible)
    rate_max = max(float(r.approx_inject_rate) for r in feasible)
    spread_min = min(float(r.rho_eff_n) for r in feasible)
    spread_max = max(float(r.rho_eff_n) for r in feasible)
    meanp_min = min(float(r.peak_mean_p) for r in feasible)
    meanp_max = max(float(r.peak_mean_p) for r in feasible)
    pmax_min = min(float(r.peak_pmax) for r in feasible)
    pmax_max = max(float(r.peak_pmax) for r in feasible)

    scored: list[tuple[float, Row]] = []
    for r in feasible:
        n_rate = _minmax_norm(float(r.approx_inject_rate), rate_min, rate_max)
        n_spread = _minmax_norm(float(r.rho_eff_n), spread_min, spread_max)
        n_meanp = _minmax_norm(float(r.peak_mean_p), meanp_min, meanp_max)
        n_pmax = _minmax_norm(float(r.peak_pmax), pmax_min, pmax_max)

        score = 0.0
        score += float(w_spread) * (n_spread if _isfinite(n_spread) else 0.0)
        score += float(w_rate) * (n_rate if _isfinite(n_rate) else 0.0)
        score -= float(w_mean_p) * (n_meanp if _isfinite(n_meanp) else 0.0)
        score -= float(w_pmax) * (n_pmax if _isfinite(n_pmax) else 0.0)

        scored.append((score, r))

    scored.sort(key=lambda t: (-t[0], -float(t[1].rho_eff_n), -float(t[1].approx_inject_rate)))

    def as_dict(rank: int, score: float, r: Row) -> dict[str, Any]:
        return {
            "rank": rank,
            "scenario": r.scenario or "(unknown)",
            "score": score,
            "damping": float(r.damping),
            "approxRate": float(r.approx_inject_rate),
            "rhoEffN": float(r.rho_eff_n),
            "minFailStep": float(r.min_fail_step),
            "peakMeanP": float(r.peak_mean_p),
            "peakPMax": float(r.peak_pmax),
            "pulseEvery": r.pulse_every,
        }

    global_top: list[dict[str, Any]] = []
    for i, (score, r) in enumerate(scored[: max(0, int(top_n))], start=1):
        global_top.append(as_dict(i, score, r))

    per_scenario: list[dict[str, Any]] = []
    scenarios = sorted({r.scenario or "(unknown)" for _, r in scored})
    for sc in scenarios:
        k = 0
        for score, r in scored:
            if (r.scenario or "(unknown)") != sc:
                continue
            k += 1
            per_scenario.append(as_dict(k, score, r))
            if k >= int(per_scenario_top_k):
                break

    return (global_top, per_scenario)


def _render_reco_md(title: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"{title}\n\n(no feasible rows)"

    header = "| rank | scenario | score | damping | approxRate | rhoEffN | minFailStep | peakMeanP | peakPMax | bandwidth | pulseEvery |"
    sep = "|---:|:--|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = [title, "", header, sep]
    for r in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(int(r.get("rank") or 0)),
                    str(r.get("scenario") or ""),
                    _fmt_num(float(r.get("score") or 0.0), 4),
                    _fmt_num(float(r.get("damping") or 0.0), 4),
                    _fmt_num(float(r.get("approxRate") or 0.0), 4),
                    _fmt_num(float(r.get("rhoEffN") or 0.0), 2),
                    _fmt_int(float(r.get("minFailStep") or 0.0)),
                    _fmt_num(float(r.get("peakMeanP") or 0.0), 4),
                    _fmt_num(float(r.get("peakPMax") or 0.0), 4),
                    _fmt_num(float(r.get("bandwidth") or 0.0), 2),
                    str(int(r.get("pulseEvery") or 0)),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _add_bandwidth(rows: list[dict[str, Any]], *, budget: int) -> list[dict[str, Any]]:
    """Annotate recommendation dicts with a simple sustained bandwidth proxy.

    We treat the compute-window budget as the usable window; bandwidth is
    approxInjectRate * min(minFailStep, budget).
    """
    out: list[dict[str, Any]] = []
    for r in rows:
        rate = _safe_float(r.get("approxRate"))
        steps = _safe_float(r.get("minFailStep"))
        usable = min(float(budget), steps) if _isfinite(steps) else float(budget)
        bw = rate * usable if _isfinite(rate) else float("nan")
        rr = dict(r)
        rr["bandwidth"] = bw
        out.append(rr)
    return out


def _clip(x: float, lo: float, hi: float) -> float:
    if not _isfinite(x):
        return float("nan")
    return max(float(lo), min(float(hi), float(x)))


def _slice_key(r: Row) -> tuple[str, int, float]:
    # Group by scenario + pulseEvery (load) with an approxRate label for readability.
    # approxRate comes from injectAmount * targetsPerPulse / pulseEvery.
    sc = r.scenario or "(unknown)"
    pe = int(r.pulse_every) if r.pulse_every else 0
    rate = float(r.approx_inject_rate) if _isfinite(r.approx_inject_rate) else float("nan")
    # Rounded rate stabilizes keys when CSV prints floats.
    rate_key = round(rate, 6) if _isfinite(rate) else float("nan")
    return (sc, pe, rate_key)


def _pick_controller_setpoints(
    *,
    rows: list[Row],
    c_bandwidth_tol: float = 0.02,
    include_pure_c: bool = False,
) -> list[dict[str, Any]]:
    """Pick damping setpoints per load slice for A/B/C (+ Balanced).

    This is intended as a controller-friendly summary: for each (scenario, pulseEvery)
    slice, choose the *damping* that best matches each objective.

    Objectives:
    - A (runtime): maximize minFailStep (tie-break lower peakMeanP)
    - B (spread): maximize rhoEffN subject to minFailStep>=1200 and peakMeanP<=2.5
                 (fallback: relax cap, then relax budget)
    - C (bandwidth): maximize bandwidth proxy = approxRate * min(minFailStep, 1200)
                    subject to peakMeanP<=2.5 (fallback: relax cap).
                    When bandwidth is within a small tolerance of the best in-slice,
                    prefer lower spike/stress (peakPMax, then peakMeanP).
    - Balanced: maximize a normalized score within slice:
        0.45*norm(clip(minFailStep,0,1200)) + 0.45*norm(rhoEffN) - 0.10*norm(peakMeanP)

    Returns a list of dict rows suitable for CSV/MD rendering.
    """

    # Only keep rows with the fields we need.
    usable: list[Row] = []
    for r in rows:
        if not r.ok:
            continue
        if not (_isfinite(r.damping) and _isfinite(r.min_fail_step) and _isfinite(r.rho_eff_n)):
            continue
        if not (_isfinite(r.approx_inject_rate) and _isfinite(r.peak_mean_p) and _isfinite(r.peak_pmax)):
            continue
        if not r.pulse_every:
            continue
        usable.append(r)

    by_slice: dict[tuple[str, int, float], list[Row]] = {}
    for r in usable:
        by_slice.setdefault(_slice_key(r), []).append(r)

    out: list[dict[str, Any]] = []
    for (scenario, pulse_every, rate_key), pts in sorted(by_slice.items(), key=lambda t: (t[0][0], t[0][1])):
        # Deterministic ordering by damping.
        pts = sorted(pts, key=lambda r: float(r.damping))

        def pick_max(key_fn, pool: list[Row]) -> Row | None:
            best: Row | None = None
            for r in pool:
                if best is None:
                    best = r
                    continue
                if float(key_fn(r)) > float(key_fn(best)) + 1e-12:
                    best = r
            return best

        # A: runtime
        a_best = None
        # max minFailStep, tie-break lower meanP, then lower damping
        for r in pts:
            if a_best is None:
                a_best = r
                continue
            if float(r.min_fail_step) > float(a_best.min_fail_step) + 1e-9:
                a_best = r
                continue
            if abs(float(r.min_fail_step) - float(a_best.min_fail_step)) <= 1e-9:
                if float(r.peak_mean_p) < float(a_best.peak_mean_p) - 1e-9:
                    a_best = r
                    continue
                if abs(float(r.peak_mean_p) - float(a_best.peak_mean_p)) <= 1e-9 and float(r.damping) < float(a_best.damping):
                    a_best = r

        # B: spread, with fallbacks
        def b_pool(min_steps: int, cap: float) -> list[Row]:
            pool: list[Row] = []
            for r in pts:
                if float(r.min_fail_step) < float(min_steps):
                    continue
                if _isfinite(cap) and float(r.peak_mean_p) > float(cap):
                    continue
                pool.append(r)
            return pool

        b_best = pick_max(lambda r: r.rho_eff_n, b_pool(1200, 2.5))
        if b_best is None:
            b_best = pick_max(lambda r: r.rho_eff_n, b_pool(1200, float("inf")))
        if b_best is None:
            b_best = pick_max(lambda r: r.rho_eff_n, b_pool(0, float("inf")))

        # C: sustained bandwidth proxy @ budget=1200, with fallback on cap
        def bw(r: Row) -> float:
            usable_steps = min(float(1200), float(r.min_fail_step))
            return float(r.approx_inject_rate) * usable_steps

        def c_pool(cap: float) -> list[Row]:
            if not _isfinite(cap):
                return list(pts)
            return [r for r in pts if float(r.peak_mean_p) <= float(cap)]

        def pick_c(pool: list[Row], *, bw_tol: float) -> Row | None:
            if not pool:
                return None

            # First, identify the best bandwidth within this slice.
            bw_vals = [bw(r) for r in pool]
            best_bw = max(bw_vals)

            # "Tighten C": if bandwidth is effectively the same, strongly prefer
            # lower spike/stress. This avoids selecting spiky regimes for tiny
            # bandwidth gains.
            bw_tol = float(bw_tol)
            if not _isfinite(bw_tol) or bw_tol < 0:
                bw_tol = 0.0
            if bw_tol > 1.0:
                bw_tol = 1.0

            cutoff = best_bw * (1.0 - bw_tol)
            near_best = [r for r in pool if bw(r) >= cutoff - 1e-12]
            if not near_best:
                near_best = list(pool)

            # Penalize spikes explicitly within the near-best set.
            # Primary: minimize peakPMax, then minimize peakMeanP,
            # then maximize rhoEffN, then prefer lower damping.
            best: Row | None = None
            for r in near_best:
                if best is None:
                    best = r
                    continue
                if float(r.peak_pmax) < float(best.peak_pmax) - 1e-9:
                    best = r
                    continue
                if abs(float(r.peak_pmax) - float(best.peak_pmax)) <= 1e-9:
                    if float(r.peak_mean_p) < float(best.peak_mean_p) - 1e-9:
                        best = r
                        continue
                    if abs(float(r.peak_mean_p) - float(best.peak_mean_p)) <= 1e-9:
                        if float(r.rho_eff_n) > float(best.rho_eff_n) + 1e-9:
                            best = r
                            continue
                        if abs(float(r.rho_eff_n) - float(best.rho_eff_n)) <= 1e-9 and float(r.damping) < float(best.damping):
                            best = r
            return best

        c_best = None
        for pool in (c_pool(2.5), c_pool(float("inf"))):
            c_best = pick_c(pool, bw_tol=float(c_bandwidth_tol))
            if c_best is not None:
                break

        c0_best = None
        if include_pure_c:
            for pool in (c_pool(2.5), c_pool(float("inf"))):
                c0_best = pick_c(pool, bw_tol=0.0)
                if c0_best is not None:
                    break

        # Balanced: normalized score within slice.
        fail_vals = [_clip(float(r.min_fail_step), 0.0, 1200.0) for r in pts]
        spread_vals = [float(r.rho_eff_n) for r in pts]
        meanp_vals = [float(r.peak_mean_p) for r in pts]
        fail_min, fail_max = min(fail_vals), max(fail_vals)
        spread_min, spread_max = min(spread_vals), max(spread_vals)
        meanp_min, meanp_max = min(meanp_vals), max(meanp_vals)

        def bal_score(r: Row) -> float:
            n_fail = _minmax_norm(_clip(float(r.min_fail_step), 0.0, 1200.0), fail_min, fail_max)
            n_spread = _minmax_norm(float(r.rho_eff_n), spread_min, spread_max)
            n_meanp = _minmax_norm(float(r.peak_mean_p), meanp_min, meanp_max)
            s = 0.0
            s += 0.45 * (n_fail if _isfinite(n_fail) else 0.0)
            s += 0.45 * (n_spread if _isfinite(n_spread) else 0.0)
            s -= 0.10 * (n_meanp if _isfinite(n_meanp) else 0.0)
            return s

        bal_best = None
        best_s = float("-inf")
        for r in pts:
            s = bal_score(r)
            if s > best_s + 1e-12:
                best_s = s
                bal_best = r

        def pack(prefix: str, r: Row | None) -> dict[str, Any]:
            if r is None:
                return {
                    f"{prefix}_damping": "",
                    f"{prefix}_minFailStep": "",
                    f"{prefix}_rhoEffN": "",
                    f"{prefix}_peakMeanP": "",
                    f"{prefix}_peakPMax": "",
                    f"{prefix}_bandwidth": "",
                }
            return {
                f"{prefix}_damping": float(r.damping),
                f"{prefix}_minFailStep": float(r.min_fail_step),
                f"{prefix}_rhoEffN": float(r.rho_eff_n),
                f"{prefix}_peakMeanP": float(r.peak_mean_p),
                f"{prefix}_peakPMax": float(r.peak_pmax),
                f"{prefix}_bandwidth": bw(r),
            }

        row: dict[str, Any] = {
            "scenario": scenario,
            "pulseEvery": int(pulse_every),
            "approxRate": float(rate_key),
        }
        row.update(pack("A", a_best))
        row.update(pack("B", b_best))
        row.update(pack("C", c_best))
        if include_pure_c:
            row.update(pack("C0", c0_best))
        row.update(pack("Bal", bal_best))
        out.append(row)

    return out


def _render_controller_setpoints_md(*, rows: list[dict[str, Any]], include_pure_c: bool = False) -> str:
    if not rows:
        return "(no setpoints computed)"

    header = (
        "| scenario | pulseEvery | approxRate | "
        "A:damp | A:fail | "
        "B:damp | B:rhoEffN | "
        "C:damp | C:bandwidth | "
        + ("C0:damp | C0:bandwidth | " if include_pure_c else "")
        + "Bal:damp |"
    )
    sep = (
        "|:--|---:|---:|---:|---:|---:|---:|---:|---:|"
        + ("---:|---:|" if include_pure_c else "")
        + "---:|"
    )
    lines = [header, sep]

    for r in rows:
        cols = [
            str(r.get("scenario") or ""),
            str(int(r.get("pulseEvery") or 0)),
            _fmt_num(_safe_float(r.get("approxRate")), 4),
            _fmt_num(_safe_float(r.get("A_damping")), 4),
            _fmt_int(_safe_float(r.get("A_minFailStep"))),
            _fmt_num(_safe_float(r.get("B_damping")), 4),
            _fmt_num(_safe_float(r.get("B_rhoEffN")), 2),
            _fmt_num(_safe_float(r.get("C_damping")), 4),
            _fmt_num(_safe_float(r.get("C_bandwidth")), 2),
        ]
        if include_pure_c:
            cols.extend(
                [
                    _fmt_num(_safe_float(r.get("C0_damping")), 4),
                    _fmt_num(_safe_float(r.get("C0_bandwidth")), 2),
                ]
            )
        cols.append(_fmt_num(_safe_float(r.get("Bal_damping")), 4))
        lines.append("| " + " | ".join(cols) + " |")

    return "\n".join(lines)


def _render_preset_block(
    *,
    name: str,
    rows: list[Row],
    budget: int,
    cap: float,
    top_n: int,
    w_spread: float,
    w_rate: float,
    w_meanp: float,
    w_pmax: float,
) -> str:
    peak_mean_p_cap = cap
    if peak_mean_p_cap <= 0:
        peak_mean_p_cap = float("inf")

    global_top, per_scenario = _decision_ready_recommendations(
        rows,
        budget=int(budget),
        peak_mean_p_cap=peak_mean_p_cap,
        top_n=int(top_n),
        per_scenario_top_k=1,
        w_spread=float(w_spread),
        w_rate=float(w_rate),
        w_mean_p=float(w_meanp),
        w_pmax=float(w_pmax),
    )

    global_top = _add_bandwidth(global_top, budget=int(budget))
    per_scenario = _add_bandwidth(per_scenario, budget=int(budget))

    lines: list[str] = []
    lines.append(f"### Preset: {name}")
    lines.append("")
    lines.append(
        f"Constraints: minFailStep ≥ {int(budget)}, "
        + ("peakMeanP cap: (none)" if not _isfinite(peak_mean_p_cap) else f"peakMeanP ≤ {peak_mean_p_cap:g}")
    )
    lines.append("")
    lines.append(
        "Weights: "
        f"wSpread={w_spread:g}, wRate={w_rate:g}, wMeanP={w_meanp:g}, wPMax={w_pmax:g}."
    )
    lines.append("")
    lines.append(_render_reco_md("Top picks (global)", global_top))
    lines.append("")
    lines.append(_render_reco_md("Top pick per scenario", per_scenario))
    return "\n".join(lines)


def _svg_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _svg_plot(
    rows: list[Row],
    *,
    x_value: Callable[[Row], float],
    x_label: str,
    y_value: Callable[[Row], float],
    y_label: str,
    title: str,
    out_path: Path,
    y_origin_zero: bool = True,
    series_key: Callable[[Row], str] | None = None,
) -> None:
    # Group into series (default: scenario).
    key_fn = series_key or (lambda r: r.scenario or "(unknown)")
    series: dict[str, list[tuple[float, float]]] = {}
    for r in rows:
        x = x_value(r)
        y = y_value(r)
        if not (_isfinite(x) and _isfinite(y)):
            continue
        series.setdefault(key_fn(r), []).append((x, float(y)))

    # Sort each series by x and dedup by x (keep the max y by default).
    for k in list(series.keys()):
        pts = sorted(series[k], key=lambda t: t[0])
        dedup: dict[float, float] = {}
        for x, y in pts:
            if x not in dedup or y > dedup[x]:
                dedup[x] = y
        series[k] = sorted(dedup.items(), key=lambda t: t[0])

    all_x = [x for pts in series.values() for (x, _) in pts]
    all_y = [y for pts in series.values() for (_, y) in pts]

    if not all_x or not all_y:
        out_path.write_text("", encoding="utf-8")
        return

    x_min, x_max = min(all_x), max(all_x)
    y_min = 0.0 if y_origin_zero else min(all_y)
    y_max = max(all_y)
    if y_max <= y_min:
        y_max = y_min + 1.0

    # Basic canvas.
    width, height = 960, 520
    margin_l, margin_r, margin_t, margin_b = 70, 20, 30, 60

    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b

    def x_to_px(x: float) -> float:
        if x_max <= x_min:
            return margin_l + plot_w / 2
        return margin_l + (x - x_min) * plot_w / (x_max - x_min)

    def y_to_px(y: float) -> float:
        if y_max <= y_min:
            return margin_t + plot_h / 2
        return margin_t + (y_max - y) * plot_h / (y_max - y_min)

    palette = [
        "#2563eb",  # blue
        "#16a34a",  # green
        "#dc2626",  # red
        "#7c3aed",  # purple
        "#0f766e",  # teal
        "#ea580c",  # orange
    ]

    scenarios = sorted(series.keys())
    color_map = {sc: palette[i % len(palette)] for i, sc in enumerate(scenarios)}

    def ticks(vmin: float, vmax: float, n: int) -> list[float]:
        if vmax <= vmin:
            return [vmin]
        step = (vmax - vmin) / n
        return [vmin + i * step for i in range(n + 1)]

    x_ticks = ticks(x_min, x_max, 5)
    y_ticks = ticks(y_min, y_max, 5)

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">' 
    )
    lines.append('<rect x="0" y="0" width="100%" height="100%" fill="white"/>')

    grid_color = "#e5e7eb"
    axis_color = "#111827"
    text_color = "#111827"

    for xv in x_ticks:
        xpx = x_to_px(xv)
        lines.append(
            f'<line x1="{xpx:.2f}" y1="{margin_t}" x2="{xpx:.2f}" y2="{margin_t+plot_h}" stroke="{grid_color}" stroke-width="1"/>'
        )
    for yv in y_ticks:
        ypx = y_to_px(yv)
        lines.append(
            f'<line x1="{margin_l}" y1="{ypx:.2f}" x2="{margin_l+plot_w}" y2="{ypx:.2f}" stroke="{grid_color}" stroke-width="1"/>'
        )

    lines.append(
        f'<line x1="{margin_l}" y1="{margin_t+plot_h}" x2="{margin_l+plot_w}" y2="{margin_t+plot_h}" stroke="{axis_color}" stroke-width="2"/>'
    )
    lines.append(
        f'<line x1="{margin_l}" y1="{margin_t}" x2="{margin_l}" y2="{margin_t+plot_h}" stroke="{axis_color}" stroke-width="2"/>'
    )

    for xv in x_ticks:
        xpx = x_to_px(xv)
        lines.append(
            f'<text x="{xpx:.2f}" y="{margin_t+plot_h+20}" font-size="12" text-anchor="middle" fill="{text_color}">{_svg_escape(_fmt_num(xv, 3))}</text>'
        )
    for yv in y_ticks:
        ypx = y_to_px(yv)
        # Use 0 decimals for larger y ranges; otherwise 2 decimals.
        y_label_text = _fmt_int(yv) if y_max >= 100 else _fmt_num(yv, 2)
        lines.append(
            f'<text x="{margin_l-10}" y="{ypx+4:.2f}" font-size="12" text-anchor="end" fill="{text_color}">{_svg_escape(y_label_text)}</text>'
        )

    lines.append(
        f'<text x="{margin_l + plot_w/2:.2f}" y="{height-20}" font-size="14" text-anchor="middle" fill="{text_color}">{_svg_escape(x_label)}</text>'
    )
    lines.append(
        f'<text x="18" y="{margin_t + plot_h/2:.2f}" font-size="14" text-anchor="middle" fill="{text_color}" transform="rotate(-90 18 {margin_t + plot_h/2:.2f})">{_svg_escape(y_label)}</text>'
    )
    lines.append(
        f'<text x="{margin_l}" y="{18}" font-size="16" text-anchor="start" fill="{text_color}">{_svg_escape(title)}</text>'
    )

    for sc in scenarios:
        pts = series[sc]
        if len(pts) < 1:
            continue
        color = color_map[sc]
        path_d = " ".join(
            ("M" if i == 0 else "L") + f" {x_to_px(x):.2f} {y_to_px(y):.2f}" for i, (x, y) in enumerate(pts)
        )
        lines.append(f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in pts:
            lines.append(
                f'<circle cx="{x_to_px(x):.2f}" cy="{y_to_px(y):.2f}" r="4" fill="{color}" stroke="white" stroke-width="1"/>'
            )

    legend_x = margin_l + plot_w - 160
    legend_y = margin_t + 10
    legend_w = 150
    legend_h = 22 + 18 * len(scenarios)
    lines.append(
        f'<rect x="{legend_x}" y="{legend_y}" width="{legend_w}" height="{legend_h}" fill="white" stroke="#d1d5db"/>'
    )
    lines.append(
        f'<text x="{legend_x+10}" y="{legend_y+16}" font-size="12" fill="{text_color}">scenario</text>'
    )
    for i, sc in enumerate(scenarios):
        y = legend_y + 22 + i * 18
        color = color_map[sc]
        lines.append(f'<line x1="{legend_x+10}" y1="{y}" x2="{legend_x+30}" y2="{y}" stroke="{color}" stroke-width="3"/>')
        lines.append(
            f'<text x="{legend_x+36}" y="{y+4}" font-size="12" fill="{text_color}">{_svg_escape(sc)}</text>'
        )

    lines.append("</svg>")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _default_out_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return root / "solData" / "testResults" / "cognitive_load_compare" / stamp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--batch-dirs",
        nargs="+",
        required=True,
        help="One or more cognitive_load_batches/<stamp> folders (each must contain cognitive_load_readout.csv).",
    )
    ap.add_argument(
        "--out-dir",
        default="",
        help="Output directory (default: solData/testResults/cognitive_load_compare/<utc-stamp>/).",
    )

    ap.add_argument(
        "--x-axis",
        default="approxInjectRate",
        choices=["approxInjectRate", "damping", "pulseEvery", "agentCount", "injectAmount"],
        help="X-axis for plots (use `damping` to visualize resonance/dissipation sweeps).",
    )

    ap.add_argument(
        "--series-by",
        default="scenario",
        choices=["scenario", "scenario+rate", "scenario+pulseEvery", "batch"],
        help=(
            "How to group lines in plots. "
            "Use scenario+rate or scenario+pulseEvery when overlaying multiple batches at different loads."
        ),
    )

    ap.add_argument(
        "--c-bandwidth-tol",
        type=float,
        default=0.02,
        help=(
            "Controller setpoints: Objective C bandwidth tie tolerance as a fraction of best bandwidth within slice. "
            "Rows within (1 - tol) * best bandwidth are treated as equivalent, then we prefer lower peakPMax/peakMeanP. "
            "Default 0.02 (2%)."
        ),
    )

    ap.add_argument(
        "--include-pure-c",
        action="store_true",
        help=(
            "Controller setpoints: include an additional C0 column that picks C with bandwidth-at-all-cost (tol=0.0), "
            "so you can compare spike-aware C vs pure bandwidth C in the same report."
        ),
    )

    # Decision-ready shortlist knobs.
    ap.add_argument("--reco-budget", type=int, default=1200, help="Minimum minFailStep for recommendations.")
    ap.add_argument(
        "--reco-peak-meanp-cap",
        type=float,
        default=2.5,
        help="Maximum peakMeanP allowed for recommendations (set <=0 to disable).",
    )
    ap.add_argument("--reco-top-n", type=int, default=8, help="Global top-N recommendations.")
    ap.add_argument("--reco-per-scenario-k", type=int, default=2, help="Top-K recommendations per scenario.")
    ap.add_argument("--w-spread", type=float, default=0.55, help="Weight for spread (rhoEffN).")
    ap.add_argument("--w-rate", type=float, default=0.35, help="Weight for load (approxInjectRate).")
    ap.add_argument("--w-meanp", type=float, default=0.10, help="Penalty weight for sustained stress (peakMeanP).")
    ap.add_argument("--w-pmax", type=float, default=0.00, help="Penalty weight for spike stress (peakPMax).")

    args = ap.parse_args()

    x_axis = str(args.x_axis)

    def x_value(r: Row) -> float:
        if x_axis == "damping":
            return float(r.damping) if _isfinite(r.damping) else float("nan")
        if x_axis == "pulseEvery":
            return float(r.pulse_every) if r.pulse_every else float("nan")
        if x_axis == "agentCount":
            return float(r.agent_count) if r.agent_count else float("nan")
        if x_axis == "injectAmount":
            return float(r.inject_amount) if _isfinite(r.inject_amount) else float("nan")
        # default: approxInjectRate
        return float(r.approx_inject_rate) if _isfinite(r.approx_inject_rate) else float("nan")

    x_label = x_axis

    series_by = str(args.series_by)

    def series_key(r: Row) -> str:
        sc = r.scenario or "(unknown)"
        if series_by == "batch":
            return f"{sc} [{Path(r.batch_dir).name}]"
        if series_by == "scenario+rate":
            return f"{sc} @rate={_fmt_num(r.approx_inject_rate, 4)}"
        if series_by == "scenario+pulseEvery":
            return f"{sc} @every={r.pulse_every}"
        return sc

    out_dir = Path(args.out_dir).resolve() if args.out_dir else _default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[Row] = []
    for bd in args.batch_dirs:
        batch_dir = Path(bd).resolve()
        readout_csv = batch_dir / "cognitive_load_readout.csv"
        if not readout_csv.exists():
            raise SystemExit(f"Missing: {readout_csv}")

        raw = _load_csv(readout_csv)
        for r in raw:
            all_rows.append(_read_row(r, batch_dir=batch_dir))

    # Sort: scenario, then chosen x-axis asc, then approxInjectRate, then pulseEvery.
    all_rows.sort(
        key=lambda r: (
            r.scenario,
            float("inf") if not _isfinite(x_value(r)) else float(x_value(r)),
            float("inf") if not _isfinite(r.approx_inject_rate) else float(r.approx_inject_rate),
            r.pulse_every,
        )
    )

    out_csv = out_dir / "cognitive_load_compare.csv"
    _write_csv(out_csv, all_rows)

    out_svg_fail = out_dir / "cognitive_load_compare_minFailStep.svg"
    _svg_plot(
        all_rows,
        x_value=x_value,
        x_label=x_label,
        y_value=lambda r: float(r.min_fail_step),
        y_label="minFailStep",
        title="Cognitive load comparison: time-to-failure",
        out_path=out_svg_fail,
        y_origin_zero=True,
        series_key=series_key,
    )

    out_svg_pmax = out_dir / "cognitive_load_compare_peakPMax.svg"
    _svg_plot(
        all_rows,
        x_value=x_value,
        x_label=x_label,
        y_value=lambda r: float(r.peak_pmax),
        y_label="peakPMax",
        title="Cognitive load comparison: peak pressure spikes",
        out_path=out_svg_pmax,
        y_origin_zero=True,
        series_key=series_key,
    )

    out_svg_meanp = out_dir / "cognitive_load_compare_peakMeanP.svg"
    _svg_plot(
        all_rows,
        x_value=x_value,
        x_label=x_label,
        y_value=lambda r: float(r.peak_mean_p),
        y_label="peakMeanP",
        title="Cognitive load comparison: peak mean pressure",
        out_path=out_svg_meanp,
        y_origin_zero=True,
        series_key=series_key,
    )

    out_svg_effn = out_dir / "cognitive_load_compare_rhoEffN.svg"
    _svg_plot(
        all_rows,
        x_value=x_value,
        x_label=x_label,
        y_value=lambda r: float(r.rho_eff_n),
        y_label="rhoEffN (effective active nodes)",
        title="Cognitive load comparison: spread (rhoEffN)",
        out_path=out_svg_effn,
        y_origin_zero=False,
        series_key=series_key,
    )

    out_svg_rhosum = out_dir / "cognitive_load_compare_peakRhoSum.svg"
    _svg_plot(
        all_rows,
        x_value=x_value,
        x_label=x_label,
        y_value=lambda r: float(r.peak_rho_sum),
        y_label="peakRhoSum",
        title="Cognitive load comparison: total activation mass (peakRhoSum)",
        out_path=out_svg_rhosum,
        y_origin_zero=True,
        series_key=series_key,
    )

    # Markdown
    out_md = out_dir / "cognitive_load_compare.md"
    md_lines: list[str] = []
    md_lines.append("# Cognitive Load Comparison")
    md_lines.append("")
    md_lines.append(f"Batches compared: {len(args.batch_dirs)}")
    md_lines.append("")
    md_lines.append(f"## Plot: time-to-failure vs {x_label}")
    md_lines.append("")
    md_lines.append(f"![minFailStep vs {x_label}](cognitive_load_compare_minFailStep.svg)")
    md_lines.append("")
    md_lines.append(f"## Plot: peak pressure spikes vs {x_label}")
    md_lines.append("")
    md_lines.append(f"![peakPMax vs {x_label}](cognitive_load_compare_peakPMax.svg)")
    md_lines.append("")
    md_lines.append(f"## Plot: peak mean pressure vs {x_label}")
    md_lines.append("")
    md_lines.append(f"![peakMeanP vs {x_label}](cognitive_load_compare_peakMeanP.svg)")
    md_lines.append("")
    md_lines.append(f"## Plot: spread (rhoEffN) vs {x_label}")
    md_lines.append("")
    md_lines.append(f"![rhoEffN vs {x_label}](cognitive_load_compare_rhoEffN.svg)")
    md_lines.append("")
    md_lines.append(f"## Plot: total activation mass (peakRhoSum) vs {x_label}")
    md_lines.append("")
    md_lines.append(f"![peakRhoSum vs {x_label}](cognitive_load_compare_peakRhoSum.svg)")
    md_lines.append("")
    md_lines.append("## Combined table")
    md_lines.append("")
    md_lines.append(_render_md_table(all_rows))

    md_lines.append("")
    md_lines.append("## Capacity (compute-window signature)")
    md_lines.append("")
    md_lines.append(
        "This table is a practical 'compute substrate' signature: for a required runtime budget (steps), it reports the *maximum* load you can push (approxInjectRate) before the system fails sooner than that budget."
    )
    md_lines.append("")
    md_lines.append(_render_capacity_table(all_rows, step_budgets=[1400, 1200, 1000, 800]))

    md_lines.append("")
    md_lines.append("## Operating points (Pareto-ish)")
    md_lines.append("")
    md_lines.append(
        "This section helps pick substrate tuning targets: maximize *spread* (rhoEffN) while meeting a compute-window budget (minFailStep) and, optionally, a sustained-stress limit (peakMeanP)."
    )
    md_lines.append("")
    md_lines.append(
        _render_operating_point_table(
            all_rows,
            step_budgets=[1400, 1200, 1000, 800],
            peak_mean_p_caps=[float("inf"), 2.5, 1.5],
        )
    )

    md_lines.append("")
    md_lines.append("### Frontier (budget ≥1200, peakMeanP ≤2.5)")
    md_lines.append("")
    md_lines.append(
        "Non-dominated points in (approxInjectRate, rhoEffN) under the constraint above. These are the candidates where you can't increase load without losing spread (or vice versa)."
    )
    md_lines.append("")
    md_lines.append(_render_frontier_table(all_rows, budget=1200, cap=2.5))

    md_lines.append("")
    md_lines.append("## Controller setpoints (damping per load)")
    md_lines.append("")
    md_lines.append(
        "Recommended damping values for each load slice (grouped by pulseEvery / approxRate). "
        "These are intended as concrete controller knobs for A/B/C: runtime (A), spread (B), and sustained bandwidth (C)."
    )
    md_lines.append("")
    setpoints = _pick_controller_setpoints(
        rows=all_rows,
        c_bandwidth_tol=float(args.c_bandwidth_tol),
        include_pure_c=bool(args.include_pure_c),
    )
    md_lines.append(_render_controller_setpoints_md(rows=setpoints, include_pure_c=bool(args.include_pure_c)))

    md_lines.append("")
    md_lines.append("## Recommendations (decision-ready shortlist)")
    md_lines.append("")

    peak_mean_p_cap = float(args.reco_peak_meanp_cap)
    if peak_mean_p_cap <= 0:
        peak_mean_p_cap = float("inf")

    md_lines.append(
        "This is a multi-objective shortlist tool. It supports different recommendation presets depending on what you want to optimize:"
    )
    md_lines.append("")
    md_lines.append("- Runtime (A): prefer long stable compute windows")
    md_lines.append("- Spread (B): prefer higher rhoEffN (parallel semantic bandwidth)")
    md_lines.append("- Throughput (C): prefer higher approxInjectRate (write bandwidth)")
    md_lines.append("- Balanced: compromise among A/B/C")
    md_lines.append("")
    md_lines.append(
        "The `bandwidth` column is a simple sustained-bandwidth proxy: approxInjectRate × min(minFailStep, budget)."
    )
    md_lines.append("")

    # Preserve the user-configurable single run as a named preset, then add additional fixed presets.
    md_lines.append(
        _render_preset_block(
            name="Custom (CLI args)",
            rows=all_rows,
            budget=int(args.reco_budget),
            cap=float(args.reco_peak_meanp_cap),
            top_n=int(args.reco_top_n),
            w_spread=float(args.w_spread),
            w_rate=float(args.w_rate),
            w_meanp=float(args.w_meanp),
            w_pmax=float(args.w_pmax),
        )
    )
    md_lines.append("")
    md_lines.append(
        _render_preset_block(
            name="Runtime-first (A)",
            rows=all_rows,
            budget=1400,
            cap=1.5,
            top_n=6,
            w_spread=0.45,
            w_rate=0.15,
            w_meanp=0.40,
            w_pmax=0.00,
        )
    )
    md_lines.append("")
    md_lines.append(
        _render_preset_block(
            name="Spread-first (B)",
            rows=all_rows,
            budget=1200,
            cap=2.5,
            top_n=6,
            w_spread=0.75,
            w_rate=0.15,
            w_meanp=0.10,
            w_pmax=0.00,
        )
    )
    md_lines.append("")
    md_lines.append(
        _render_preset_block(
            name="Throughput-first (C)",
            rows=all_rows,
            budget=1200,
            cap=2.5,
            top_n=6,
            w_spread=0.25,
            w_rate=0.65,
            w_meanp=0.10,
            w_pmax=0.05,
        )
    )
    md_lines.append("")
    md_lines.append(
        _render_preset_block(
            name="Balanced (A/B/C)",
            rows=all_rows,
            budget=1200,
            cap=2.0,
            top_n=6,
            w_spread=0.55,
            w_rate=0.35,
            w_meanp=0.10,
            w_pmax=0.00,
        )
    )
    md_lines.append("")
    md_lines.append("## Sources")
    md_lines.append("")
    for bd in args.batch_dirs:
        md_lines.append(f"- {Path(bd).resolve()}")

    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_md}")
    print(f"Wrote: {out_svg_fail}")
    print(f"Wrote: {out_svg_pmax}")
    print(f"Wrote: {out_svg_meanp}")
    print(f"Wrote: {out_svg_effn}")
    print(f"Wrote: {out_svg_rhosum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
