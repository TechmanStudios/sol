"""Adaptive cognitive-load exploration loop.

Goal
----
Run an iterative sequence of small damping sweeps, using the previous
iteration's results to propose the next test. This is designed to support
"probe cognitive-load space" workflows where we want to:
- bracket a runtime budget boundary (e.g. minFailStep ~ 1200)
- surface regime transitions as damping changes
- optionally compare spike-aware C vs pure-throughput C0 controller setpoints

This script is intentionally dependency-free (stdlib only) and composes the
existing dashboard automation tools:
- run_dashboard_sweep.py (executes command_queue via Firefox/Selenium)
- analyze_cognitive_load_sweep.py (produces cognitive_load_readout.csv)
- analyze_cognitive_load_compare.py (optional, produces a compare MD with C/C0)

Typical usage
-------------
From sol/:

  python tools/dashboard_automation/adaptive_cognitive_load_loop.py \
    --iterations 10 \
    --pulse-every 4 \
    --damping-low 1.0 --damping-high 2.2 \
    --points 7 \
    --budget 1200 \
    --include-compare

Notes
-----
- Each iteration produces its own batch folder under:
  solData/testResults/adaptive_cognitive_load/<stamp>/iter_XX/
- You can stop/restart; results are written as the run progresses.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _read_csv_with_header(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        return header, list(reader)


def _write_csv_with_header(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def _safe_float(v: Any) -> float:
    try:
        if v is None:
            return float("nan")
        s = str(v).strip()
        if not s:
            return float("nan")
        return float(s)
    except Exception:
        return float("nan")


def _isfinite(x: float) -> bool:
    return math.isfinite(float(x))


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _parse_branch_from_stem(stem: str) -> str:
    # Expected: iter_XX_bN_YY_damp...
    # If absent, bucket as b0.
    parts = (stem or "").split("_")
    for p in parts:
        if p.startswith("b") and p[1:].isdigit():
            return p
    return "b0"


def _parse_int_list(s: str) -> list[int]:
    s = (s or "").strip()
    if not s:
        return []
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


@dataclass(frozen=True)
class IterationResult:
    iter_index: int
    batch_dir: Path
    readout_csv: Path
    points: list[dict[str, Any]]


def _linspace(low: float, high: float, n: int) -> list[float]:
    if n <= 1:
        return [float(low)]
    low = float(low)
    high = float(high)
    step = (high - low) / float(n - 1)
    return [low + i * step for i in range(n)]


def _make_command(
    *,
    dashboard: str,
    out_prefix: str,
    params: dict[str, Any],
    meta: dict[str, Any],
    runs: int,
    timeout_s: float,
) -> dict[str, Any]:
    return {
        "kind": "sol.dashboard.sweep.v1",
        "dashboard": dashboard,
        "outPrefix": out_prefix,
        "runs": int(runs),
        "timeoutS": float(timeout_s),
        "params": params,
        "meta": meta,
    }


def _run_py(script: Path, args: list[str]) -> None:
    cmd = [sys.executable, str(script)] + args
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def _load_readout_points(readout_csv: Path) -> list[dict[str, Any]]:
    rows = _read_csv_dicts(readout_csv)
    out: list[dict[str, Any]] = []
    for r in rows:
        stem = r.get("stem") or ""
        out.append(
            {
                "stem": stem,
                "branch": _parse_branch_from_stem(stem),
                "scenario": r.get("scenario") or "",
                "pulseEvery": int(float(r.get("pulseEvery") or 0) or 0),
                "approxRate": _safe_float(r.get("approxInjectRate")),
                "damping": _safe_float(r.get("damping")),
                "minFailStep": _safe_float(r.get("minFailStep")),
                "peakMeanP": _safe_float(r.get("peakMeanP_max")),
                "peakPMax": _safe_float(r.get("peakPMax_max")),
                "rhoEffN": _safe_float(r.get("peakRhoEffN")),
                "ok": (str(r.get("ok") or "").lower() == "true"),
            }
        )
    out = [
        p
        for p in out
        if bool(p.get("ok"))
        and _isfinite(_safe_float(p.get("damping")))
        and _isfinite(_safe_float(p.get("minFailStep")))
    ]
    out.sort(key=lambda p: float(p["damping"]))
    return out


def _pick_next_damping_window(*, points: list[dict[str, Any]], budget: int) -> tuple[float, float, str]:
    """Pick next damping window by bracketing the steepest transition.

    Heuristic:
    - Prefer an adjacent pair where minFailStep crosses the budget.
    - Otherwise, pick the adjacent pair with max |ΔminFailStep|.

    Returns: (low, high, reason)
    """

    if len(points) < 2:
        d = float(points[0]["damping"]) if points else 1.0
        return (max(0.01, d * 0.8), d * 1.2, "insufficient points; expanded around single")

    budget = int(budget)

    best_pair: tuple[int, int] | None = None
    best_score = float("-inf")
    best_reason = ""

    for i in range(len(points) - 1):
        a = points[i]
        b = points[i + 1]
        fa = float(a["minFailStep"])
        fb = float(b["minFailStep"])
        da = float(a["damping"]) 
        db = float(b["damping"]) 

        crosses = (fa - budget) * (fb - budget) <= 0
        delta = abs(fb - fa)

        score = delta
        reason = f"max ΔminFailStep={delta:.1f}"
        if crosses:
            score = 1e9 + delta
            reason = f"crosses budget {budget} (Δ={delta:.1f})"

        if score > best_score:
            best_score = score
            best_pair = (i, i + 1)
            best_reason = reason

    assert best_pair is not None
    i, j = best_pair
    low = float(points[i]["damping"])
    high = float(points[j]["damping"])

    # Expand slightly around the bracket to avoid missing the ridge.
    pad = 0.20 * (high - low)
    low2 = max(0.01, low - pad)
    high2 = high + pad
    return (low2, high2, best_reason)


def _pick_next_damping_window_multi(
    *,
    points: list[dict[str, Any]],
    budget: int,
    w_fail: float,
    w_spike: float,
    w_meanp: float,
    w_rho: float,
    prefer_budget_cross: bool,
) -> tuple[float, float, str]:
    """Pick next damping window using a multi-objective adjacent-pair score.

    Score uses adjacent pair deltas; if prefer_budget_cross is True, any pair
    that crosses the budget is prioritized.
    """

    if len(points) < 2:
        d = float(points[0]["damping"]) if points else 1.0
        return (max(0.01, d * 0.8), d * 1.2, "insufficient points; expanded around single")

    budget = int(budget)

    best_pair: tuple[int, int] | None = None
    best_score = float("-inf")
    best_reason = ""
    best_cross = False

    for i in range(len(points) - 1):
        a = points[i]
        b = points[i + 1]

        fa = float(a.get("minFailStep", float("nan")))
        fb = float(b.get("minFailStep", float("nan")))
        if not (_isfinite(fa) and _isfinite(fb)):
            continue

        crosses = (fa - budget) * (fb - budget) <= 0
        d_fail = abs(fb - fa)

        pa = float(a.get("peakPMax", float("nan")))
        pb = float(b.get("peakPMax", float("nan")))
        d_spike = abs(pb - pa) if (_isfinite(pa) and _isfinite(pb)) else 0.0

        ma = float(a.get("peakMeanP", float("nan")))
        mb = float(b.get("peakMeanP", float("nan")))
        d_meanp = abs(mb - ma) if (_isfinite(ma) and _isfinite(mb)) else 0.0

        ra = float(a.get("rhoEffN", float("nan")))
        rb = float(b.get("rhoEffN", float("nan")))
        d_rho = abs(rb - ra) if (_isfinite(ra) and _isfinite(rb)) else 0.0

        score = (w_fail * d_fail) + (w_spike * d_spike) + (w_meanp * d_meanp) + (w_rho * d_rho)

        if prefer_budget_cross:
            # Prefer any crossing pair over any non-crossing pair.
            if crosses and not best_cross:
                best_pair = (i, i + 1)
                best_score = score
                best_cross = True
                best_reason = f"crosses budget {budget}; score={score:.3g} (Δfail={d_fail:.1f}, Δspike={d_spike:.2f}, ΔmeanP={d_meanp:.3f}, ΔrhoEffN={d_rho:.2f})"
                continue
            if best_cross and not crosses:
                continue

        if score > best_score:
            best_pair = (i, i + 1)
            best_score = score
            best_cross = crosses
            cross_txt = "crosses" if crosses else "no-cross"
            best_reason = f"{cross_txt}; score={score:.3g} (Δfail={d_fail:.1f}, Δspike={d_spike:.2f}, ΔmeanP={d_meanp:.3f}, ΔrhoEffN={d_rho:.2f})"

    if best_pair is None:
        d = float(points[len(points) // 2]["damping"])
        return (max(0.01, d * 0.8), d * 1.2, "no scorable pairs; expanded around midpoint")

    i, j = best_pair
    low = float(points[i]["damping"])
    high = float(points[j]["damping"])
    if high < low:
        low, high = high, low

    pad = 0.20 * (high - low)
    low2 = max(0.01, low - pad)
    high2 = high + pad
    return (low2, high2, best_reason)


def _widen_window(low: float, high: float, factor: float, *, min_low: float = 0.01) -> tuple[float, float]:
    low = float(low)
    high = float(high)
    if high < low:
        low, high = high, low
    mid = 0.5 * (low + high)
    half = 0.5 * (high - low)
    half2 = max(half * float(factor), 1e-6)
    return (max(min_low, mid - half2), mid + half2)


def _adjust_pulse_every(*, points: list[dict[str, Any]], budget: int, pulse_every: int) -> tuple[int, str]:
    """Adjust load if we're far from the budget boundary.

    - If all minFailStep >> budget: increase load by decreasing pulseEvery.
    - If all minFailStep << budget: decrease load by increasing pulseEvery.
    """

    if not points:
        return pulse_every, "no points"

    fails = [float(p["minFailStep"]) for p in points if _isfinite(float(p["minFailStep"]))]
    if not fails:
        return pulse_every, "no finite fail steps"

    mn = min(fails)
    mx = max(fails)
    budget_f = float(budget)

    # Simple deadband; only adjust if clearly above/below.
    if mn > budget_f + 150:
        new_pe = max(1, int(pulse_every) - 1)
        if new_pe != pulse_every:
            return new_pe, f"all above budget (min={mn:.0f}); increasing load (pulseEvery {pulse_every}->{new_pe})"

    if mx < budget_f - 150:
        new_pe = int(pulse_every) + 1
        return new_pe, f"all below budget (max={mx:.0f}); decreasing load (pulseEvery {pulse_every}->{new_pe})"

    return pulse_every, "kept pulseEvery"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--budget", type=int, default=1200)
    ap.add_argument("--points", type=int, default=7)

    # Base experiment params (keep aligned with earlier cognitive-load runs).
    ap.add_argument("--dashboard", default="sol_dashboard_v3_7_2.html")
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--dt", type=float, default=0.12)
    ap.add_argument("--press-slider", type=float, default=200.0)
    ap.add_argument("--mode", default="multiAgentTrain")
    ap.add_argument("--scenario", default="distributed", choices=["distributed", "concentrated", "roaming", "burstAll"])
    ap.add_argument("--agent-target-ids", default="64,82,79,12,13,14")
    ap.add_argument("--probe-ids", default="64,82,79")
    ap.add_argument("--agent-count", type=int, default=6)
    ap.add_argument("--targets-per-pulse", type=int, default=3)
    ap.add_argument("--pulse-step", type=int, default=100)
    ap.add_argument("--pulse-every", type=int, default=4)
    ap.add_argument("--target-id", type=int, default=64)

    # Initial search window.
    ap.add_argument("--damping-low", type=float, default=1.0)
    ap.add_argument("--damping-high", type=float, default=2.5)

    # Controller compare
    ap.add_argument("--include-compare", action="store_true")
    ap.add_argument("--c-bandwidth-tol", type=float, default=0.02)
    ap.add_argument("--include-pure-c", action="store_true")

    # Exploration policy
    ap.add_argument("--branches", type=int, default=3, help="How many parallel damping windows to track.")
    ap.add_argument(
        "--branch-modes",
        default="budget,spike,spread",
        help="Comma-separated branch strategies (budget, spike, spread). Truncated/padded to --branches.",
    )
    ap.add_argument("--min-window", type=float, default=0.05, help="Minimum damping window width before widening.")
    ap.add_argument("--widen-every", type=int, default=3, help="Every N iterations, force an exploration widening step.")
    ap.add_argument("--widen-factor", type=float, default=2.0, help="Multiply window width by this factor on widen.")
    ap.add_argument("--w_fail", type=float, default=1.0)
    ap.add_argument("--w_spike", type=float, default=2.0)
    ap.add_argument("--w_meanp", type=float, default=1.0)
    ap.add_argument("--w_rho", type=float, default=1.0)

    args = ap.parse_args()

    sol_root = Path(__file__).resolve().parents[2]
    tools_dir = sol_root / "tools" / "dashboard_automation"
    run_script = tools_dir / "run_dashboard_sweep.py"
    analyze_script = tools_dir / "analyze_cognitive_load_sweep.py"
    compare_script = tools_dir / "analyze_cognitive_load_compare.py"

    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
    out_root = sol_root / "solData" / "testResults" / "adaptive_cognitive_load" / stamp
    if out_root.exists():
        for i in range(1, 100):
            candidate = sol_root / "solData" / "testResults" / "adaptive_cognitive_load" / f"{stamp}_{i:02d}"
            if not candidate.exists():
                out_root = candidate
                break
    out_root.mkdir(parents=True, exist_ok=True)

    pulse_every = int(args.pulse_every)
    damp_low = float(args.damping_low)
    damp_high = float(args.damping_high)

    branch_modes_raw = [p.strip() for p in str(args.branch_modes).split(",") if p.strip()]
    if not branch_modes_raw:
        branch_modes_raw = ["budget"]
    branch_modes: list[str] = []
    for i in range(int(args.branches)):
        branch_modes.append(branch_modes_raw[i] if i < len(branch_modes_raw) else branch_modes_raw[-1])

    # Per-branch state (damping windows). All branches share pulseEvery for now.
    branch_windows: dict[str, tuple[float, float]] = {f"b{i}": (damp_low, damp_high) for i in range(int(args.branches))}

    journal: list[dict[str, Any]] = []

    for it in range(int(args.iterations)):
        iter_name = f"iter_{it+1:02d}"
        batch_dir = out_root / iter_name
        queue = batch_dir / "command_queue"
        done = batch_dir / "command_done"
        results = batch_dir / "command_results"
        queue.mkdir(parents=True, exist_ok=True)
        done.mkdir(parents=True, exist_ok=True)
        results.mkdir(parents=True, exist_ok=True)

        # Build per-branch grids.
        branch_grids: dict[str, list[float]] = {}
        for bi in range(int(args.branches)):
            b = f"b{bi}"
            lo, hi = branch_windows[b]
            if abs(hi - lo) < float(args.min_window):
                lo, hi = _widen_window(lo, hi, float(args.widen_factor))
            branch_grids[b] = _linspace(lo, hi, int(args.points))

        scenario = str(args.scenario)
        agent_targets_all = _parse_int_list(str(args.agent_target_ids))
        if scenario != "concentrated" and not agent_targets_all:
            raise SystemExit("--agent-target-ids must contain at least one id")
        if scenario == "concentrated":
            agent_targets_all = [int(args.target_id)]

        base_agent_count = int(args.agent_count)
        if scenario == "concentrated":
            base_agent_count = 1
        if base_agent_count < 1:
            raise SystemExit("--agent-count must be >= 1")
        if base_agent_count > len(agent_targets_all):
            raise SystemExit(
                f"--agent-count={base_agent_count} exceeds --agent-target-ids length ({len(agent_targets_all)})."
            )

        base_targets_per_pulse = int(args.targets_per_pulse)
        if base_targets_per_pulse < 1:
            raise SystemExit("--targets-per-pulse must be >= 1")

        probe_ids = _parse_int_list(str(args.probe_ids))
        inject_amount = 1.0

        # Write command files (all branches in one Firefox session).
        for bi in range(int(args.branches)):
            b = f"b{bi}"
            dampings = branch_grids[b]

            agent_count = min(base_agent_count, len(agent_targets_all))
            agent_targets = agent_targets_all[:agent_count]

            if scenario == "concentrated":
                agent_targets = [int(args.target_id)]
                agent_count = 1
                targets_per_pulse = 1
            elif scenario == "roaming":
                targets_per_pulse = 1
            elif scenario == "burstAll":
                targets_per_pulse = agent_count
            else:
                targets_per_pulse = min(base_targets_per_pulse, agent_count)

            approx_rate = float(inject_amount) * float(targets_per_pulse) / float(max(1, int(pulse_every)))

            for i, d in enumerate(dampings, start=1):
                stem = f"{iter_name}_{b}_{i:02d}_damp{d:.6g}".replace(".", "p")
                out_prefix = f"adapCog_{iter_name}_{b}_damp{d:.6g}".replace(".", "p")

                cmd = _make_command(
                    dashboard=str(args.dashboard),
                    out_prefix=out_prefix,
                    runs=1,
                    timeout_s=900.0,
                    params={
                        "steps": int(args.steps),
                        "dts": [float(args.dt)],
                        "dampings": [float(d)],
                        "modes": [str(args.mode)],
                        "pressSliderVal": float(args.press_slider),
                        "injectAmount": float(inject_amount),
                        "targetId": int(args.target_id),
                        "targetIds": agent_targets,
                        "targetsPerPulse": int(targets_per_pulse),
                        "pulseStep": int(args.pulse_step),
                        "pulseEvery": int(pulse_every),
                        "pulseCount": 0,
                        "probeIds": probe_ids,
                        "traceEvery": 50,
                        "progressEvery": 250,
                        "adaptiveTrace": True,
                        "guardrail": {"type": "none"},
                    },
                    meta={
                        # IMPORTANT: analyze_cognitive_load_sweep.py filters on phase==COGLOAD.
                        "phase": "COGLOAD",
                        "kind": "adaptive.cognitiveLoad.iter",
                        "iter": it + 1,
                        "branch": b,
                        "branchMode": branch_modes[bi] if bi < len(branch_modes) else "",
                        "knob": "damping",
                        "scenario": scenario,
                        "injectAmount": float(inject_amount),
                        "agentCount": int(agent_count),
                        "targetsPerPulse": int(targets_per_pulse),
                        "pulseEvery": int(pulse_every),
                        "dt": float(args.dt),
                        "damping": float(d),
                        "steps": int(args.steps),
                        "pressSliderVal": float(args.press_slider),
                        "approxInjectRate": approx_rate,
                        "budget": int(args.budget),
                    },
                )
                _write_json(queue / f"{stem}.json", cmd)

        # Run this iteration batch.
        _run_py(
            run_script,
            [
                "--firefox-dev",
                "--headless",
                "--run-command-dir",
                str(queue),
                "--command-done-dir",
                str(done),
                "--command-results-dir",
                str(results),
            ],
        )

        # Analyze.
        _run_py(analyze_script, ["--batch-dir", str(batch_dir)])
        readout_csv = batch_dir / "cognitive_load_readout.csv"
        points_all = _load_readout_points(readout_csv)

        # Split analyzed readout by branch into synthetic sub-batches for per-branch compare.
        header, rows_all = _read_csv_with_header(readout_csv)
        rows_by_branch: dict[str, list[dict[str, Any]]] = {}
        for r in rows_all:
            stem = str(r.get("stem") or "")
            b = _parse_branch_from_stem(stem)
            rows_by_branch.setdefault(b, []).append(r)

        branch_dirs: dict[str, Path] = {}
        for b, rows_b in rows_by_branch.items():
            bdir = batch_dir / b
            branch_dirs[b] = bdir
            _write_csv_with_header(bdir / "cognitive_load_readout.csv", header, rows_b)

        # Optional compare (for C vs C0 table).
        compare_md_by_branch: dict[str, str] = {}
        if bool(args.include_compare):
            for b, bdir in sorted(branch_dirs.items()):
                compare_out = bdir / "compare"
                compare_out.mkdir(parents=True, exist_ok=True)
                _run_py(
                    compare_script,
                    [
                        "--batch-dirs",
                        str(bdir),
                        "--out-dir",
                        str(compare_out),
                        "--x-axis",
                        "damping",
                        "--series-by",
                        "scenario+rate",
                        "--c-bandwidth-tol",
                        str(float(args.c_bandwidth_tol)),
                    ]
                    + (["--include-pure-c"] if bool(args.include_pure_c) else []),
                )
                compare_md_by_branch[b] = str((compare_out / "cognitive_load_compare.md").resolve())

        # Decide next test.
        next_pulse_every, pe_reason = _adjust_pulse_every(
            points=points_all, budget=int(args.budget), pulse_every=pulse_every
        )

        # Branch decisions.
        next_branch_windows: dict[str, tuple[float, float]] = {}
        branch_reasons: dict[str, str] = {}
        for bi in range(int(args.branches)):
            b = f"b{bi}"
            mode = branch_modes[bi] if bi < len(branch_modes) else "budget"
            pts = [p for p in points_all if str(p.get("branch")) == b]
            if mode == "budget":
                lo, hi, why = _pick_next_damping_window_multi(
                    points=pts,
                    budget=int(args.budget),
                    w_fail=float(args.w_fail),
                    w_spike=float(args.w_spike),
                    w_meanp=float(args.w_meanp),
                    w_rho=float(args.w_rho),
                    prefer_budget_cross=True,
                )
                next_branch_windows[b] = (lo, hi)
                branch_reasons[b] = f"budget: {why}"
            elif mode == "spike":
                lo, hi, why = _pick_next_damping_window_multi(
                    points=pts,
                    budget=int(args.budget),
                    w_fail=0.25 * float(args.w_fail),
                    w_spike=2.0 * float(args.w_spike),
                    w_meanp=float(args.w_meanp),
                    w_rho=0.5 * float(args.w_rho),
                    prefer_budget_cross=False,
                )
                next_branch_windows[b] = (lo, hi)
                branch_reasons[b] = f"spike: {why}"
            elif mode == "spread":
                lo, hi, why = _pick_next_damping_window_multi(
                    points=pts,
                    budget=int(args.budget),
                    w_fail=0.5 * float(args.w_fail),
                    w_spike=0.5 * float(args.w_spike),
                    w_meanp=float(args.w_meanp),
                    w_rho=2.0 * float(args.w_rho),
                    prefer_budget_cross=False,
                )
                next_branch_windows[b] = (lo, hi)
                branch_reasons[b] = f"spread: {why}"
            else:
                lo, hi, why = _pick_next_damping_window(points=pts, budget=int(args.budget))
                next_branch_windows[b] = (lo, hi)
                branch_reasons[b] = f"{mode}: {why}"

        # Occasional widening step: widen the last (most exploratory) branch.
        if int(args.widen_every) > 0 and ((it + 1) % int(args.widen_every) == 0):
            b = f"b{max(0, int(args.branches) - 1)}"
            lo, hi = next_branch_windows.get(b, branch_windows.get(b, (damp_low, damp_high)))
            lo2, hi2 = _widen_window(lo, hi, float(args.widen_factor))
            next_branch_windows[b] = (lo2, hi2)
            branch_reasons[b] = (branch_reasons.get(b, "") + f"; widen x{float(args.widen_factor):g}").strip("; ")

        journal.append(
            {
                "iter": it + 1,
                "batchDir": str(batch_dir),
                "pulseEvery": pulse_every,
                "branchModes": {f"b{i}": branch_modes[i] for i in range(int(args.branches))},
                "branchWindows": {b: {"low": float(branch_windows[b][0]), "high": float(branch_windows[b][1])} for b in branch_windows},
                "points": int(args.points),
                "nextPulseEvery": next_pulse_every,
                "reasonPulseEvery": pe_reason,
                "nextBranchWindows": {b: {"low": float(next_branch_windows[b][0]), "high": float(next_branch_windows[b][1])} for b in next_branch_windows},
                "reasonBranch": branch_reasons,
                "compareMdByBranch": compare_md_by_branch,
            }
        )

        _write_json(out_root / "journal.json", {"runs": journal})

        pulse_every = next_pulse_every
        branch_windows = next_branch_windows

    print(f"Adaptive run complete: {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
