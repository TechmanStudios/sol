# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Burn-In Stability Metrics
=============================
Collects and tracks drift and stability metrics trends over burn-in cycles.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class BurnInStabilityMetric:
    metric_name: str
    values: List[float] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)

@dataclass
class BurnInMetricWindow:
    window_id: str
    start_cycle: int
    end_cycle: int
    metrics: Dict[str, BurnInStabilityMetric] = field(default_factory=dict)

@dataclass
class BurnInDriftReport:
    metric_name: str
    drift_value: float
    threshold_exceeded: bool
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BurnInStabilityTrend:
    metric_name: str
    slope: float
    improving: bool
    stability_score: float

@dataclass
class BurnInStabilitySummary:
    summary_id: str
    trends: Dict[str, BurnInStabilityTrend] = field(default_factory=dict)
    drifts: Dict[str, BurnInDriftReport] = field(default_factory=dict)
    overall_score: float = 1.0
    passed_thresholds: bool = True


def collect_burnin_metrics(cycle_reports: List[Any]) -> Dict[str, BurnInStabilityMetric]:
    """
    Collects metric values across multiple cycle reports.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    keys = [
        "phase_drift", "cadence_drift", "carrier_drift", "wavefront_coherence",
        "resonance_coherence", "uncertainty_window_size", "packet_dispersion",
        "pml_boundary_reflection", "crosstalk", "active_mass_preservation",
        "oracle_match_rate", "rollback_success_rate", "ranger_evidence_completeness",
        "court_verdict_consistency", "ledger_integrity"
    ]
    
    collected = {k: BurnInStabilityMetric(metric_name=k) for k in keys}
    
    for report in cycle_reports:
        metrics_dict = extract(report, "metrics", {}) or {}
        timestamp = extract(report, "timestamp", time.time())
        for k in keys:
            val = metrics_dict.get(k, 0.0)
            collected[k].values.append(float(val))
            collected[k].timestamps.append(timestamp)
            
    return collected


def measure_metric_drift(metrics: Dict[str, BurnInStabilityMetric], window: BurnInMetricWindow) -> Dict[str, BurnInDriftReport]:
    """
    Measures the drift (max - min or final - initial) of metrics in the given window.
    """
    drifts = {}
    thresholds = {
        "phase_drift": 0.05,
        "cadence_drift": 0.02,
        "carrier_drift": 0.03,
        "wavefront_coherence": 0.10,
        "resonance_coherence": 0.10,
        "uncertainty_window_size": 0.05,
        "packet_dispersion": 0.03,
        "pml_boundary_reflection": 0.05,
        "crosstalk": 0.04,
        "active_mass_preservation": 1.0,
        "oracle_match_rate": 0.05,
        "rollback_success_rate": 0.0,
        "ranger_evidence_completeness": 0.0,
        "court_verdict_consistency": 0.0,
        "ledger_integrity": 0.0
    }
    
    for name, m in metrics.items():
        vals = m.values[window.start_cycle : window.end_cycle + 1]
        if not vals:
            drifts[name] = BurnInDriftReport(name, 0.0, False)
            continue
            
        drift = max(vals) - min(vals)
        limit = thresholds.get(name, 0.05)
        
        # Check negative drift for coherence, mass, rates where lower is worse
        # For simplify, if drift > limit, check if trend is deteriorating
        exceeded = drift > limit
        drifts[name] = BurnInDriftReport(
            metric_name=name,
            drift_value=drift,
            threshold_exceeded=exceeded,
            details={"min": min(vals), "max": max(vals), "limit": limit}
        )
        
    return drifts


def detect_stability_regression(metrics: Dict[str, BurnInStabilityMetric], policy: Any) -> bool:
    """
    Returns True if any metric exceeds its drift threshold or shows critical deterioration.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    max_cycles = len(next(iter(metrics.values())).values) if metrics else 0
    if max_cycles <= 1:
        return False
        
    window = BurnInMetricWindow("W_REG", 0, max_cycles - 1)
    drifts = measure_metric_drift(metrics, window)
    
    for report in drifts.values():
        if report.threshold_exceeded:
            return True
            
    # Wavefront coherence drop below 0.90 is a regression
    if "wavefront_coherence" in metrics:
        vals = metrics["wavefront_coherence"].values
        if vals and vals[-1] < 0.90:
            return True
            
    # Resonance coherence drop below 0.90
    if "resonance_coherence" in metrics:
        vals = metrics["resonance_coherence"].values
        if vals and vals[-1] < 0.90:
            return True
            
    # Active mass drop below 14.0
    if "active_mass_preservation" in metrics:
        vals = metrics["active_mass_preservation"].values
        if vals and vals[-1] < 14.0:
            return True
            
    return False


def summarize_stability_trends(metrics: Dict[str, BurnInStabilityMetric]) -> BurnInStabilitySummary:
    """
    Analyzes trends and returns a comprehensive stability summary.
    """
    trends = {}
    drifts = {}
    overall_score = 1.0
    passed = True
    
    max_cycles = len(next(iter(metrics.values())).values) if metrics else 0
    window = BurnInMetricWindow("W_SUM", 0, max_cycles - 1)
    drifts = measure_metric_drift(metrics, window)
    
    for name, m in metrics.items():
        vals = m.values
        if len(vals) < 2:
            trends[name] = BurnInStabilityTrend(name, 0.0, True, 1.0)
            continue
            
        slope = vals[-1] - vals[0]
        # For coherence, mass, rates: positive slope is improving
        # For drift, dispersion, reflection, crosstalk: negative slope is improving
        improving = True
        if name in ["wavefront_coherence", "resonance_coherence", "active_mass_preservation", "oracle_match_rate", "rollback_success_rate"]:
            improving = slope >= 0
        else:
            improving = slope <= 0
            
        stability_score = 1.0 - abs(slope)
        trends[name] = BurnInStabilityTrend(
            metric_name=name,
            slope=slope,
            improving=improving,
            stability_score=stability_score
        )
        
    for r in drifts.values():
        if r.threshold_exceeded:
            passed = False
            overall_score = min(overall_score, 0.5)
            
    return BurnInStabilitySummary(
        summary_id=f"SUM_TRND_{uuid.uuid4().hex[:8]}",
        trends=trends,
        drifts=drifts,
        overall_score=overall_score,
        passed_thresholds=passed
    )
