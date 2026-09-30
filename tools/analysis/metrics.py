"""
Derived metrics computation for SOL run data.
==============================================
Operates on in-memory row dicts (list[dict]) — no pandas required.
"""
from __future__ import annotations

import math
import statistics
from typing import Any


def entropy_stats(rows: list[dict], key: str = "entropy") -> dict:
    """Compute summary statistics for an entropy time series."""
    vals = [r[key] for r in rows if key in r and isinstance(r[key], (int, float))]
    if not vals:
        return {"count": 0}
    return {
        "count": len(vals),
        "mean": statistics.mean(vals),
        "stdev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals),
        "max": max(vals),
        "final": vals[-1],
        "range": max(vals) - min(vals),
    }


def flux_stats(rows: list[dict], key: str = "totalFlux") -> dict:
    """Compute summary statistics for a flux time series."""
    return entropy_stats(rows, key)


def mass_stats(rows: list[dict], key: str = "mass") -> dict:
    """Compute summary statistics for total mass."""
    return entropy_stats(rows, key)


def active_count_stats(rows: list[dict], key: str = "activeCount") -> dict:
    """Compute summary statistics for active node count."""
    return entropy_stats(rows, key)


def rho_max_history(rows: list[dict]) -> dict:
    """Track which node holds rhoMax and for how many ticks."""
    id_key = "rhoMaxId"
    val_key = "maxRho"
    holder_ticks: dict[Any, int] = {}
    for r in rows:
        nid = r.get(id_key)
        if nid is not None:
            holder_ticks[nid] = holder_ticks.get(nid, 0) + 1

    peak_val = max((r.get(val_key, 0) for r in rows), default=0)
    dominant = max(holder_ticks, key=holder_ticks.get) if holder_ticks else None
    return {
        "dominant_node": dominant,
        "dominant_ticks": holder_ticks.get(dominant, 0) if dominant else 0,
        "total_ticks": len(rows),
        "peak_rho": peak_val,
        "holder_distribution": holder_ticks,
    }


def time_to_threshold(rows: list[dict], key: str = "entropy",
                       threshold: float = 0.5, direction: str = "above") -> int | None:
    """Return the step index where `key` first crosses `threshold`.
    direction='above' → first row where val >= threshold.
    direction='below' → first row where val <= threshold.
    Returns None if never crossed.
    """
    for i, r in enumerate(rows):
        v = r.get(key)
        if v is None:
            continue
        if direction == "above" and v >= threshold:
            return i
        if direction == "below" and v <= threshold:
            return i
    return None


def threshold_bracket(rows: list[dict], key: str = "entropy",
                       low: float = 0.4, high: float = 0.6) -> dict:
    """Find the step range where `key` is within [low, high]."""
    inside = [i for i, r in enumerate(rows) if low <= r.get(key, -999) <= high]
    if not inside:
        return {"first_entry": None, "last_exit": None, "ticks_inside": 0}
    return {
        "first_entry": inside[0],
        "last_exit": inside[-1],
        "ticks_inside": len(inside),
    }


def convergence_rate(rows: list[dict], key: str = "entropy",
                      window: int = 20) -> float | None:
    """Estimate convergence rate from last `window` samples.
    Returns the mean absolute change per step (lower = more converged).
    """
    vals = [r.get(key) for r in rows if r.get(key) is not None]
    if len(vals) < window + 1:
        return None
    tail = vals[-window:]
    diffs = [abs(tail[i+1] - tail[i]) for i in range(len(tail)-1)]
    return statistics.mean(diffs)


def summarize_condition(rows: list[dict]) -> dict:
    """Produce a full summary dict for a single condition's time series."""
    return {
        "entropy": entropy_stats(rows),
        "flux": flux_stats(rows),
        "mass": mass_stats(rows),
        "activeCount": active_count_stats(rows),
        "rhoMax": rho_max_history(rows),
        "convergence_entropy": convergence_rate(rows, "entropy"),
        "convergence_flux": convergence_rate(rows, "totalFlux"),
    }


def compare_conditions(summaries: dict[str, dict]) -> dict:
    """Given {condition_label: summary_dict}, produce comparison table."""
    table = {}
    metrics = ["entropy", "flux", "mass", "activeCount"]
    for metric in metrics:
        table[metric] = {}
        for label, summary in summaries.items():
            s = summary.get(metric, {})
            table[metric][label] = {
                "mean": s.get("mean"),
                "final": s.get("final"),
                "range": s.get("range"),
            }
    return table
