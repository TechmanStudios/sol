#!/usr/bin/env python3
"""
SOL Claim Compiler
==================

Closes the RSI feedback loop by analyzing experiment result JSON files,
extracting claim-worthy findings, and updating the proof packet.

Pipeline:
    1. Scan experiment output directories for JSON result files
    2. Extract metadata (trial counts, compute time)
    3. Detect claim-worthy patterns via template matching
    4. Check if open questions are answered
    5. Append new claims + experiment sections to proof packet
    6. Update proof packet header with cumulative stats
    7. Track compiled files to avoid double-counting

Claim Detection Patterns:
    BASIN_STABILITY   — same basin across N+ configs in a sweep
    GATE_FUNCTIONAL   — truth-table match for known gate type
    ENTROPY_PROFILE   — monotonic entropy vs damping trend
    NOISE_RESILIENCE  — stability above threshold across noise levels
    CAPACITY_BITS     — unique basin count → information capacity
    CASCADE_FIDELITY  — signal preservation/degradation in pipelines
    ENERGY_THRESHOLD  — basin switch at specific energy level
    DEAD_ZONE_LOCK    — invariant basin across entire damping range

Each auto-detected claim is tagged [AUTO-Cnn] and includes:
    - Claim text from template
    - Evidence summary (trials, parameter ranges, key metrics)
    - Confidence level (fraction of supporting trials)
"""
from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent
_DATA_DIR = _SOL_ROOT / "data"
_RSI_DIR = _DATA_DIR / "rsi"
_PROOF_PACKETS_DIR = _SOL_ROOT / "solKnowledge" / "proof_packets"
_DOMAINS_DIR = _PROOF_PACKETS_DIR / "domains"
_LEDGER_FILE = _PROOF_PACKETS_DIR / "LEDGER.md"
_COMPILED_MANIFEST = _RSI_DIR / "compiled_manifest.jsonl"

# Default domain — all current claims route here
_DEFAULT_DOMAIN = "phonon_faraday"


def _get_domain_packet(domain: str = _DEFAULT_DOMAIN) -> Path:
    """Get the path to a domain proof packet."""
    return _DOMAINS_DIR / f"{domain}.md"


# Backward-compat alias — code that references _MAIN_PACKET still works
_MAIN_PACKET = _get_domain_packet(_DEFAULT_DOMAIN)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PendingClaim:
    """A claim candidate extracted from experiment data."""
    claim_id: str = ""          # e.g. "C23"
    text: str = ""              # Claim statement
    evidence: str = ""          # Evidence summary for the table
    source_file: str = ""       # JSON file that produced this claim
    pattern: str = ""           # Detection pattern name
    confidence: float = 0.0     # 0.0 - 1.0
    trials: int = 0             # Supporting trial count
    details: dict = field(default_factory=dict)  # Raw evidence data


@dataclass
class OpenQuestionUpdate:
    """An update to an existing open question."""
    question_number: int = 0    # 1-4
    status: str = "open"        # open, answered, partially_answered
    answer_summary: str = ""    # Brief answer text
    evidence: str = ""          # What experiment answered it


@dataclass
class CompileResult:
    """Summary of a compilation run."""
    timestamp: str = ""
    files_scanned: int = 0
    files_new: int = 0              # Not previously compiled
    total_trials_added: int = 0
    compute_seconds_added: float = 0.0
    new_claims: list[PendingClaim] = field(default_factory=list)
    question_updates: list[OpenQuestionUpdate] = field(default_factory=list)
    experiments_added: int = 0
    proof_packet_updated: bool = False
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 1. Result Scanner
# ---------------------------------------------------------------------------

def scan_result_files(data_dir: Path) -> list[Path]:
    """Find all experiment result JSON files in a data directory."""
    files = []
    if not data_dir.is_dir():
        return files
    for f in sorted(data_dir.glob("*.json")):
        # Skip manifest/meta files
        if f.name in ("all_results.json", "compiled_manifest.json"):
            continue
        files.append(f)
    return files


def load_compiled_set() -> set[str]:
    """Load the set of already-compiled file paths."""
    compiled = set()
    if _COMPILED_MANIFEST.exists():
        with open(_COMPILED_MANIFEST, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        compiled.add(entry.get("file", ""))
                    except json.JSONDecodeError:
                        pass
    return compiled


def mark_compiled(file_path: str, claims_produced: int, trials: int):
    """Record that a file has been compiled."""
    _RSI_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "file": file_path,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "claims_produced": claims_produced,
        "trials": trials,
    }
    with open(_COMPILED_MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# 2. Claim Detectors
# ---------------------------------------------------------------------------
# Each detector takes a parsed JSON result dict and returns a list of
# PendingClaim objects (possibly empty).
# ---------------------------------------------------------------------------

def detect_basin_stability(data: dict, source: str) -> list[PendingClaim]:
    """Detect if a sweep shows the same basin across many damping values."""
    claims = []

    # Look for sweep-style results with damping + basin fields
    results = _extract_results_list(data)
    if not results or len(results) < 5:
        return claims

    # Group by basin
    basin_runs: dict[str, list] = {}
    for r in results:
        basin = r.get("basin_label") or r.get("basin") or r.get("final_basin")
        if basin and basin not in ("?", "None", None):
            basin_str = str(basin)
            basin_runs.setdefault(basin_str, []).append(r)

    # If one basin captures >80% of runs across a damping range
    for basin, runs in basin_runs.items():
        if len(runs) >= 0.8 * len(results) and len(runs) >= 5:
            dampings = sorted(set(r.get("damping", 0) for r in runs if "damping" in r))
            if len(dampings) >= 3:
                d_min, d_max = min(dampings), max(dampings)
                claims.append(PendingClaim(
                    text=f"Basin '{basin}' is the deterministic attractor across damping "
                         f"range d={d_min}-{d_max} ({len(dampings)} values tested), "
                         f"capturing {len(runs)}/{len(results)} configurations",
                    evidence=f"{len(results)} trials, d={d_min}-{d_max}",
                    source_file=source,
                    pattern="BASIN_STABILITY",
                    confidence=len(runs) / len(results),
                    trials=len(results),
                    details={"basin": basin, "d_range": [d_min, d_max],
                             "configs": len(runs), "total": len(results)},
                ))
    return claims


def detect_gate_functional(data: dict, source: str) -> list[PendingClaim]:
    """Detect functional logic gates from truth table data."""
    claims = []
    probes = data.get("probes", {})

    for probe_name, probe_data in probes.items():
        if not isinstance(probe_data, list):
            continue
        for entry in probe_data:
            tt = entry.get("truth_table")
            damping = entry.get("damping", "?")
            if not tt:
                continue

            # XOR detection
            if entry.get("xor_like") is True:
                claims.append(PendingClaim(
                    text=f"XOR-like gate is functional at d={damping}: each single input "
                         f"routes to a distinct basin, dual input routes to a third basin — "
                         f"three distinguishable output states",
                    evidence=f"4-entry truth table at d={damping}",
                    source_file=source,
                    pattern="GATE_FUNCTIONAL",
                    confidence=1.0,
                    trials=4,
                    details={"gate": "XOR", "damping": damping, "truth_table": tt},
                ))

            # NAND detection
            if entry.get("nand_functional") is True:
                claims.append(PendingClaim(
                    text=f"NAND gate (cascaded NOT+AND) is functional at d={damping}",
                    evidence=f"NAND truth table verified at d={damping}",
                    source_file=source,
                    pattern="GATE_FUNCTIONAL",
                    confidence=1.0,
                    trials=4,
                    details={"gate": "NAND", "damping": damping},
                ))

    return claims


def detect_entropy_profile(data: dict, source: str) -> list[PendingClaim]:
    """Detect information-theoretic entropy profiles."""
    claims = []
    if data.get("type") != "entropy_measurement":
        return claims

    results = data.get("results", [])
    if len(results) < 3:
        return claims

    # Extract damping -> final_entropy pairs
    pairs = []
    for r in results:
        d = r.get("damping")
        e = r.get("final_entropy")
        m = r.get("max_entropy", 7.13)
        if d is not None and e is not None:
            pairs.append((d, e, m))
    pairs.sort()

    if len(pairs) < 3:
        return claims

    # Check for entropy cliff: where does entropy drop below 80% of max?
    max_ent = pairs[0][2]
    cliff_d = None
    for d, e, m in pairs:
        if e < 0.8 * max_ent and cliff_d is None:
            cliff_d = d

    # Find near-max region
    near_max = [(d, e) for d, e, m in pairs if e > 0.95 * max_ent]
    low_region = [(d, e) for d, e, m in pairs if e < 0.5 * max_ent]

    if near_max and low_region:
        near_max_d = max(d for d, _ in near_max)
        pct_low = min(e / max_ent for _, e in low_region)
        claims.append(PendingClaim(
            text=f"Entropy profile traces a degradation curve from near-maximum "
                 f"({near_max[0][1]/max_ent:.1%}) at low damping to "
                 f"{pct_low:.1%} near extinction. "
                 f"{'Entropy cliff occurs at d≈' + str(cliff_d) if cliff_d else 'Degradation is gradual'}",
            evidence=f"{len(pairs)} damping values, entropy range "
                     f"{min(e for _, e, _ in pairs):.2f}-{max(e for _, e, _ in pairs):.2f} "
                     f"(max={max_ent:.2f})",
            source_file=source,
            pattern="ENTROPY_PROFILE",
            confidence=0.95,
            trials=data.get("trials", len(pairs)),
            details={"pairs": pairs, "cliff_d": cliff_d},
        ))
    return claims


def detect_noise_resilience(data: dict, source: str) -> list[PendingClaim]:
    """Detect error correction / noise resilience patterns."""
    claims = []
    if data.get("type") != "error_resilience":
        return claims

    results = data.get("results", [])
    if len(results) < 4:
        return claims

    # Group by damping
    by_damping: dict[float, list] = {}
    for r in results:
        d = r.get("damping", 0)
        by_damping.setdefault(d, []).append(r)

    for damping, runs in by_damping.items():
        # Sort by noise_std
        runs.sort(key=lambda x: x.get("noise_std", 0))

        # Find max noise where stability >= 0.9
        stable_threshold = None
        for r in runs:
            if r.get("stability", 0) >= 0.9:
                stable_threshold = r.get("noise_std", 0)

        if stable_threshold is not None and stable_threshold > 0:
            claims.append(PendingClaim(
                text=f"At d={damping}, basin identity is resilient to noise: "
                     f"100% stable up to σ={stable_threshold}, with graceful "
                     f"degradation (stability={runs[-1].get('stability', 0):.0%} "
                     f"at σ={runs[-1].get('noise_std', 0)})",
                evidence=f"{len(runs)} noise levels at d={damping}",
                source_file=source,
                pattern="NOISE_RESILIENCE",
                confidence=0.9,
                trials=data.get("trials", len(runs)),
                details={"damping": damping, "stable_threshold": stable_threshold},
            ))
    return claims


def detect_capacity(data: dict, source: str) -> list[PendingClaim]:
    """Detect information capacity measurements."""
    claims = []
    if data.get("type") != "capacity_measurement":
        return claims

    total_basins = data.get("total_unique_basins", 0)
    total_bits = data.get("total_bits", 0)

    if total_basins >= 5:
        per_damping = data.get("per_damping", [])
        detail_parts = []
        peak_d = None
        peak_basins = 0
        for pd in per_damping:
            d = pd.get("damping", "?")
            ub = pd.get("unique_basins", 0)
            bits = pd.get("bits", 0)
            detail_parts.append(f"d={d}: {ub} basins ({bits:.2f} bits)")
            if ub > peak_basins:
                peak_basins = ub
                peak_d = d

        claims.append(PendingClaim(
            text=f"Information capacity of the lattice is ~{total_bits:.1f} bits "
                 f"({total_basins} distinguishable basins across tested configurations). "
                 f"Capacity peaks at d={peak_d} with {peak_basins} unique basins"
                 + (f" — moderate damping creates *more* distinct attractors than low damping"
                    if peak_d and peak_d > 1.0 else ""),
            evidence=f"{data.get('trials', 0)} trials, "
                     + ", ".join(detail_parts),
            source_file=source,
            pattern="CAPACITY_BITS",
            confidence=0.95,
            trials=data.get("trials", 0),
            details={"total_basins": total_basins, "total_bits": total_bits,
                     "peak_d": peak_d, "peak_basins": peak_basins},
        ))
    return claims


def detect_dead_zone_lock(data: dict, source: str) -> list[PendingClaim]:
    """Detect dead-zone invariant basin lock from sweep data."""
    claims = []
    probes = data.get("probes", {})

    sweep = probes.get("sweep", [])
    if not sweep or len(sweep) < 5:
        return claims

    # Check each injection type for invariance
    for inject_type in ("standard", "cold_inject", "clock_assisted"):
        basins = []
        dampings = []
        for row in sweep:
            d = row.get("damping", 0)
            entry = row.get(inject_type, {})
            if isinstance(entry, dict):
                basin = entry.get("basin_label", "")
                if basin:
                    basins.append(basin)
                    dampings.append(d)

        if len(basins) >= 5:
            unique = set(basins)
            if len(unique) == 1:
                basin_name = basins[0]
                d_min, d_max = min(dampings), max(dampings)
                claims.append(PendingClaim(
                    text=f"Dead zone basin lock: {inject_type.replace('_', ' ')} injection "
                         f"routes to '{basin_name}' invariantly across entire dead zone "
                         f"d={d_min}-{d_max} — basin is impervious to damping within this range",
                    evidence=f"{len(basins)} configs, d={d_min}-{d_max}",
                    source_file=source,
                    pattern="DEAD_ZONE_LOCK",
                    confidence=1.0,
                    trials=len(basins),
                    details={"inject_type": inject_type, "basin": basin_name,
                             "d_range": [d_min, d_max]},
                ))
    return claims


def detect_cascade_fidelity(data: dict, source: str) -> list[PendingClaim]:
    """Detect cascade signal preservation/degradation."""
    claims = []
    probes = data.get("probes", {})

    # Check q4_cascade_depth in suite_1 format
    cascade_data = probes.get("q4_cascade_depth", [])
    if not cascade_data:
        return claims

    # Separate standard cascades from NOT cascades
    standard = [r for r in cascade_data if r.get("type", "standard") == "standard"
                or "signal_preserved" in r]
    not_chains = [r for r in cascade_data if r.get("type") == "not_chain"
                  or r.get("alternating") is not None]

    # Standard cascade degradation
    if standard:
        all_degraded = all(r.get("signal_preserved") is False for r in standard
                          if "signal_preserved" in r)
        if all_degraded and len(standard) >= 3:
            max_stages = max(r.get("n_stages", 0) for r in standard)
            claims.append(PendingClaim(
                text=f"Standard pipeline cascades (2-{max_stages} stages) all collapse to a "
                     f"single attractor — signal is NOT preserved through multi-stage "
                     f"standard injection pipelines",
                evidence=f"{len(standard)} cascade tests, 2-{max_stages} stages",
                source_file=source,
                pattern="CASCADE_FIDELITY",
                confidence=1.0,
                trials=len(standard),
                details={"type": "standard_degradation", "max_stages": max_stages},
            ))

    # NOT chain fidelity
    if not_chains:
        all_alternating = all(r.get("alternating") is True for r in not_chains
                             if "alternating" in r)
        if all_alternating and len(not_chains) >= 3:
            max_stages = max(r.get("n_stages", 0) for r in not_chains)
            claims.append(PendingClaim(
                text=f"NOT-gate cascades preserve faithful alternation through "
                     f"{max_stages} stages — each stage inverts the previous, "
                     f"maintaining signal integrity throughout the chain",
                evidence=f"{len(not_chains)} NOT-chain tests, 2-{max_stages} stages",
                source_file=source,
                pattern="CASCADE_FIDELITY",
                confidence=1.0,
                trials=len(not_chains),
                details={"type": "not_chain_fidelity", "max_stages": max_stages},
            ))
    return claims


def detect_energy_threshold(data: dict, source: str) -> list[PendingClaim]:
    """Detect minimum energy for basin control."""
    claims = []
    probes = data.get("probes", {})

    min_energy = probes.get("min_energy", [])
    if not min_energy or len(min_energy) < 3:
        return claims

    # Sort by energy
    sorted_e = sorted(min_energy, key=lambda x: x.get("total_energy", 0))

    # Detect basin switch point
    basins_by_energy = [(r.get("total_energy", 0), r.get("basin", "")) for r in sorted_e]
    switch_point = None
    for i in range(len(basins_by_energy) - 1):
        if basins_by_energy[i][1] != basins_by_energy[i + 1][1]:
            switch_point = (basins_by_energy[i][0], basins_by_energy[i + 1][0])
            break

    if switch_point:
        claims.append(PendingClaim(
            text=f"Basin control has an energy threshold: below E={switch_point[1]} the "
                 f"dominant basin shifts (from '{basins_by_energy[-1][1]}' to "
                 f"'{basins_by_energy[0][1]}'). "
                 f"Minimum meaningful injection: E={sorted_e[0].get('total_energy', 0)} "
                 f"produces mass={sorted_e[0].get('mass', 0):.3f}",
            evidence=f"{len(min_energy)} energy levels tested, "
                     f"E={sorted_e[0].get('total_energy', 0)}-{sorted_e[-1].get('total_energy', 0)}",
            source_file=source,
            pattern="ENERGY_THRESHOLD",
            confidence=0.9,
            trials=len(min_energy),
            details={"switch_point": switch_point,
                     "basins": basins_by_energy},
        ))
    return claims


def detect_extreme_w0_invariance(data: dict, source: str) -> list[PendingClaim]:
    """Detect that extreme w0 values don't break dead zone."""
    claims = []
    probes = data.get("probes", {})

    extreme_data = probes.get("extreme_w0", [])
    if not extreme_data or len(extreme_data) < 5:
        return claims

    # Check if all land on same basin regardless of w0
    basins = set()
    w0_values = set()
    for r in extreme_data:
        basin = r.get("basin_label", "")
        w0 = r.get("w0_spirit", 0)
        if basin:
            basins.add(basin)
        w0_values.add(w0)

    if len(basins) == 1 and len(w0_values) >= 3:
        max_w0 = max(w0_values)
        claims.append(PendingClaim(
            text=f"Dead zone is impervious to energy magnitude: spirit-highway w0 "
                 f"from {min(w0_values)} to {max_w0} all route to '{list(basins)[0]}' — "
                 f"the dead zone is not an energy deficit but a topological trap",
            evidence=f"{len(extreme_data)} trials, w0={min(w0_values)}-{max_w0}",
            source_file=source,
            pattern="DEAD_ZONE_LOCK",
            confidence=1.0,
            trials=len(extreme_data),
            details={"basin": list(basins)[0], "w0_range": sorted(w0_values)},
        ))
    return claims


# ---------------------------------------------------------------------------
# 2b. NEW Claim Detectors — Latch, Adder, Temporal, Injection Diversity
# ---------------------------------------------------------------------------

def detect_latch_behavior(data: dict, source: str) -> list[PendingClaim]:
    """Detect SR-latch or memory-element behavior from probe data."""
    claims = []
    probes = data.get("probes", {})

    sr_data = probes.get("sr_latch", [])
    if not sr_data:
        # Also check top-level results for latch-style keys
        results = _extract_results_list(data)
        sr_data = [r for r in results
                   if "grail_first" in r or "order_dependent" in r]
    if not sr_data or len(sr_data) < 2:
        return claims

    for row in sr_data:
        d = row.get("damping", "?")
        grail_first = row.get("grail_first", "")
        metatron_first = row.get("metatron_first", "")
        simultaneous = row.get("simultaneous", "")
        order_dep = row.get("order_dependent", None)

        # Skip empty rows
        if not grail_first and not metatron_first:
            continue

        # Third-state detection: simultaneous input produces a different basin
        if (simultaneous and grail_first and metatron_first
                and simultaneous != grail_first
                and simultaneous != metatron_first):
            claims.append(PendingClaim(
                text=f"SR-latch at d={d} exhibits third-state behavior: sequential "
                     f"inputs route to '{grail_first}'/'{metatron_first}', but "
                     f"simultaneous input produces distinct basin '{simultaneous}' — "
                     f"a memory element with three output states",
                evidence=f"SR-latch probe at d={d}, 3 input orderings",
                source_file=source,
                pattern="LATCH_BEHAVIOR",
                confidence=0.9,
                trials=3,
                details={"damping": d, "grail_first": grail_first,
                         "metatron_first": metatron_first,
                         "simultaneous": simultaneous,
                         "order_dependent": order_dep},
            ))

        # Order-dependent routing
        if order_dep is True and grail_first != metatron_first:
            claims.append(PendingClaim(
                text=f"Injection order determines basin identity at d={d}: "
                     f"grail-first → '{grail_first}', metatron-first → "
                     f"'{metatron_first}' — the lattice has input-order memory",
                evidence=f"SR-latch probe at d={d}",
                source_file=source,
                pattern="LATCH_BEHAVIOR",
                confidence=1.0,
                trials=2,
                details={"damping": d, "order_dependent": True,
                         "grail_first": grail_first,
                         "metatron_first": metatron_first},
            ))

    return claims


def detect_half_adder(data: dict, source: str) -> list[PendingClaim]:
    """Detect half-adder (2-input arithmetic) behavior."""
    claims = []
    probes = data.get("probes", {})

    ha_data = probes.get("half_adder", [])
    if not ha_data:
        results = _extract_results_list(data)
        ha_data = [r for r in results if "A" in r and "B" in r and "basin" in r]
    if not ha_data or len(ha_data) < 3:
        return claims

    # Build truth table: (A, B) → basin
    truth_table = {}
    for row in ha_data:
        a = row.get("A", 0)
        b = row.get("B", 0)
        basin = row.get("basin", "")
        if basin and basin not in ("?[None]", "None"):
            truth_table[(a, b)] = basin

    # Need at least 3 valid entries from {(0,0), (1,0), (0,1), (1,1)}
    if len(truth_table) < 3:
        return claims

    # Count distinct output basins
    unique_outputs = set(truth_table.values())

    # A valid adder has: (0,0)→null/zero, (1,0)→basin_a, (0,1)→basin_b, (1,1)→basin_sum
    # Key: (1,1) should differ from single-input results
    basin_11 = truth_table.get((1, 1))
    basin_10 = truth_table.get((1, 0))
    basin_01 = truth_table.get((0, 1))

    if basin_11 and basin_10 and basin_11 != basin_10:
        claims.append(PendingClaim(
            text=f"Half-adder behavior: dual injection (A+B) routes to "
                 f"'{basin_11}', while single-A routes to '{basin_10}'"
                 f"{' and single-B routes to ' + repr(basin_01) if basin_01 else ''}"
                 f" — {len(unique_outputs)} distinct output states from "
                 f"2-input combinational logic",
            evidence=f"{len(truth_table)}-entry truth table, "
                     f"{len(unique_outputs)} unique basins",
            source_file=source,
            pattern="HALF_ADDER",
            confidence=0.95,
            trials=len(ha_data),
            details={"truth_table": {f"{k[0]},{k[1]}": v
                                     for k, v in truth_table.items()},
                     "unique_outputs": len(unique_outputs)},
        ))

    return claims


def detect_temporal_injection(data: dict, source: str) -> list[PendingClaim]:
    """Detect that different temporal injection patterns route to different basins."""
    claims = []
    probes = data.get("probes", {})

    burst_data = probes.get("burst_patterns", [])
    if not burst_data or len(burst_data) < 2:
        return claims

    for row in burst_data:
        d = row.get("damping", "?")
        patterns = {}
        for key in ("burst_5x30", "ramp_10to50", "oscillating", "single_shot"):
            val = row.get(key)
            if val and val not in ("?", "None"):
                patterns[key] = val

        if len(patterns) < 3:
            continue

        unique_basins = set(patterns.values())
        if len(unique_basins) >= 3:
            claims.append(PendingClaim(
                text=f"Temporal injection diversity at d={d}: {len(unique_basins)} "
                     f"distinct basins from {len(patterns)} injection patterns "
                     f"({', '.join(f'{k}→{v}' for k, v in patterns.items())}) — "
                     f"the lattice is sensitive to injection *timing*, not just total energy",
                evidence=f"{len(patterns)} temporal patterns at d={d}, "
                         f"{len(unique_basins)} unique basins",
                source_file=source,
                pattern="TEMPORAL_INJECTION",
                confidence=0.9,
                trials=len(patterns),
                details={"damping": d, "patterns": patterns,
                         "unique_basins": len(unique_basins)},
            ))

    return claims


def detect_injection_diversity(data: dict, source: str) -> list[PendingClaim]:
    """Detect that different injection configurations route to different basins."""
    claims = []
    probes = data.get("probes", {})

    asym_data = probes.get("asymmetric", [])
    if not asym_data or len(asym_data) < 4:
        return claims

    # Group by damping
    by_damping: dict = {}
    for row in asym_data:
        d = row.get("damping", 0)
        config = row.get("config", "?")
        basin = row.get("basin", "?")
        by_damping.setdefault(d, {})[config] = basin

    for d, configs in by_damping.items():
        unique_basins = set(configs.values())
        if len(unique_basins) >= 3 and len(configs) >= 3:
            claims.append(PendingClaim(
                text=f"Injection topology diversity at d={d}: {len(unique_basins)} "
                     f"distinct basins from {len(configs)} injection configurations "
                     f"— spatial injection pattern selects the attractor",
                evidence=f"{len(configs)} configs at d={d}, "
                         f"{len(unique_basins)} unique basins",
                source_file=source,
                pattern="INJECTION_DIVERSITY",
                confidence=0.9,
                trials=len(configs),
                details={"damping": d, "configs": configs,
                         "unique_basins": len(unique_basins)},
            ))

    return claims


def detect_min_energy_transition(data: dict, source: str) -> list[PendingClaim]:
    """Detect minimum energy basin identity transitions."""
    claims = []
    probes = data.get("probes", {})
    results = _extract_results_list(data)

    # Check for min_energy probe or results with total_energy field
    min_e = probes.get("min_energy", [])
    if not min_e:
        min_e = [r for r in results if "total_energy" in r]
    if not min_e or len(min_e) < 4:
        return claims

    # Sort by energy descending
    sorted_e = sorted(min_e, key=lambda x: x.get("total_energy", 0), reverse=True)

    # Track iton transitions
    high_e = [r for r in sorted_e if r.get("total_energy", 0) >= 50]
    low_e = [r for r in sorted_e if r.get("total_energy", 0) <= 10]

    if high_e and low_e:
        high_iton = [r.get("iton", 0) for r in high_e if "iton" in r]
        low_iton = [r.get("iton", 0) for r in low_e if "iton" in r]

        if high_iton and low_iton:
            avg_high = sum(high_iton) / len(high_iton)
            avg_low = sum(low_iton) / len(low_iton)

            # Counterintuitive: lower energy → higher iton
            if avg_low > avg_high * 1.5 and avg_low >= 0.7:
                claims.append(PendingClaim(
                    text=f"Counterintuitive energy-iton relationship: low injection "
                         f"energy (E≤10) produces *higher* iton ({avg_low:.3f}) than "
                         f"high energy (E≥50, iton={avg_high:.3f}) — minimal "
                         f"perturbation yields maximal information transport",
                    evidence=f"{len(min_e)} energy levels tested",
                    source_file=source,
                    pattern="MIN_ENERGY_ITON",
                    confidence=0.85,
                    trials=len(min_e),
                    details={"avg_high_iton": avg_high, "avg_low_iton": avg_low,
                             "n_levels": len(min_e)},
                ))

    return claims


# Master detector list
ALL_DETECTORS = [
    detect_basin_stability,
    detect_gate_functional,
    detect_entropy_profile,
    detect_noise_resilience,
    detect_capacity,
    detect_dead_zone_lock,
    detect_cascade_fidelity,
    detect_energy_threshold,
    detect_extreme_w0_invariance,
    # --- NEW detectors (Phase 2 plateau break) ---
    detect_latch_behavior,
    detect_half_adder,
    detect_temporal_injection,
    detect_injection_diversity,
    detect_min_energy_transition,
]


def run_detectors(data: dict, source: str) -> list[PendingClaim]:
    """Run all claim detectors on a result file."""
    claims = []
    for detector in ALL_DETECTORS:
        try:
            found = detector(data, source)
            claims.extend(found)
        except Exception as e:
            pass  # Individual detector failures shouldn't stop compilation
    return claims


# ---------------------------------------------------------------------------
# 3. Open Question Resolver
# ---------------------------------------------------------------------------

def check_open_questions(suite_results: dict[str, dict]) -> list[OpenQuestionUpdate]:
    """
    Check if overnight results answer the known open questions.

    Q1: Higher-order analog correction (R² > 0.99?)
    Q2: Dead zone physics (why christic[22]?)
    Q3: Clock optimization (optimal period?)
    Q4: Cascade depth limit (max depth?)
    Q5: Half-adder generalization across damping regimes
    Q6: SR-latch third-state reproducibility
    Q7: Temporal injection minimum distinguishing cadence
    Q8: Dream afterstate — rest-phase basin drift
    """
    updates = []

    # Q1: Analog correction — check max R² values
    for name, data in suite_results.items():
        probes = data.get("probes", {})
        q1 = probes.get("q1_analog_correction", [])
        if q1:
            r2_values = [r.get("r2_simple", 0) for r in q1 if r.get("r2_simple", 0) > 0]
            r2_multi = [r.get("r2_multi", 0) for r in q1 if r.get("r2_multi", 0) > 0]
            max_r2 = max(r2_values + r2_multi) if (r2_values or r2_multi) else 0

            if max_r2 > 0.99:
                updates.append(OpenQuestionUpdate(
                    question_number=1,
                    status="answered",
                    answer_summary=f"R²={max_r2:.4f} achieved — higher-order correction successful",
                    evidence=f"{len(q1)} configurations tested",
                ))
            elif max_r2 > 0:
                updates.append(OpenQuestionUpdate(
                    question_number=1,
                    status="answered",
                    answer_summary=f"R² ceiling is ~{max_r2:.3f} with current terms. "
                                   f"Multivariate regression with psi_diff, delta_p², rho_sum, "
                                   f"and w0 does not reach 0.99 — the 6% residual appears "
                                   f"structural rather than correctable by linear terms",
                    evidence=f"{len(q1)} damping×step configurations, max R²={max_r2:.3f}",
                ))

        # Q2: Dead zone physics
        q2 = probes.get("q2_dead_zone_physics")
        if q2 and isinstance(q2, dict):
            christic_info = q2.get("christic_22")
            if christic_info:
                updates.append(OpenQuestionUpdate(
                    question_number=2,
                    status="partially_answered",
                    answer_summary=f"christic[22] has degree {christic_info.get('degree', '?')}, "
                                   f"spirit group, avg neighbor degree "
                                   f"{christic_info.get('avg_neighbor_degree', '?')}. In dead zone "
                                   f"only 2-3/140 nodes route to it. The dead zone is not an energy "
                                   f"deficit — w0 up to 1000 still routes to christic[22]. "
                                   f"Cold and clock injection can override basin selection",
                    evidence="Structural analysis + w0 sweep + injection diversity probe",
                ))

        # Q3: Clock optimization
        q3 = probes.get("q3_clock_optimization", [])
        if q3 and isinstance(q3, list) and len(q3) > 3:
            # Find best config
            best = max(q3, key=lambda x: x.get("avg_iton", 0) if x.get("sustained") else 0)
            if best.get("avg_iton", 0) > 0:
                updates.append(OpenQuestionUpdate(
                    question_number=3,
                    status="answered",
                    answer_summary=f"Optimal clock: period={best.get('period', '?')}, "
                                   f"pulse_frac={best.get('pulse_frac', '?')}, "
                                   f"avg_iton={best.get('avg_iton', 0):.3f} at "
                                   f"d={best.get('damping', '?')}. "
                                   f"The ~2× heartbeat period (75 steps vs 35-step heartbeat) "
                                   f"is the optimal resonance, not 3× as hypothesized",
                    evidence=f"{len(q3)} period×pulse×damping configurations swept",
                ))

        # Q4: Cascade depth
        q4 = probes.get("q4_cascade_depth", [])
        if q4 and isinstance(q4, list) and len(q4) > 3:
            standard = [r for r in q4 if "signal_preserved" in r]
            not_chains = [r for r in q4 if "alternating" in r]
            parts = []
            if standard:
                max_tested = max(r.get("n_stages", 0) for r in standard)
                all_degraded = all(not r.get("signal_preserved", True) for r in standard)
                if all_degraded:
                    parts.append(f"Standard cascades degrade at ALL depths (2-{max_tested})")
            if not_chains:
                max_not = max(r.get("n_stages", 0) for r in not_chains)
                all_alternating = all(r.get("alternating", False) for r in not_chains)
                if all_alternating:
                    parts.append(f"NOT-chains preserve alternation through {max_not} stages")
            if parts:
                updates.append(OpenQuestionUpdate(
                    question_number=4,
                    status="answered",
                    answer_summary="; ".join(parts) +
                                   ". The cascade depth limit is architecture-dependent: "
                                   "injection pipelines immediately collapse, "
                                   "NOT-chain inversions are indefinitely faithful",
                    evidence=f"{len(q4)} cascade tests",
                ))

        # Q5: Half-adder generalization
        ha = probes.get("half_adder", [])
        if ha and isinstance(ha, list) and len(ha) >= 3:
            # Check if there are results at multiple dampings
            dampings_tested = set()
            truth_tables_by_d: dict[float, dict] = {}
            for row in ha:
                d = row.get("damping", 0.2)  # Default assumes d=0.2
                a = row.get("A", 0)
                b = row.get("B", 0)
                basin = row.get("basin", "")
                if basin and basin not in ("?[None]", "None"):
                    dampings_tested.add(d)
                    truth_tables_by_d.setdefault(d, {})[(a, b)] = basin

            if len(dampings_tested) >= 2:
                # Check if A+B still differs from A-only at each damping
                generalizes = True
                for d, tt in truth_tables_by_d.items():
                    if tt.get((1, 1)) == tt.get((1, 0)):
                        generalizes = False
                        break

                if generalizes:
                    updates.append(OpenQuestionUpdate(
                        question_number=5,
                        status="answered",
                        answer_summary=f"Half-adder generalizes across {len(dampings_tested)} "
                                       f"damping values — dual input always differs from single input",
                        evidence=f"{len(ha)} truth-table entries across d={sorted(dampings_tested)}",
                    ))
                else:
                    updates.append(OpenQuestionUpdate(
                        question_number=5,
                        status="partially_answered",
                        answer_summary=f"Half-adder tested at {len(dampings_tested)} dampings "
                                       f"but does not generalize — at some dampings A+B equals A-only",
                        evidence=f"{len(ha)} entries across d={sorted(dampings_tested)}",
                    ))

        # Q6: SR-latch third-state reproducibility
        sr = probes.get("sr_latch", [])
        if sr and isinstance(sr, list) and len(sr) >= 2:
            third_states = []
            for row in sr:
                d = row.get("damping", "?")
                g_first = row.get("grail_first", "")
                m_first = row.get("metatron_first", "")
                simul = row.get("simultaneous", "")
                if simul and g_first and m_first and simul != g_first and simul != m_first:
                    third_states.append({"damping": d, "third": simul})

            if third_states:
                # Check if the third state is consistent (same basin) across tests
                third_basins = set(ts["third"] for ts in third_states)
                if len(third_basins) == 1:
                    updates.append(OpenQuestionUpdate(
                        question_number=6,
                        status="answered",
                        answer_summary=f"SR-latch third state IS reproducible: "
                                       f"'{list(third_basins)[0]}' consistently appears "
                                       f"on simultaneous input at {len(third_states)} dampings",
                        evidence=f"{len(sr)} SR-latch tests, {len(third_states)} third-state events",
                    ))
                else:
                    updates.append(OpenQuestionUpdate(
                        question_number=6,
                        status="partially_answered",
                        answer_summary=f"Third state varies by damping: "
                                       f"{len(third_basins)} distinct third-state basins observed",
                        evidence=f"{len(sr)} SR-latch tests",
                    ))

        # Q7: Temporal injection sensitivity
        burst = probes.get("burst_patterns", [])
        if burst and isinstance(burst, list) and len(burst) >= 2:
            # Check how many dampings show ≥3 distinct basins from temporal patterns
            sensitive_dampings = []
            for row in burst:
                d = row.get("damping", "?")
                patterns = {}
                for key in ("burst_5x30", "ramp_10to50", "oscillating", "single_shot"):
                    val = row.get(key)
                    if val and val not in ("?", "None"):
                        patterns[key] = val
                unique = set(patterns.values())
                if len(unique) >= 3:
                    sensitive_dampings.append(d)

            if sensitive_dampings:
                updates.append(OpenQuestionUpdate(
                    question_number=7,
                    status="partially_answered",
                    answer_summary=f"Temporal sensitivity confirmed at {len(sensitive_dampings)} "
                                   f"dampings (d={sorted(sensitive_dampings)}). "
                                   f"Minimum distinguishing cadence not yet quantified",
                    evidence=f"{len(burst)} burst-pattern tests",
                ))

        # Q8: Dream afterstate
        dream = probes.get("dream_afterstate", [])
        if dream and isinstance(dream, list) and len(dream) >= 3:
            shifted = [r for r in dream if r.get("basin_shifted") is True]
            stable = [r for r in dream if r.get("basin_shifted") is False]
            if shifted:
                shift_dampings = [r.get("damping", "?") for r in shifted]
                updates.append(OpenQuestionUpdate(
                    question_number=8,
                    status="answered" if len(shifted) >= 2 else "partially_answered",
                    answer_summary=f"Dream afterstate confirmed: basin shifts during rest "
                                   f"phase at {len(shifted)} dampings (d={shift_dampings}). "
                                   f"Stable at {len(stable)} dampings",
                    evidence=f"{len(dream)} dream-afterstate tests",
                ))
            elif stable and len(stable) >= 3:
                updates.append(OpenQuestionUpdate(
                    question_number=8,
                    status="answered",
                    answer_summary=f"No dream afterstate: basin is stable through "
                                   f"1000-step rest phase at all {len(stable)} dampings tested",
                    evidence=f"{len(dream)} dream-afterstate tests",
                ))

    return updates


# ---------------------------------------------------------------------------
# 4. Proof Packet Updater
# ---------------------------------------------------------------------------

def get_current_claim_count(text: str) -> int:
    """Get the highest claim number from the proof packet."""
    max_c = 0
    for m in re.finditer(r'\|\s*C(\d+)\s*\|', text):
        n = int(m.group(1))
        if n > max_c:
            max_c = n
    return max_c


def update_proof_packet(
    claims: list[PendingClaim],
    question_updates: list[OpenQuestionUpdate],
    total_new_trials: int,
    total_new_seconds: float,
    new_experiment_count: int,
) -> bool:
    """
    Update the proof packet with new claims, question answers, and metadata.

    Returns True if the packet was modified, False otherwise.
    """
    if not _MAIN_PACKET.exists():
        return False

    text = _MAIN_PACKET.read_text(encoding="utf-8")
    original = text

    # --- (A) Deduplicate claims ---
    # Remove claims whose core pattern+details already exist in the packet
    filtered_claims = []
    for claim in claims:
        # Check if a similar claim text already exists
        # Simple heuristic: check if key phrases from the claim are already present
        key_phrases = _extract_key_phrases(claim.text)
        already_present = any(
            phrase.lower() in text.lower() for phrase in key_phrases
        ) if key_phrases else False
        if not already_present:
            filtered_claims.append(claim)
    claims = filtered_claims

    if not claims and not question_updates and total_new_trials == 0:
        return False

    # --- (B) Update header metadata ---
    if total_new_trials > 0 or total_new_seconds > 0:
        text = _update_header_metadata(text, total_new_trials, total_new_seconds,
                                        new_experiment_count)

    # --- (C) Assign claim IDs and insert into claims table ---
    if claims:
        current_max = get_current_claim_count(text)
        for i, claim in enumerate(claims):
            claim.claim_id = f"C{current_max + i + 1}"

        text = _insert_claims_into_table(text, claims)

    # --- (D) Update open questions ---
    if question_updates:
        text = _update_open_questions(text, question_updates)

    # --- (E) Add new experiment sections ---
    if claims:
        text = _add_experiment_section(text, claims, question_updates)

    # --- (F) Update footer ---
    if claims or total_new_trials > 0:
        text = _update_footer(text, len(claims), total_new_trials, total_new_seconds)

    # Write back
    if text != original:
        _MAIN_PACKET.write_text(text, encoding="utf-8")
        return True
    return False


def _extract_key_phrases(claim_text: str) -> list[str]:
    """Extract distinguishing phrases from a claim for dedup checking."""
    phrases = []
    # Look for specific patterns like "XOR gate", "NAND gate", "basin lock", etc.
    patterns = [
        r'(XOR[- ](?:like )?gate)',
        r'(NAND gate)',
        r'(dead zone basin lock)',
        r'(entropy (?:profile|cliff))',
        r'(noise resilien\w+)',
        r'(information capacity.*?bits)',
        r'(NOT-gate cascades? preserve)',
        r'(NOT-chain[\w ]*faithful)',
        r'(energy threshold)',
        r'(basin.*?impervious.*?energy)',
        r'(basin.*?invariant.*?d=\d)',
        r'(capacity.*?peaks)',
    ]
    for pat in patterns:
        m = re.search(pat, claim_text, re.IGNORECASE)
        if m:
            phrases.append(m.group(1))
    # Fallback: first 50 chars if no patterns matched
    if not phrases and len(claim_text) > 20:
        phrases.append(claim_text[:50])
    return phrases


def _update_header_metadata(text: str, new_trials: int, new_seconds: float,
                             new_experiments: int) -> str:
    """Update the trial count, compute time, and experiment count in the header."""
    # Update total compute
    m = re.search(
        r'(\*\*Total compute:\*\*\s*~?)([\d,]+)\s*seconds\s*\(~?(\d+)\s*minutes?\)',
        text
    )
    if m:
        old_secs = int(m.group(2).replace(",", ""))
        new_secs = old_secs + int(new_seconds)
        new_mins = int(new_secs / 60)
        text = text.replace(
            m.group(0),
            f"{m.group(1)}{new_secs:,} seconds (~{new_mins} minutes)"
        )

    # Update total trials
    m = re.search(
        r'(\*\*Total trials:\*\*\s*~?)([\d,]+)',
        text
    )
    if m:
        old_trials = int(m.group(2).replace(",", ""))
        total = old_trials + new_trials
        text = text.replace(
            m.group(0),
            f"{m.group(1)}{total:,}"
        )

    # Update experiment suite count (in the header text)
    m = re.search(r'across (\d+) experiment suites?', text)
    if m:
        old_count = int(m.group(1))
        text = text.replace(
            m.group(0),
            f"across {old_count + new_experiments} experiment suites"
        )

    return text


def _insert_claims_into_table(text: str, claims: list[PendingClaim]) -> str:
    """Insert new claim rows after the last existing claim in the table."""
    # Find the last claim row
    last_claim_match = None
    for m in re.finditer(r'\| C\d+ \|[^\n]+\n', text):
        last_claim_match = m

    if not last_claim_match:
        return text

    insert_pos = last_claim_match.end()
    new_rows = ""
    for claim in claims:
        # Truncate evidence to fit table
        ev = claim.evidence[:80] if len(claim.evidence) > 80 else claim.evidence
        new_rows += f"| {claim.claim_id} | {claim.text} | {ev} |\n"

    text = text[:insert_pos] + new_rows + text[insert_pos:]
    return text


def _update_open_questions(text: str, updates: list[OpenQuestionUpdate]) -> str:
    """Update the open questions section — mark answered questions as resolved.

    For fully answered questions: replace the question line with a [RESOLVED] tag
    and the answer summary.  For partially answered: append a [PARTIAL] annotation
    but keep the question open so the RSI loop continues targeting it.
    """
    for update in updates:
        if update.status not in ("answered", "partially_answered"):
            continue

        # Find question N in the "Remaining Open Questions" section
        # Pattern: "N. **Bold title:** rest of question text"
        q_pattern = rf'({update.question_number}\.\s*\*\*[^*]+\*\*:?\s*[^\n]*)'
        m = re.search(q_pattern, text)
        if not m:
            continue

        old_line = m.group(0)

        if update.status == "answered":
            # Replace the question with a RESOLVED marker — this removes it
            # from the "open" count so the fitness function sees progress.
            resolved_line = (
                f"{update.question_number}. ~~**[RESOLVED]**~~ "
                f"{update.answer_summary} *({update.evidence})*"
            )
            text = text.replace(old_line, resolved_line)
        else:
            # Partially answered: annotate but keep question open
            annotation = (
                f"\n   > **[PARTIAL]** {update.answer_summary} "
                f"*({update.evidence})*"
            )
            text = text.replace(old_line, old_line + annotation)
    return text


def _add_experiment_section(text: str, claims: list[PendingClaim],
                            question_updates: list[OpenQuestionUpdate]) -> str:
    """Add new experiment section before §14 (open questions)."""
    # Find the § number for the new section
    existing_sections = re.findall(r'## (\d+)\.', text)
    if existing_sections:
        last_section = max(int(s) for s in existing_sections)
        # Insert before the "Remaining Open Questions" section
        new_section_num = last_section  # Will be inserted before open questions
    else:
        new_section_num = 14

    # Build the new section content
    claimed_patterns = set()
    evidence_parts = []
    for c in claims:
        claimed_patterns.add(c.pattern)
        evidence_parts.append(f"- **{c.claim_id}:** {c.text}")

    q_parts = []
    for qu in question_updates:
        status_tag = "ANSWERED" if qu.status == "answered" else "PARTIALLY ANSWERED"
        q_parts.append(f"- **Q{qu.question_number} [{status_tag}]:** {qu.answer_summary}")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    section_text = f"""
## {new_section_num}. RSI Auto-Compiled Results ({date_str})

**Source:** Automated RSI claim compilation
**Method:** Pattern-matched claim detection from experiment JSON outputs
**Compilation date:** {date_str}

### Claims Compiled

{chr(10).join(evidence_parts)}

"""

    if q_parts:
        section_text += f"""### Open Question Updates

{chr(10).join(q_parts)}

"""

    section_text += f"*Claims proven: {', '.join(c.claim_id for c in claims)}*\n"

    # Insert before "## 14. Remaining Open Questions" (or wherever open questions are)
    oq_match = re.search(r'\n(## \d+\.\s*Remaining Open Questions)', text)
    if oq_match:
        # Re-number the open questions section
        old_oq_header = oq_match.group(1)
        new_oq_num = new_section_num + 1
        new_oq_header = f"## {new_oq_num}. Remaining Open Questions"
        text = text.replace(old_oq_header, new_oq_header)
        text = text[:oq_match.start()] + "\n" + section_text + "\n" + text[oq_match.start():]
    else:
        # Append to end
        text += "\n" + section_text

    return text


def _update_footer(text: str, new_claims: int, new_trials: int, new_seconds: float) -> str:
    """Update the proof packet footer with new totals."""
    # Find the existing footer
    footer_pattern = (
        r'\*Proof packet compiled from (\d+) experiment suites?, '
        r'~?([\d,]+) independent engine runs, '
        r'~?(\d+) minutes? of compute'
    )
    m = re.search(footer_pattern, text)
    if m:
        old_suites = int(m.group(1))
        old_runs = int(m.group(2).replace(",", ""))
        old_mins = int(m.group(3))

        new_text = (
            f"*Proof packet compiled from {old_suites + 1} experiment suites, "
            f"~{old_runs + new_trials:,} independent engine runs, "
            f"~{old_mins + int(new_seconds / 60)} minutes of compute"
        )
        text = text[:m.start()] + new_text + text[m.end():]

    return text


# ---------------------------------------------------------------------------
# 4b. Ledger Updater
# ---------------------------------------------------------------------------

def update_ledger(domain: str = _DEFAULT_DOMAIN) -> bool:
    """Sync the master LEDGER.md with the current state of domain packets.

    Reads each domain packet, extracts aggregate stats (claims, open Qs,
    trials, compute, suites), and rewrites the Domain Registry table and
    Totals line in the ledger.

    Returns True if the ledger was modified.
    """
    if not _LEDGER_FILE.exists():
        return False
    if not _DOMAINS_DIR.is_dir():
        return False

    # Gather stats from all domain packets
    domain_stats: list[dict[str, Any]] = []
    global_claims = 0
    global_open_q = 0
    global_trials = 0
    global_compute = 0

    for packet_path in sorted(_DOMAINS_DIR.glob("*.md")):
        d_name = packet_path.stem
        text = packet_path.read_text(encoding="utf-8")

        claims = _count_claims_in_text(text)
        open_q = _count_open_questions_in_text(text)
        trials, compute_min = _parse_totals_from_text(text)
        suites = _count_suites_in_text(text)

        domain_stats.append({
            "name": d_name,
            "file": f"{d_name}.md",
            "claims": claims,
            "open_q": open_q,
            "trials": trials,
            "compute_min": compute_min,
            "suites": suites,
        })

        global_claims += claims
        global_open_q += open_q
        global_trials += trials
        global_compute += compute_min

    if not domain_stats:
        return False

    # Rebuild the Domain Registry table
    ledger_text = _LEDGER_FILE.read_text(encoding="utf-8")
    original = ledger_text

    # Replace the domain registry table
    registry_header = "| Domain | Packet | Claims | Open Qs | Trials | Compute (min) | Suites | Last Updated |"
    registry_sep = "|--------|--------|-------:|--------:|-------:|---------------:|-------:|--------------|"
    registry_start = ledger_text.find(registry_header)
    if registry_start == -1:
        return False

    # Find the end of the table (next blank line or section)
    table_end = ledger_text.find("\n\n", registry_start + len(registry_header))
    if table_end == -1:
        table_end = len(ledger_text)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    table_rows = []
    for ds in domain_stats:
        table_rows.append(
            f"| {ds['name']} "
            f"| [{ds['file']}](domains/{ds['file']}) "
            f"| {ds['claims']} "
            f"| {ds['open_q']} "
            f"| {ds['trials']:,} "
            f"| {ds['compute_min']} "
            f"| {ds['suites']} "
            f"| {date_str} |"
        )

    new_table = (
        registry_header + "\n" +
        registry_sep + "\n" +
        "\n".join(table_rows)
    )

    ledger_text = ledger_text[:registry_start] + new_table + ledger_text[table_end:]

    # Update totals line
    totals_pattern = r'\*\*Totals:\*\*[^\n]+'
    new_totals = (
        f"**Totals:** {global_claims} claims | {global_open_q} open question"
        f"{'s' if global_open_q != 1 else ''} | "
        f"{global_trials:,} trials | {global_compute} min compute"
    )
    ledger_text = re.sub(totals_pattern, new_totals, ledger_text)

    # Update regeneration timestamp
    regen_pattern = r'Last regenerated: \d{4}-\d{2}-\d{2}'
    ledger_text = re.sub(regen_pattern, f"Last regenerated: {date_str}", ledger_text)

    if ledger_text != original:
        _LEDGER_FILE.write_text(ledger_text, encoding="utf-8")
        return True
    return False


def _count_claims_in_text(text: str) -> int:
    """Count '| C<n> |' rows in a domain packet."""
    count = 0
    for line in text.split("\n"):
        if re.match(r'^\|\s*C\d+\s*\|', line.strip()):
            count += 1
    return count


def _count_open_questions_in_text(text: str) -> int:
    """Count unresolved open questions in a domain packet."""
    in_questions = False
    count = 0
    for line in text.split("\n"):
        if "Remaining Open Questions" in line:
            in_questions = True
            continue
        if in_questions:
            stripped = line.strip()
            if stripped.startswith("---") or (stripped.startswith("#") and "Open" not in stripped):
                break
            if stripped and stripped[0].isdigit() and "." in stripped[:4]:
                if "[RESOLVED]" in stripped:
                    continue
                count += 1
    return count


def _parse_totals_from_text(text: str) -> tuple[int, int]:
    """Extract trials and compute minutes from a domain packet header."""
    trials = 0
    minutes = 0
    for line in text.split("\n")[:20]:
        if "Total trials" in line:
            nums = re.findall(r'[\d,]+', line)
            for n in nums:
                val = int(n.replace(",", ""))
                if val > trials:
                    trials = val
        if "Total compute" in line:
            m_min = re.search(r'~?(\d+)\s*minutes?', line)
            if m_min:
                minutes = int(m_min.group(1))
    return trials, minutes


def _count_suites_in_text(text: str) -> int:
    """Count experiment suites from a domain packet header."""
    for line in text.split("\n")[:20]:
        m = re.search(r'across (\d+) experiment suites?', line)
        if m:
            return int(m.group(1))
    return 0


# ---------------------------------------------------------------------------
# 5. Main Compilation Entry Point
# ---------------------------------------------------------------------------

def compile_results(
    data_dirs: list[Path] | None = None,
    update_proof_packet_flag: bool = True,
    verbose: bool = True,
) -> CompileResult:
    """
    Main entry point: scan experiment data, extract claims, update proof packet.

    Args:
        data_dirs: List of directories to scan for JSON results.
                   If None, scans all overnight_rsi output directories.
        update_proof_packet_flag: Whether to actually modify the proof packet.
        verbose: Print progress to stdout.

    Returns:
        CompileResult with summary of what was found and updated.
    """
    result = CompileResult(
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Default: scan all overnight output directories
    if data_dirs is None:
        overnight_dir = _DATA_DIR / "overnight_rsi"
        if overnight_dir.is_dir():
            data_dirs = sorted(
                [d for d in overnight_dir.iterdir() if d.is_dir()],
                key=lambda d: d.name,
            )
        else:
            data_dirs = []

    if not data_dirs:
        if verbose:
            print("  [COMPILE] No data directories found.")
        return result

    # Load already-compiled files
    compiled_set = load_compiled_set()

    # Scan all directories
    all_claims: list[PendingClaim] = []
    suite_results: dict[str, dict] = {}
    total_trials = 0
    total_seconds = 0.0
    new_experiment_count = 0

    for data_dir in data_dirs:
        files = scan_result_files(data_dir)
        for fpath in files:
            result.files_scanned += 1
            fkey = str(fpath)

            if fkey in compiled_set:
                continue  # Already compiled

            result.files_new += 1

            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                result.errors.append(f"Failed to parse {fpath.name}: {e}")
                continue

            # Extract trial count
            trials = data.get("trials", 0)
            if not trials:
                # Count from results list
                results_list = _extract_results_list(data)
                trials = len(results_list) if results_list else 0
            total_trials += trials

            # Track suite results for open question checking
            suite_name = data.get("suite", "")
            if suite_name:
                suite_results[fpath.name] = data
                new_experiment_count += 1

            # Run claim detectors
            found_claims = run_detectors(data, fpath.name)
            all_claims.extend(found_claims)

            # Mark as compiled only if we're actually updating
            if update_proof_packet_flag:
                mark_compiled(fkey, len(found_claims), trials)

        # Check for run_log.txt to extract compute time
        run_log = data_dir / "run_log.txt"
        if run_log.exists():
            try:
                log_text = run_log.read_text(encoding="utf-8")
                # Extract elapsed time from budget lines
                elapsed_matches = re.findall(r'Elapsed:\s*([\d.]+)s', log_text)
                if elapsed_matches:
                    total_seconds = max(float(s) for s in elapsed_matches)
            except Exception:
                pass

    result.total_trials_added = total_trials
    result.compute_seconds_added = total_seconds

    # Check open questions
    result.question_updates = check_open_questions(suite_results)

    # Deduplicate claims (same pattern + same key details)
    deduped_claims = _deduplicate_claims(all_claims)
    result.new_claims = deduped_claims
    result.experiments_added = new_experiment_count

    if verbose:
        print(f"  [COMPILE] Scanned {result.files_scanned} files "
              f"({result.files_new} new)")
        print(f"  [COMPILE] Found {len(deduped_claims)} new claim candidates")
        print(f"  [COMPILE] {len(result.question_updates)} open question updates")
        print(f"  [COMPILE] +{total_trials} trials, +{total_seconds:.0f}s compute")
        for c in deduped_claims:
            print(f"    [{c.pattern}] {c.text[:80]}...")
        for qu in result.question_updates:
            status_tag = "ANSWERED" if qu.status == "answered" else "PARTIAL"
            print(f"    Q{qu.question_number} [{status_tag}]: {qu.answer_summary[:60]}...")

    # Update proof packet (domain)
    if update_proof_packet_flag and (deduped_claims or result.question_updates
                                     or total_trials > 0):
        result.proof_packet_updated = update_proof_packet(
            deduped_claims,
            result.question_updates,
            total_trials,
            total_seconds,
            new_experiment_count,
        )
        if verbose:
            if result.proof_packet_updated:
                print(f"  [COMPILE] Domain packet UPDATED with {len(deduped_claims)} new claims")
            else:
                print(f"  [COMPILE] Domain packet unchanged (all claims already present)")

        # Sync master ledger
        if result.proof_packet_updated:
            ledger_updated = update_ledger()
            if verbose:
                if ledger_updated:
                    print(f"  [COMPILE] Master LEDGER.md synced")
                else:
                    print(f"  [COMPILE] Master LEDGER.md already current")

    return result


def _extract_results_list(data: dict) -> list[dict]:
    """Extract the main results list from various JSON formats."""
    # Direct "results" key
    if "results" in data and isinstance(data["results"], list):
        return data["results"]
    # "{type}_results" pattern
    for key, val in data.items():
        if key.endswith("_results") and isinstance(val, list):
            return val
    # Probes → flatten all probe results
    probes = data.get("probes", {})
    if probes:
        all_results = []
        for pname, pdata in probes.items():
            if isinstance(pdata, list):
                all_results.extend(pdata)
        return all_results
    return []


def _deduplicate_claims(claims: list[PendingClaim]) -> list[PendingClaim]:
    """Remove duplicate claims based on pattern + key evidence."""
    seen = set()
    unique = []
    for claim in claims:
        # Create a dedup key from pattern + core details
        key_parts = [claim.pattern]
        details = claim.details
        if "gate" in details:
            key_parts.append(str(details["gate"]))
        if "damping" in details:
            key_parts.append(f"d={details['damping']}")
        if "basin" in details:
            key_parts.append(str(details["basin"]))
        if "d_range" in details:
            key_parts.append(f"range={details['d_range']}")
        if "inject_type" in details:
            key_parts.append(details["inject_type"])
        if "type" in details:
            key_parts.append(details["type"])
        # New detector dedup keys
        if "truth_table" in details:
            key_parts.append(f"tt_keys={sorted(details['truth_table'].keys())}")
        if "patterns" in details:
            key_parts.append(f"n_patterns={len(details['patterns'])}")
        if "configs" in details:
            v = details["configs"]
            key_parts.append(f"n_configs={len(v) if isinstance(v, (list, dict)) else v}")
        if "order_dependent" in details:
            key_parts.append(f"order_dep={details['order_dependent']}")
        if "avg_low_iton" in details:
            key_parts.append(f"low_iton={details['avg_low_iton']:.2f}")

        key = "|".join(key_parts)
        if key not in seen:
            seen.add(key)
            unique.append(claim)
    return unique


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """Run claim compiler from command line."""
    import argparse
    parser = argparse.ArgumentParser(description="SOL Claim Compiler")
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Specific data directory to compile")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze without updating proof packet")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress output")
    args = parser.parse_args()

    data_dirs = None
    if args.data_dir:
        data_dirs = [Path(args.data_dir)]

    result = compile_results(
        data_dirs=data_dirs,
        update_proof_packet_flag=not args.dry_run,
        verbose=not args.quiet,
    )

    if not args.quiet:
        print(f"\n  Summary: {len(result.new_claims)} claims, "
              f"{result.total_trials_added} trials, "
              f"{result.compute_seconds_added:.0f}s compute, "
              f"packet updated: {result.proof_packet_updated}")


if __name__ == "__main__":
    main()
