"""
Sanity checks for SOL experiment data.
=======================================
Implements the invariant-checking, sample-size, and detector-validation
patterns from the SOL skill library.
"""
from __future__ import annotations

from typing import Any


class SanityResult:
    """Container for a single check result."""

    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.detail}"

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


class SanityReport:
    """Collects multiple sanity check results."""

    def __init__(self):
        self.checks: list[SanityResult] = []

    def add(self, check: SanityResult):
        self.checks.append(check)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failures(self) -> list[SanityResult]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        return {
            "all_passed": self.all_passed,
            "total": len(self.checks),
            "failures": len(self.failures),
            "checks": [c.to_dict() for c in self.checks],
        }

    def __repr__(self):
        status = "ALL PASS" if self.all_passed else f"{len(self.failures)} FAILURES"
        return f"SanityReport({status}, {len(self.checks)} checks)"


def check_invariants(conditions: list[dict], invariant_keys: list[str]) -> SanityResult:
    """Verify that invariant parameters are constant across all conditions.
    
    Each condition dict must have the invariant keys present.
    """
    if not conditions:
        return SanityResult("invariants", False, "No conditions provided")

    violations = []
    for key in invariant_keys:
        values = set()
        for c in conditions:
            v = c.get(key)
            if v is not None:
                values.add(str(v))
        if len(values) > 1:
            violations.append(f"{key}: {values}")

    if violations:
        return SanityResult("invariants", False, f"Invariant drift: {'; '.join(violations)}")
    return SanityResult("invariants", True, f"All {len(invariant_keys)} invariants constant")


def check_sample_size(condition_sizes: dict[str, int], min_n: int = 3) -> SanityResult:
    """Check that each condition has at least min_n reps."""
    underpowered = {k: v for k, v in condition_sizes.items() if v < min_n}
    if underpowered:
        return SanityResult("sample_size", False,
                            f"Underpowered cells (n<{min_n}): {underpowered}")
    return SanityResult("sample_size", True,
                        f"All cells have n>={min_n} (cells: {len(condition_sizes)})")


def check_mass_conservation(rows: list[dict], injected_total: float,
                             tolerance: float = 0.01) -> SanityResult:
    """Check that total mass doesn't exceed injected amount (no mass creation).
    
    Note: mass can decrease (damping), but should never increase beyond injected.
    """
    if not rows:
        return SanityResult("mass_conservation", False, "No data")
    
    max_mass = max(r.get("mass", 0) for r in rows)
    if max_mass > injected_total * (1 + tolerance):
        return SanityResult("mass_conservation", False,
                            f"Mass exceeded injection: max={max_mass:.2f}, injected={injected_total:.2f}")
    return SanityResult("mass_conservation", True,
                        f"Mass bounded: max={max_mass:.2f} <= injected={injected_total:.2f}")


def check_entropy_bounds(rows: list[dict]) -> SanityResult:
    """Verify entropy stays in [0, 1] (normalized Shannon entropy)."""
    for i, r in enumerate(rows):
        e = r.get("entropy", 0)
        if e < -0.001 or e > 1.001:
            return SanityResult("entropy_bounds", False,
                                f"Entropy out of [0,1] at step {i}: {e:.6f}")
    return SanityResult("entropy_bounds", True, "Entropy in [0,1] for all steps")


def check_no_nan(rows: list[dict], keys: list[str] | None = None) -> SanityResult:
    """Check for NaN/Inf in key metrics."""
    import math
    check_keys = keys or ["entropy", "totalFlux", "mass", "maxRho", "activeCount"]
    for i, r in enumerate(rows):
        for k in check_keys:
            v = r.get(k)
            if v is not None and isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return SanityResult("no_nan", False, f"NaN/Inf in {k} at step {i}")
    return SanityResult("no_nan", True, "No NaN/Inf values found")


def check_baseline_declared(protocol: dict) -> SanityResult:
    """Verify the protocol declares a baseline mode."""
    mode = protocol.get("baseline")
    if mode in ("restore", "fresh"):
        return SanityResult("baseline_declared", True, f"Baseline mode: {mode}")
    return SanityResult("baseline_declared", False,
                        f"Baseline mode not declared or invalid: {mode}")


def run_standard_checks(protocol: dict, conditions: list[dict],
                         all_rows: list[dict], injected_total: float) -> SanityReport:
    """Run the standard suite of sanity checks for a completed experiment.
    
    Args:
        protocol: The protocol JSON dict.
        conditions: List of condition descriptors for invariant checking.
        all_rows: All per-step metric rows from the run.
        injected_total: Total density injected across all injections.
    """
    report = SanityReport()

    # Baseline declared
    report.add(check_baseline_declared(protocol))

    # Invariants
    inv_keys = list(protocol.get("invariants", {}).keys())
    if conditions and inv_keys:
        report.add(check_invariants(conditions, inv_keys))

    # Data quality
    report.add(check_no_nan(all_rows))
    report.add(check_entropy_bounds(all_rows))

    # Mass conservation (only if we have injection data)
    if injected_total > 0:
        report.add(check_mass_conservation(all_rows, injected_total))

    return report
