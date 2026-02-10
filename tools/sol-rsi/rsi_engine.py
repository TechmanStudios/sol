#!/usr/bin/env python3
"""
SOL Recursive Self-Improvement (RSI) Engine
=============================================

Outer-loop controller that wraps the existing cortex/evolve/hippocampus
inner loop with a genuine recursive self-improvement cycle:

    EVALUATE -> REFLECT -> MUTATE -> PLAN -> EXECUTE -> COMMIT -> repeat

What makes this RSI (not just automation):
  1. FITNESS FUNCTION — computable measure of "how well do we understand
     the SOL engine?" (claim count, parameter coverage, open questions,
     experiment productivity).
  2. SELF-EVALUATION — after each cycle, compute fitness delta and identify
     which experiment types produced the most knowledge gain.
  3. STRATEGY MUTATION — adjust the genome (template weights, parameter
     ranges, probe types, scope) based on what worked.
  4. SCOPE EXPANSION — propose novel experiment categories that the system
     hasn't yet attempted.
  5. THREE EXECUTION MODES:
       interactive — human-in-the-loop (current workflow)
       cron        — GitHub Actions nightly/weekly
       persistent  — continuous loop on local/server machine

The existing cortex/orchestrator is the INNER loop.
This RSI engine is the OUTER loop that improves the inner loop.

Usage:
    # Interactive mode (prints plan, waits for approval)
    python rsi_engine.py --mode interactive --cycles 1

    # Cron mode (GitHub Actions, unattended, single cycle)
    python rsi_engine.py --mode cron --cycles 1

    # Persistent mode (continuous loop until budget exhausted)
    python rsi_engine.py --mode persistent --cycles 10 --budget-hours 8

    # Dry run (evaluate + reflect only, no execution)
    python rsi_engine.py --dry-run

    # Status report
    python rsi_engine.py --status
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Gen-2 frontier experiment types — injected when original frontier is exhausted
_GEN2_FRONTIER_TYPES = [
    "multi_damping_sweep",      # Simultaneous multi-zone exploration
    "phase_space_mapping",      # Grid search over damping × injection energy
    "perturbation_analysis",    # Small perturbations from known basins
    "symmetry_breaking",        # Asymmetric injection patterns
    "resonance_hunting",        # Fine-grained sweep for transition points
    "boundary_cartography",     # Map boundaries between basins precisely
    "stochastic_injection",     # Random injection amounts/targets
]

# Lazy import for claim compiler (same package)
def _get_compiler():
    from claim_compiler import compile_results
    return compile_results

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_SOL_ROOT = _THIS_DIR.parent.parent
_DATA_DIR = _SOL_ROOT / "data"
_RSI_DIR = _DATA_DIR / "rsi"
_FITNESS_LOG = _RSI_DIR / "fitness_ledger.jsonl"
_GENOME_FILE = _RSI_DIR / "strategy_genome.json"
_CYCLE_LOG = _RSI_DIR / "cycle_log.jsonl"
_PROOF_PACKETS_DIR = _SOL_ROOT / "solKnowledge" / "proof_packets"
_DOMAINS_DIR = _PROOF_PACKETS_DIR / "domains"
_RAW_PACKETS_DIR = _PROOF_PACKETS_DIR / "raw"

# Tool paths (for inner-loop integration)
_CORE_DIR = _SOL_ROOT / "tools" / "sol-core"
_CORTEX_DIR = _SOL_ROOT / "tools" / "sol-cortex"
_HIPPO_DIR = _SOL_ROOT / "tools" / "sol-hippocampus"
_EVOLVE_DIR = _SOL_ROOT / "tools" / "sol-evolve"
_ORCHESTRATOR_DIR = _SOL_ROOT / "tools" / "sol-orchestrator"


# ===================================================================
# 1. FITNESS FUNCTION
# ===================================================================
# Computable measure of knowledge quality and research progress.
# Score is a weighted sum of:
#   - claim_count:        number of proven claims
#   - open_questions:     number remaining (lower = better)
#   - experiment_count:   total experiment suites
#   - parameter_coverage: fraction of known parameter space explored
#   - trial_count:        total independent engine runs
#   - claim_strength:     average evidence quality per claim
# ===================================================================

@dataclass
class FitnessScore:
    """Quantified knowledge state."""
    timestamp: str = ""
    cycle_id: int = 0

    # Raw metrics
    claim_count: int = 0
    open_questions: int = 0
    experiment_count: int = 0
    trial_count: int = 0
    proof_packet_count: int = 0
    compute_minutes: float = 0.0

    # Derived scores (0.0 - 1.0 each, higher = better)
    claim_density: float = 0.0       # claims per experiment
    question_ratio: float = 0.0      # 1 - (open / (open + closed))
    coverage_score: float = 0.0      # parameter space coverage
    productivity: float = 0.0        # claims per compute-minute

    # Composite fitness (weighted sum, 0-100 scale)
    fitness: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# Fitness weights (tunable via genome)
DEFAULT_FITNESS_WEIGHTS = {
    "claim_density": 0.25,    # Reward insight-dense experiments
    "question_ratio": 0.25,   # Reward closing open questions
    "coverage_score": 0.25,   # Reward exploring new parameter space
    "productivity": 0.25,     # Reward compute efficiency
}


def evaluate_fitness(cycle_id: int = 0) -> FitnessScore:
    """
    Scan the knowledge base and compute current fitness score.

    Reads proof packets, counts claims/questions/experiments, and
    computes a composite fitness score.
    """
    score = FitnessScore(
        timestamp=datetime.now(timezone.utc).isoformat(),
        cycle_id=cycle_id,
    )

    # --- Scan proof packets ---
    if _PROOF_PACKETS_DIR.is_dir():
        packets = list(_PROOF_PACKETS_DIR.glob("*.md"))
        score.proof_packet_count = len(packets)

        # Parse all domain packets for claims, questions, experiments
        if _DOMAINS_DIR.is_dir():
            for domain_packet in sorted(_DOMAINS_DIR.glob("*.md")):
                try:
                    text = domain_packet.read_text(encoding="utf-8")
                    score.claim_count += _count_claims(text)
                    score.open_questions += _count_open_questions(text)
                    score.experiment_count += _count_experiments(text)
                    trials, compute = _parse_totals(text)
                    score.trial_count += trials
                    score.compute_minutes += compute
                except Exception:
                    pass

        # Count claims in raw (pre-domain) packets too
        raw_dir = _RAW_PACKETS_DIR if _RAW_PACKETS_DIR.is_dir() else _PROOF_PACKETS_DIR
        for packet in (raw_dir.glob("PP-*.md") if raw_dir.is_dir() else []):
            try:
                ptxt = packet.read_text(encoding="utf-8")
                # Cortex packets use "Claim:" prefix
                claim_lines = [l for l in ptxt.split("\n")
                               if l.strip().startswith("**Claim")]
                score.claim_count += len(claim_lines)
            except Exception:
                pass

    # --- Compute derived scores ---
    if score.experiment_count > 0:
        score.claim_density = min(1.0, score.claim_count / (score.experiment_count * 3))

    total_closeable = score.claim_count + score.open_questions
    if total_closeable > 0:
        score.question_ratio = score.claim_count / total_closeable

    # Parameter coverage: estimate based on known parameter dimensions
    # Dimensions: damping (0-84), c_press, w0 configs, injection protocols,
    # topology (surgery), spectral, logic gates, ISA, clock, cascade
    KNOWN_DIMENSIONS = 12
    score.coverage_score = min(1.0, score.experiment_count / KNOWN_DIMENSIONS)

    if score.compute_minutes > 0:
        # Claims per compute-minute (normalized to [0,1])
        raw_prod = score.claim_count / score.compute_minutes
        score.productivity = min(1.0, raw_prod / 0.5)  # 0.5 claims/min = perfect

    # --- Composite fitness (0-100 scale) ---
    weights = _load_genome().get("fitness_weights", DEFAULT_FITNESS_WEIGHTS)
    score.fitness = 100.0 * (
        weights.get("claim_density", 0.25) * score.claim_density +
        weights.get("question_ratio", 0.25) * score.question_ratio +
        weights.get("coverage_score", 0.25) * score.coverage_score +
        weights.get("productivity", 0.25) * score.productivity
    )

    return score


def _count_claims(text: str) -> int:
    """Count '| C<n> |' rows in the claims table."""
    import re
    count = 0
    for line in text.split("\n"):
        stripped = line.strip()
        # Match lines like "| C1 | ..." or "| C22 | ..."
        if re.match(r'^\|\s*C\d+\s*\|', stripped):
            count += 1
    return count


def _count_open_questions(text: str) -> int:
    """Count numbered items under 'Remaining Open Questions' that are NOT resolved.

    Questions marked with ~~**[RESOLVED]**~~ are excluded from the count.
    This lets the fitness function see real progress when the claim compiler
    closes open questions.
    """
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
                # Skip resolved questions
                if "[RESOLVED]" in stripped:
                    continue
                count += 1
    return count


def _count_experiments(text: str) -> int:
    """Count 'Experiment N' sections."""
    count = 0
    for line in text.split("\n"):
        if "## " in line and "Experiment" in line:
            count += 1
    return count


def _parse_totals(text: str) -> tuple[int, float]:
    """Extract total trials and compute minutes from the document header."""
    import re
    trials = 0
    minutes = 0.0
    # Only scan the first 20 lines (header block)
    header_lines = text.split("\n")[:20]
    for line in header_lines:
        # Match "**Total trials:** ~2,837 independent engine runs"
        if "Total trials" in line:
            nums = re.findall(r'[\d,]+', line)
            for n in nums:
                val = int(n.replace(",", ""))
                if val > 100:  # Plausible trial count
                    trials = max(trials, val)
        # Match "**Total compute:** ~7,644 seconds (~127 minutes)"
        if "Total compute" in line and "minute" in line:
            m = re.search(r'~?(\d+)\s*minutes?\b', line)
            if m:
                minutes = float(m.group(1))
    return trials, minutes


# ===================================================================
# 2. STRATEGY GENOME
# ===================================================================
# The genome encodes the current research strategy as a mutable
# JSON document. It evolves across RSI cycles.
#
# Fields:
#   - fitness_weights: how to weight fitness components
#   - template_preferences: which hypothesis templates to prioritize
#   - parameter_focus: which parameter ranges to explore next
#   - experiment_types: enabled experiment categories
#   - scope_frontier: categories not yet attempted
#   - mutation_rate: how aggressively to change strategy
#   - history: list of mutations applied
# ===================================================================

DEFAULT_GENOME = {
    "version": 1,
    "created": "",
    "last_cycle": 0,

    "fitness_weights": DEFAULT_FITNESS_WEIGHTS,

    "template_preferences": {
        "parameter_sweep": 1.0,
        "replication": 0.5,
        "topology_surgery": 0.8,
        "injection_protocol": 0.9,
        "logic_gate": 1.0,
        "clock_signal": 0.8,
        "cascade_pipeline": 0.7,
        "isa_program": 0.6,
        "analog_fidelity": 0.5,
    },

    "parameter_focus": {
        "damping_range": [0.0, 84.0],
        "damping_priority_zones": [
            {"range": [0.0, 10.0], "priority": 0.5, "note": "well-explored turbulent regime"},
            {"range": [10.0, 15.0], "priority": 0.9, "note": "transition zone"},
            {"range": [15.0, 40.0], "priority": 1.0, "note": "dead zone — poorly understood"},
            {"range": [40.0, 55.0], "priority": 0.8, "note": "re-activation zone"},
            {"range": [55.0, 84.0], "priority": 0.7, "note": "extinction approach"},
        ],
        "w0_range": [0.1, 100.0],
        "injection_energy_range": [1.0, 500.0],
    },

    "experiment_types": {
        "enabled": [
            "parameter_sweep",
            "topology_surgery",
            "injection_protocol",
            "logic_gate",
            "clock_signal",
            "cascade",
            "isa_program",
            "hardware_validation",
        ],
        "scope_frontier": [
            "information_theoretic",
            "multi_engine_coupling",
            "adaptive_damping",
            "graph_evolution",
            "temporal_encoding",
            "error_correction",
            "capacity_measurement",
        ],
    },

    "mutation_rate": 0.15,  # Fraction of genome parameters to mutate per cycle
    "exploration_rate": 0.2,  # Probability of trying a frontier experiment

    "history": [],
}


def _load_genome() -> dict:
    """Load the current strategy genome, or create default."""
    if _GENOME_FILE.exists():
        with open(_GENOME_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_GENOME.copy()


def _save_genome(genome: dict):
    """Persist the strategy genome."""
    _RSI_DIR.mkdir(parents=True, exist_ok=True)
    with open(_GENOME_FILE, "w", encoding="utf-8") as f:
        json.dump(genome, f, indent=2)


# ===================================================================
# 3. REFLECTION ENGINE
# ===================================================================
# After each cycle, analyze what happened and generate insights:
#   - Which experiment types were most productive?
#   - Which parameter zones yielded most claims?
#   - What is the fitness trend over the last N cycles?
#   - Are we plateauing? (fitness delta < threshold)
# ===================================================================

@dataclass
class ReflectionReport:
    """Analysis of the last RSI cycle (or recent history)."""
    cycle_id: int = 0
    fitness_current: float = 0.0
    fitness_previous: float = 0.0
    fitness_delta: float = 0.0
    is_improving: bool = False
    is_plateauing: bool = False  # delta < 1.0 for 3+ cycles

    # Per-category productivity (claims produced per category in recent cycles)
    category_productivity: dict[str, float] = field(default_factory=dict)

    # Recommended strategy adjustments
    recommendations: list[str] = field(default_factory=list)

    # Frontier recommendation (novel experiment type to try)
    frontier_pick: str | None = None

    # Leads from raw proof packets (unexplored threads)
    raw_leads: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def reflect(current: FitnessScore) -> ReflectionReport:
    """
    Analyze fitness trajectory and produce strategy recommendations.
    """
    report = ReflectionReport(
        cycle_id=current.cycle_id,
        fitness_current=current.fitness,
    )

    # Load history
    history = _load_fitness_history()

    if history:
        prev = history[-1]
        report.fitness_previous = prev.get("fitness", 0.0)
        report.fitness_delta = report.fitness_current - report.fitness_previous
        report.is_improving = report.fitness_delta > 0.5

        # Check for plateau (last 3+ cycles all < 1.0 delta)
        if len(history) >= 3:
            recent_deltas = []
            for i in range(len(history) - 1, max(len(history) - 4, -1), -1):
                if i > 0:
                    delta = history[i].get("fitness", 0.0) - history[i - 1].get("fitness", 0.0)
                    recent_deltas.append(abs(delta))
            if recent_deltas and all(d < 1.0 for d in recent_deltas):
                report.is_plateauing = True

    # Category productivity analysis
    genome = _load_genome()
    for cat, pref in genome.get("template_preferences", {}).items():
        report.category_productivity[cat] = pref  # Placeholder — will be enriched

    # Generate recommendations
    if report.is_plateauing:
        report.recommendations.append(
            "PLATEAU DETECTED: Increase exploration_rate and try frontier experiments"
        )
        report.recommendations.append(
            "Consider increasing mutation_rate to break out of local optimum"
        )

    if current.open_questions > 0:
        report.recommendations.append(
            f"OPEN QUESTIONS: {current.open_questions} remaining — "
            f"prioritize experiments that directly address these"
        )

    if current.coverage_score < 0.8:
        report.recommendations.append(
            f"COVERAGE GAP: {current.coverage_score:.0%} of parameter space explored — "
            f"expand to underexplored regions"
        )

    if current.claim_density < 0.5:
        report.recommendations.append(
            "LOW DENSITY: experiments producing fewer claims per run — "
            "consider more targeted hypotheses"
        )

    # Frontier pick
    frontier = genome.get("experiment_types", {}).get("scope_frontier", [])
    if frontier and (report.is_plateauing or random.random() < genome.get("exploration_rate", 0.2)):
        report.frontier_pick = random.choice(frontier)
        report.recommendations.append(
            f"FRONTIER: Try novel experiment category '{report.frontier_pick}'"
        )

    # Raw packet leads — surface unresolved threads from early experiments
    leads = extract_raw_leads()
    if leads:
        report.raw_leads = leads
        n_prov = sum(1 for l in leads if l["status"] == "provisional")
        n_cand = sum(1 for l in leads if l["status"] == "CANDIDATE")
        if n_prov + n_cand > 0:
            report.recommendations.append(
                f"RAW LEADS: {n_prov} provisional + {n_cand} candidate "
                f"proof packets contain unexplored threads "
                f"({', '.join(l['topic'] for l in leads[:3])}...)"
            )

    return report


# ---------------------------------------------------------------------------
# 3b. Raw Packet Lead Extractor
# ---------------------------------------------------------------------------

@dataclass
class RawLead:
    """An unexplored thread from a raw proof packet."""
    file: str = ""
    topic: str = ""
    claim: str = ""
    parameters: list[str] = field(default_factory=list)
    status: str = "provisional"
    date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def extract_raw_leads() -> list[dict]:
    """Scan raw proof packets for unexplored research leads.

    Extracts the CLAIM, key parameters, and STATUS from each raw packet
    to identify threads the RSI loop hasn't followed up on.

    Returns a list of lead dicts sorted by relevance (CANDIDATE and
    provisional status items first, since those haven't been promoted).
    """
    raw_dir = _RAW_PACKETS_DIR
    if not raw_dir.is_dir():
        return []

    leads = []
    for pp_path in sorted(raw_dir.glob("PP-*.md")):
        try:
            text = pp_path.read_text(encoding="utf-8")
        except Exception:
            continue

        lead: dict[str, Any] = {
            "file": pp_path.name,
            "topic": "",
            "claim": "",
            "parameters": [],
            "status": "provisional",
            "date": "",
        }

        # Extract date from filename
        date_m = re.search(r'PP-(\d{4}-\d{2}-\d{2})', pp_path.name)
        if date_m:
            lead["date"] = date_m.group(1)

        # Extract topic from title
        title_m = re.search(r'^#\s+(?:Proof Packet[:\s—-]*)?(.+)', text, re.MULTILINE)
        if title_m:
            topic = title_m.group(1).strip()
            # Clean up common prefixes
            topic = re.sub(r'^PP-\d{4}-\d{2}-\d{2}-', '', topic)
            lead["topic"] = topic[:80]

        # Extract claim
        claim_section = re.search(
            r'## CLAIM\s*\n(.+?)(?=\n## |\Z)',
            text, re.DOTALL
        )
        if claim_section:
            claim_text = claim_section.group(1).strip()
            # Take first sentence/paragraph
            lead["claim"] = claim_text.split("\n")[0][:200]

        # Also check for "**Primary claim:**" format (cortex packets)
        if not lead["claim"]:
            claim_m = re.search(r'\*\*Primary claim:\*\*\s*(.+)', text)
            if claim_m:
                lead["claim"] = claim_m.group(1).strip()[:200]

        # Extract key parameters
        params: list[str] = []
        # Look for common parameter mentions in the text
        for param_name in ("damping", "c_press", "dt", "psiFreqHz", "psiAmp",
                           "hold", "pressC", "w0", "injection"):
            if re.search(rf'\b{param_name}\b', text, re.IGNORECASE):
                params.append(param_name)
        lead["parameters"] = params[:6]

        # Extract status
        status_m = re.search(
            r'## STATUS\s*\n\s*(\w+)',
            text, re.MULTILINE
        )
        if status_m:
            lead["status"] = status_m.group(1).strip()
        elif "CANDIDATE" in text:
            lead["status"] = "CANDIDATE"

        # Skip if we couldn't extract anything useful
        if lead["topic"] or lead["claim"]:
            leads.append(lead)

    # Sort: prioritize leads with genuinely novel parameters (not just
    # damping/c_press re-sweeps), then by status, then oldest-first.
    explored_core = {"damping", "w0", "injection", "c_press", "dt"}
    def _lead_sort_key(l: dict) -> tuple:
        has_novel = any(p not in explored_core for p in l.get("parameters", []))
        status_order = {"provisional": 0, "CANDIDATE": 1, "supported": 2, "robust": 3}
        return (
            0 if has_novel else 1,           # novel-param leads first
            status_order.get(l["status"], 9),
            l["date"],                        # oldest first within tier
        )
    leads.sort(key=_lead_sort_key)

    return leads


def _load_fitness_history() -> list[dict]:
    """Load all fitness scores from the ledger."""
    if not _FITNESS_LOG.exists():
        return []
    entries = []
    with open(_FITNESS_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


# ===================================================================
# 4. STRATEGY MUTATION
# ===================================================================
# Based on reflection, adjust the genome:
#   - Increase weight on productive experiment types
#   - Decrease weight on unproductive ones
#   - Shift parameter focus to underexplored zones
#   - Occasionally promote a frontier experiment to "enabled"
# ===================================================================

import random


def mutate_genome(genome: dict, reflection: ReflectionReport) -> dict:
    """
    Apply strategy mutations based on reflection results.

    Mutations are small (controlled by mutation_rate) and logged.
    """
    mutations = []
    rate = genome.get("mutation_rate", 0.15)
    now = datetime.now(timezone.utc).isoformat()

    # --- (A) Adjust template preferences based on productivity ---
    prefs = genome.get("template_preferences", {})
    for cat in prefs:
        if random.random() < rate:
            # Boost or trim based on heuristic
            if reflection.is_plateauing:
                # Increase variance: random walk
                delta = random.uniform(-0.2, 0.2)
            elif reflection.is_improving:
                # Double down on current strategy (small positive nudge)
                delta = random.uniform(0.0, 0.1)
            else:
                # Neutral: small random adjustment
                delta = random.uniform(-0.1, 0.1)

            old_val = prefs[cat]
            prefs[cat] = max(0.1, min(2.0, old_val + delta))
            if abs(delta) > 0.01:
                mutations.append(f"template_pref[{cat}]: {old_val:.2f} -> {prefs[cat]:.2f}")

    # --- (B) Shift parameter focus based on coverage ---
    focus = genome.get("parameter_focus", {})
    zones = focus.get("damping_priority_zones", [])
    for zone in zones:
        if random.random() < rate:
            old_p = zone["priority"]
            # If poorly explored, increase priority
            if "dead zone" in zone.get("note", ""):
                zone["priority"] = min(1.0, old_p + random.uniform(0.0, 0.15))
            elif "well-explored" in zone.get("note", ""):
                zone["priority"] = max(0.1, old_p - random.uniform(0.0, 0.1))
            if abs(zone["priority"] - old_p) > 0.01:
                mutations.append(
                    f"damping_zone[{zone['range']}]: priority {old_p:.2f} -> {zone['priority']:.2f}"
                )

    # --- (C) Frontier promotion ---
    frontier = genome.get("experiment_types", {}).get("scope_frontier", [])
    enabled = genome.get("experiment_types", {}).get("enabled", [])
    if reflection.frontier_pick and reflection.frontier_pick in frontier:
        frontier.remove(reflection.frontier_pick)
        enabled.append(reflection.frontier_pick)
        mutations.append(f"FRONTIER PROMOTED: {reflection.frontier_pick}")

    # --- (C2) Frontier regeneration when exhausted ---
    if not frontier:
        gen2_candidates = [t for t in _GEN2_FRONTIER_TYPES if t not in enabled]
        if gen2_candidates:
            genome.setdefault("experiment_types", {})["scope_frontier"] = gen2_candidates
            frontier = gen2_candidates  # update local ref
            mutations.append(
                f"FRONTIER REGENERATED: {len(gen2_candidates)} Gen-2 types: "
                f"{gen2_candidates}"
            )

    # --- (D) Adjust exploration/mutation rates ---
    if reflection.is_plateauing:
        old_er = genome.get("exploration_rate", 0.2)
        genome["exploration_rate"] = min(0.8, old_er + 0.10)
        old_mr = genome.get("mutation_rate", 0.15)
        genome["mutation_rate"] = min(0.5, old_mr + 0.05)
        mutations.append(
            f"PLATEAU RESPONSE: exploration_rate {old_er:.2f}->{genome['exploration_rate']:.2f}, "
            f"mutation_rate {old_mr:.2f}->{genome['mutation_rate']:.2f}"
        )
    elif reflection.is_improving:
        # Reward improvement: maintain current rates to preserve diversity.
        # (Previous stabilization reflex reduced mutation_rate on improvement,
        #  killing exploration at exactly the wrong moment.)
        mutations.append(
            f"IMPROVING: rates preserved "
            f"(mutation={genome.get('mutation_rate', 0.15):.2f}, "
            f"exploration={genome.get('exploration_rate', 0.2):.2f})"
        )

    # Log mutations
    genome["last_cycle"] = reflection.cycle_id
    genome.setdefault("history", []).append({
        "cycle": reflection.cycle_id,
        "timestamp": now,
        "mutations": mutations,
        "fitness_delta": reflection.fitness_delta,
    })

    # Keep history manageable
    if len(genome["history"]) > 50:
        genome["history"] = genome["history"][-50:]

    return genome


# ===================================================================
# 5. PLAN GENERATOR
# ===================================================================
# Given the mutated genome and reflection, generate the next
# experiment plan (what the inner loop should execute).
# ===================================================================

@dataclass
class RSIPlan:
    """What the inner loop should do next."""
    cycle_id: int = 0
    mode: str = "interactive"

    # Planned experiments
    experiments: list[dict] = field(default_factory=list)

    # Configuration for inner loop
    cortex_max_protocols: int = 3
    cortex_gap_type: str | None = None

    # Genome state at plan time
    genome_version: int = 0
    mutation_summary: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def generate_plan(
    genome: dict,
    reflection: ReflectionReport,
    current_fitness: FitnessScore,
    mode: str = "interactive",
) -> RSIPlan:
    """
    Generate the next experiment plan from genome + reflection.
    """
    plan = RSIPlan(
        cycle_id=reflection.cycle_id,
        mode=mode,
        genome_version=genome.get("version", 1),
    )

    # Collect mutation summary
    hist = genome.get("history", [])
    if hist:
        last = hist[-1]
        plan.mutation_summary = last.get("mutations", [])

    # --- Prioritize open questions ---
    if current_fitness.open_questions > 0:
        plan.experiments.append({
            "type": "open_question_resolution",
            "priority": "HIGH",
            "description": f"Address {current_fitness.open_questions} open questions from proof packet",
            "strategy": "Read §14, design targeted probes for each question",
        })

    # --- Frontier exploration ---
    if reflection.frontier_pick:
        plan.experiments.append({
            "type": reflection.frontier_pick,
            "priority": "MEDIUM",
            "description": f"Novel experiment: explore '{reflection.frontier_pick}' category",
            "strategy": "Design exploratory protocol for new domain",
        })

    # --- Parameter zone sweeps ---
    focus = genome.get("parameter_focus", {})
    zones = sorted(
        focus.get("damping_priority_zones", []),
        key=lambda z: z.get("priority", 0),
        reverse=True,
    )
    for zone in zones[:2]:  # Top 2 priority zones
        if zone.get("priority", 0.0) > 0.7:
            plan.experiments.append({
                "type": "parameter_sweep",
                "priority": "MEDIUM",
                "description": f"Sweep damping {zone['range']} ({zone.get('note', '')})",
                "strategy": "Fine-grained sweep targeting least-understood behavior",
            })

    # --- Template-preference-driven experiments (weighted random) ---
    prefs = genome.get("template_preferences", {})
    already_planned = {e["type"] for e in plan.experiments}
    eligible = [(tmpl, w) for tmpl, w in prefs.items()
                if tmpl not in already_planned and w > 0.3]
    if eligible:
        labels_list = [t for t, _ in eligible]
        weights = [w for _, w in eligible]
        n_picks = min(3, len(eligible))
        picks = random.choices(labels_list, weights=weights, k=n_picks)
        for tmpl in dict.fromkeys(picks):   # deduplicate, preserve order
            plan.experiments.append({
                "type": tmpl,
                "priority": "MEDIUM",
                "description": f"Template '{tmpl}' (weight={prefs[tmpl]:.2f})",
                "strategy": f"Apply {tmpl} template to highest-priority gap",
            })

    # --- Raw packet leads (unexplored threads from early experiments) ---
    raw_leads = getattr(reflection, "raw_leads", [])
    if raw_leads:
        # Prioritize leads with genuinely novel parameters — psiFreqHz, hold,
        # pressC etc. are from different manifold regions than phonon_faraday's
        # damping/w0/injection focus.  Skip cortex-generated packets that just
        # re-sweep damping, since those overlap with existing domain work.
        explored_params = {"damping", "w0", "injection", "c_press", "dt"}
        novel_leads = [
            l for l in raw_leads
            if any(p not in explored_params for p in l.get("parameters", []))
            and l.get("claim", "") and "no claim" not in l.get("claim", "").lower()
        ]
        # Fall back to any leads if no novel-param ones
        candidates = novel_leads[:2] if novel_leads else raw_leads[:2]
        for lead in candidates:
            params_str = ", ".join(lead.get("parameters", [])[:3])
            plan.experiments.append({
                "type": "raw_lead_followup",
                "priority": "LOW",
                "description": (
                    f"Follow up: {lead.get('topic', 'unknown')[:60]} "
                    f"({lead.get('status', '?')}, {lead.get('date', '?')})"
                ),
                "strategy": (
                    f"Replicate and extend: {lead.get('claim', '')[:100]}. "
                    f"Key params: {params_str}"
                ),
                "source_file": lead.get("file", ""),
            })

    # --- Wildcard: ensure at least one type not already in plan ---
    all_enabled = genome.get("experiment_types", {}).get("enabled", [])
    frontier_types = genome.get("experiment_types", {}).get("scope_frontier", [])
    all_types = all_enabled + frontier_types
    already_in_plan = {e["type"] for e in plan.experiments}
    wildcards = [t for t in all_types if t not in already_in_plan]
    if wildcards:
        wild = random.choice(wildcards)
        plan.experiments.append({
            "type": wild,
            "priority": "LOW",
            "description": f"Wildcard exploration: '{wild}'",
            "strategy": "Random selection to maintain diversity",
        })

    # Configure cortex
    if mode == "cron":
        plan.cortex_max_protocols = min(5, max(2, len(plan.experiments)))
    elif mode == "persistent":
        plan.cortex_max_protocols = min(8, max(3, len(plan.experiments)))
    else:
        plan.cortex_max_protocols = 3

    return plan


# ===================================================================
# 6. EXECUTION BRIDGE
# ===================================================================
# Thin wrapper that translates the RSI plan into inner-loop calls.
# In "interactive" mode, this prints the plan and waits.
# In "cron" and "persistent" modes, this calls the orchestrator API.
# ===================================================================

def execute_plan(plan: RSIPlan, dry_run: bool = False) -> dict:
    """
    Execute the RSI plan via the inner loop.

    Returns execution results dict.
    """
    results = {
        "cycle_id": plan.cycle_id,
        "mode": plan.mode,
        "experiments_planned": len(plan.experiments),
        "experiments_executed": 0,
        "dry_run": dry_run,
    }

    if dry_run:
        print("\n  [DRY RUN] Plan generated but not executed.")
        return results

    if plan.mode == "interactive":
        print("\n  [INTERACTIVE] Plan generated. Execute via human guidance.")
        print("  The following experiments are recommended:")
        for i, exp in enumerate(plan.experiments, 1):
            print(f"    {i}. [{exp['priority']}] {exp['type']}: {exp['description']}")
        print("\n  Use the sol-cortex or sol-orchestrator agents to execute.")
        return results

    # --- Automated execution (cron / persistent) ---
    try:
        _inject_path_lazy(_ORCHESTRATOR_DIR)
        from orchestrator import PipelineConfig, run_pipeline

        config = PipelineConfig(
            cortex_max_protocols=plan.cortex_max_protocols,
            cortex_gap_type=plan.cortex_gap_type,
        )
        pipeline_result = run_pipeline(config)
        results["pipeline_result"] = pipeline_result
        results["experiments_executed"] = plan.cortex_max_protocols
    except ImportError:
        print("  [WARNING] Orchestrator not available. Logging plan only.")
    except Exception as e:
        results["error"] = str(e)
        print(f"  [ERROR] Execution failed: {e}")

    return results


def _inject_path_lazy(directory: Path):
    d = str(directory)
    if d not in sys.path:
        sys.path.insert(0, d)


# ===================================================================
# 7. PERSISTENCE / LOGGING
# ===================================================================

def log_fitness(score: FitnessScore):
    """Append fitness score to the ledger."""
    _RSI_DIR.mkdir(parents=True, exist_ok=True)
    with open(_FITNESS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(score.to_dict()) + "\n")


def log_cycle(cycle_id: int, fitness: FitnessScore, reflection: ReflectionReport,
              plan: RSIPlan, execution: dict):
    """Log a complete RSI cycle."""
    entry = {
        "cycle_id": cycle_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fitness": fitness.to_dict(),
        "reflection": reflection.to_dict(),
        "plan": plan.to_dict(),
        "execution": execution,
    }
    _RSI_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CYCLE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# ===================================================================
# 8. RSI MAIN LOOP
# ===================================================================

def rsi_cycle(cycle_id: int, mode: str = "interactive", dry_run: bool = False) -> FitnessScore:
    """
    Execute one complete RSI cycle:
        EVALUATE -> REFLECT -> MUTATE -> PLAN -> EXECUTE -> COMMIT
    """
    print(f"\n{'='*70}")
    print(f"  RSI CYCLE {cycle_id}")
    print(f"  Mode: {mode} | Dry-run: {dry_run}")
    print(f"{'='*70}")

    # --- EVALUATE ---
    print("\n  [1/6] EVALUATE: computing fitness score...")
    fitness = evaluate_fitness(cycle_id)
    print(f"    Fitness: {fitness.fitness:.1f}/100")
    print(f"    Claims: {fitness.claim_count} | Open Q: {fitness.open_questions} | "
          f"Experiments: {fitness.experiment_count}")
    print(f"    Trials: {fitness.trial_count} | Compute: {fitness.compute_minutes:.0f} min")
    print(f"    Density: {fitness.claim_density:.2f} | Coverage: {fitness.coverage_score:.2f} | "
          f"Productivity: {fitness.productivity:.2f}")

    # --- REFLECT ---
    print("\n  [2/6] REFLECT: analyzing trajectory...")
    reflection = reflect(fitness)
    print(f"    Delta: {reflection.fitness_delta:+.1f}")
    print(f"    Improving: {reflection.is_improving} | Plateauing: {reflection.is_plateauing}")
    for rec in reflection.recommendations:
        print(f"    -> {rec}")

    # --- MUTATE ---
    print("\n  [3/6] MUTATE: evolving strategy genome...")
    genome = _load_genome()
    if genome.get("created", "") == "":
        genome["created"] = datetime.now(timezone.utc).isoformat()
    genome = mutate_genome(genome, reflection)
    _save_genome(genome)
    hist = genome.get("history", [])
    if hist:
        for m in hist[-1].get("mutations", []):
            print(f"    >> {m}")
    if not hist or not hist[-1].get("mutations"):
        print("    (no mutations this cycle)")

    # --- PLAN ---
    print("\n  [4/6] PLAN: generating experiment plan...")
    plan = generate_plan(genome, reflection, fitness, mode)
    print(f"    Planned experiments: {len(plan.experiments)}")
    for i, exp in enumerate(plan.experiments, 1):
        print(f"    {i}. [{exp['priority']:>6s}] {exp['type']}: {exp['description']}")

    # --- EXECUTE ---
    print("\n  [5/7] EXECUTE...")
    execution = execute_plan(plan, dry_run=dry_run)
    print(f"    Executed: {execution['experiments_executed']}/{len(plan.experiments)}")

    # --- COMPILE ---
    print("\n  [6/7] COMPILE: extracting claims from experiment data...")
    compile_result = None
    if not dry_run:
        try:
            _compile = _get_compiler()
            compile_result = _compile(
                update_proof_packet_flag=True,
                verbose=True,
            )
            if compile_result and compile_result.proof_packet_updated:
                print(f"    Proof packet updated: +{len(compile_result.new_claims)} claims, "
                      f"+{compile_result.total_trials_added} trials")
                # Re-evaluate fitness with updated proof packet
                print("    Re-evaluating fitness after compilation...")
                fitness = evaluate_fitness(cycle_id)
                print(f"    Updated fitness: {fitness.fitness:.1f}/100 "
                      f"(claims={fitness.claim_count}, open_q={fitness.open_questions})")
            else:
                print("    No new claims to compile (all results already processed)")
        except Exception as e:
            print(f"    [WARNING] Claim compilation failed: {e}")
    else:
        print("    [DRY RUN] Skipping compilation.")

    # --- COMMIT ---
    print("\n  [7/7] COMMIT: persisting results...")
    log_fitness(fitness)
    log_cycle(cycle_id, fitness, reflection, plan, execution)
    print(f"    Fitness logged to {_FITNESS_LOG}")
    print(f"    Cycle logged to {_CYCLE_LOG}")
    print(f"    Genome saved to {_GENOME_FILE}")

    return fitness


def run_rsi(
    mode: str = "interactive",
    cycles: int = 1,
    budget_hours: float = 0.0,
    dry_run: bool = False
):
    """
    Run the RSI engine for N cycles or until budget exhausted.
    """
    print("\n" + "=" * 70)
    print("  SOL RECURSIVE SELF-IMPROVEMENT ENGINE")
    print(f"  Mode: {mode} | Cycles: {cycles} | Budget: {budget_hours}h")
    print("=" * 70)

    # Determine starting cycle ID
    history = _load_fitness_history()
    start_cycle = len(history) + 1

    t0 = time.time()
    results = []

    for i in range(cycles):
        cycle_id = start_cycle + i

        # Budget check
        if budget_hours > 0:
            elapsed_hours = (time.time() - t0) / 3600
            if elapsed_hours >= budget_hours:
                print(f"\n  Budget exhausted ({elapsed_hours:.1f}h >= {budget_hours}h). Stopping.")
                break

        fitness = rsi_cycle(cycle_id, mode=mode, dry_run=dry_run)
        results.append(fitness)

        # In persistent mode, allow a pause between cycles
        if mode == "persistent" and i < cycles - 1:
            print(f"\n  Cycle {cycle_id} complete. Pausing 5s before next cycle...")
            time.sleep(5)

    # Final summary
    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  RSI SESSION COMPLETE")
    print(f"  Cycles: {len(results)} | Time: {elapsed:.0f}s")
    if results:
        print(f"  Start fitness: {results[0].fitness:.1f} | End fitness: {results[-1].fitness:.1f}")
        print(f"  Net delta: {results[-1].fitness - results[0].fitness:+.1f}")
    print(f"{'='*70}")


def print_status():
    """Print current RSI status."""
    print("\n" + "=" * 70)
    print("  SOL RSI STATUS REPORT")
    print("=" * 70)

    # Current fitness
    fitness = evaluate_fitness(0)
    print(f"\n  Current Fitness: {fitness.fitness:.1f}/100")
    print(f"    Claims: {fitness.claim_count}")
    print(f"    Open Questions: {fitness.open_questions}")
    print(f"    Experiments: {fitness.experiment_count}")
    print(f"    Trials: {fitness.trial_count}")
    print(f"    Compute: {fitness.compute_minutes:.0f} min")

    # Fitness history
    history = _load_fitness_history()
    if history:
        print(f"\n  Fitness History ({len(history)} cycles):")
        for h in history[-5:]:
            print(f"    Cycle {h.get('cycle_id', '?')}: "
                  f"fitness={h.get('fitness', 0):.1f} "
                  f"claims={h.get('claim_count', 0)} "
                  f"open_q={h.get('open_questions', 0)}")
    else:
        print("\n  No previous cycles. Run 'python rsi_engine.py' to start.")

    # Genome status
    genome = _load_genome()
    if genome.get("created"):
        print(f"\n  Genome: version={genome.get('version', 1)}, "
              f"cycles={genome.get('last_cycle', 0)}, "
              f"mutation_rate={genome.get('mutation_rate', 0.15):.2f}, "
              f"exploration_rate={genome.get('exploration_rate', 0.2):.2f}")

        frontier = genome.get("experiment_types", {}).get("scope_frontier", [])
        enabled = genome.get("experiment_types", {}).get("enabled", [])
        print(f"    Enabled types: {len(enabled)}")
        print(f"    Frontier types: {len(frontier)} — {frontier[:3]}...")
    else:
        print("\n  Genome: not yet initialized")

    print()


# ===================================================================
# CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SOL Recursive Self-Improvement Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  interactive   Human-in-the-loop (default). Prints plan, doesn't auto-execute.
  cron          Unattended single cycle (for GitHub Actions).
  persistent    Continuous loop until budget exhausted.

Examples:
  python rsi_engine.py                              # Interactive, 1 cycle
  python rsi_engine.py --mode cron --cycles 1       # GitHub Actions
  python rsi_engine.py --mode persistent --cycles 10 --budget-hours 8
  python rsi_engine.py --dry-run                    # Evaluate only
  python rsi_engine.py --status                     # Status report
        """
    )

    parser.add_argument("--mode", choices=["interactive", "cron", "persistent"],
                        default="interactive", help="Execution mode")
    parser.add_argument("--cycles", type=int, default=1, help="Number of RSI cycles")
    parser.add_argument("--budget-hours", type=float, default=0.0,
                        help="Maximum runtime in hours (0 = unlimited)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Evaluate and plan only, don't execute")
    parser.add_argument("--status", action="store_true",
                        help="Print current RSI status and exit")

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    run_rsi(
        mode=args.mode,
        cycles=args.cycles,
        budget_hours=args.budget_hours,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
