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
    python rsi_engine.py --mode persistent --budget-dollars 1.0

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
import os
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
_CHECKPOINT_FILE = _RSI_DIR / "_rsi_state.json"
_HEARTBEAT_FILE = _RSI_DIR / "heartbeat.json"
_COST_LEDGER = _RSI_DIR / "llm_cost_ledger.jsonl"
_OUTCOME_LEDGER = _RSI_DIR / "outcome_ledger.jsonl"
_PROOF_PACKETS_DIR = _SOL_ROOT / "solKnowledge" / "proof_packets"
_DOMAINS_DIR = _PROOF_PACKETS_DIR / "domains"
_RAW_PACKETS_DIR = _PROOF_PACKETS_DIR / "raw"

# Tool paths (for inner-loop integration)
_CORE_DIR = _SOL_ROOT / "tools" / "sol-core"
_CORTEX_DIR = _SOL_ROOT / "tools" / "sol-cortex"
_HIPPO_DIR = _SOL_ROOT / "tools" / "sol-hippocampus"
_EVOLVE_DIR = _SOL_ROOT / "tools" / "sol-evolve"
_ORCHESTRATOR_DIR = _SOL_ROOT / "tools" / "sol-orchestrator"


# ---------------------------------------------------------------------------
# .env auto-loading (mirrors client.py but runs independently)
# ---------------------------------------------------------------------------

def _load_dotenv():
    """Load .env from SOL root if GITHUB_TOKEN is not already set."""
    if os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_MODELS_TOKEN"):
        return
    env_path = _SOL_ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key and val and key not in os.environ:
                os.environ[key] = val

_load_dotenv()


# ---------------------------------------------------------------------------
# Checkpointing (crash-safe resume for persistent mode)
# ---------------------------------------------------------------------------

def _save_checkpoint(state: dict):
    """Write current RSI run state to disk so persistent mode can resume."""
    _RSI_DIR.mkdir(parents=True, exist_ok=True)
    state["updated"] = datetime.now(timezone.utc).isoformat()
    with open(_CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _load_checkpoint() -> dict | None:
    """Load checkpoint from prior crashed run, if any."""
    if _CHECKPOINT_FILE.exists():
        try:
            with open(_CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _clear_checkpoint():
    """Remove checkpoint after a clean session finish."""
    if _CHECKPOINT_FILE.exists():
        _CHECKPOINT_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Heartbeat (external liveness monitor)
# ---------------------------------------------------------------------------

def _write_heartbeat(cycle_id: int, status: str, extra: dict | None = None):
    """Write a heartbeat file for external monitoring."""
    _RSI_DIR.mkdir(parents=True, exist_ok=True)
    hb = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle_id": cycle_id,
        "status": status,
        "pid": os.getpid(),
    }
    if extra:
        hb.update(extra)
    with open(_HEARTBEAT_FILE, "w", encoding="utf-8") as f:
        json.dump(hb, f, indent=2)


# ---------------------------------------------------------------------------
# Cost ceiling helpers
# ---------------------------------------------------------------------------

def _load_session_cost() -> float:
    """Load total cost for today from the LLM cost ledger."""
    if not _COST_LEDGER.exists():
        return 0.0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0.0
    try:
        with open(_COST_LEDGER, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("timestamp", "").startswith(today):
                        total += entry.get("cost_usd", 0.0)
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return total


# ---------------------------------------------------------------------------
# Smart cooldown (rate-limit aware inter-cycle pause)
# ---------------------------------------------------------------------------

# GPT-5 Chat free tier: 12 calls/day, 2/min
_DAILY_CALL_LIMIT = 12
_PER_MINUTE_LIMIT = 2
_CALLS_PER_CYCLE = 5  # consolidation makes ~5 LLM calls per cortex session


# ---------------------------------------------------------------------------
# Outcome Ledger — record what each cycle actually produced
# ---------------------------------------------------------------------------

def _record_outcome(
    cycle_id: int,
    pre_fitness: FitnessScore,
    post_fitness: FitnessScore,
    plan: 'RSIPlan',
    execution: dict,
):
    """Record the measurable outcome of an RSI cycle.

    Stores the delta in claims, questions, fitness, plus which template types
    were planned.  This data feeds reward-driven mutation in future cycles.
    """
    _RSI_DIR.mkdir(parents=True, exist_ok=True)
    templates_planned = [
        e.get("type", "unknown") for e in getattr(plan, "experiments", [])
    ]
    # Derive which template the cortex *actually* used (from execution output)
    cortex_output = execution.get("pipeline_result", {}).get("stages", {}).get(
        "cortex", {}
    )
    if isinstance(cortex_output, dict):
        cortex_output = cortex_output.get("output", {})
    else:
        cortex_output = {}

    outcome = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle_id": cycle_id,
        "templates_planned": templates_planned,
        "experiments_executed": execution.get("experiments_executed", 0),
        "pre": {
            "fitness": round(pre_fitness.fitness, 2),
            "claims": pre_fitness.claim_count,
            "open_q": pre_fitness.open_questions,
            "experiments": pre_fitness.experiment_count,
        },
        "post": {
            "fitness": round(post_fitness.fitness, 2),
            "claims": post_fitness.claim_count,
            "open_q": post_fitness.open_questions,
            "experiments": post_fitness.experiment_count,
        },
        "delta": {
            "fitness": round(post_fitness.fitness - pre_fitness.fitness, 3),
            "claims": post_fitness.claim_count - pre_fitness.claim_count,
            "open_q": post_fitness.open_questions - pre_fitness.open_questions,
            "experiments": post_fitness.experiment_count - pre_fitness.experiment_count,
        },
        "error": execution.get("error"),
    }
    with open(_OUTCOME_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(outcome) + "\n")


def _load_outcome_history(last_n: int = 20) -> list[dict]:
    """Load recent outcome records for reward computation."""
    if not _OUTCOME_LEDGER.exists():
        return []
    entries = []
    try:
        with open(_OUTCOME_LEDGER, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return entries[-last_n:]

def _compute_cooldown(cycles_remaining: int) -> float:
    """
    Compute how many seconds to wait before the next cycle so we don't
    burn through the daily rate limit too fast.

    Strategy: spread remaining daily calls evenly across remaining cycles,
    with a floor of 60s (to respect per-minute limits) and a cap of 1800s.
    """
    # If no more cycles, no wait
    if cycles_remaining <= 0:
        return 0.0

    # Read today's cost ledger to estimate calls already made
    calls_today = 0
    if _COST_LEDGER.exists():
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            with open(_COST_LEDGER, "r", encoding="utf-8") as f:
                for line in f:
                    if today in line:
                        calls_today += 1
        except OSError:
            pass

    calls_remaining_today = max(1, _DAILY_CALL_LIMIT - calls_today)
    calls_needed = cycles_remaining * _CALLS_PER_CYCLE

    if calls_needed <= calls_remaining_today:
        # Enough budget — just respect per-minute limit
        return max(60.0, 30.0 * _CALLS_PER_CYCLE)  # ~2.5 min between cycles
    else:
        # Spread remaining calls across 24h from now
        seconds_per_call = 86400 / max(1, _DAILY_CALL_LIMIT)
        cooldown = seconds_per_call * _CALLS_PER_CYCLE
        return min(1800.0, max(60.0, cooldown))


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

        # Count claims + open questions in raw (pre-domain) packets too
        # Scan both raw/ and root proof_packets/ since cortex writes to root
        scan_dirs = []
        if _RAW_PACKETS_DIR.is_dir():
            scan_dirs.append(_RAW_PACKETS_DIR)
        scan_dirs.append(_PROOF_PACKETS_DIR)  # always scan root
        seen_packets = set()
        for scan_dir in scan_dirs:
            for packet in scan_dir.glob("PP-*.md"):
                if packet.name in seen_packets:
                    continue
                seen_packets.add(packet.name)
                try:
                    ptxt = packet.read_text(encoding="utf-8")
                    # Cortex packets use "Claim:" prefix
                    claim_lines = [l for l in ptxt.split("\n")
                                   if l.strip().startswith("**Claim")]
                    score.claim_count += len(claim_lines)
                    # Also count open questions in cortex proof packets
                    score.open_questions += _count_open_questions(ptxt)
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

    # Attach component scores for fitness-weight evolution
    report._claim_density = current.claim_density
    report._question_ratio = current.question_ratio
    report._coverage_score = current.coverage_score
    report._productivity = current.productivity

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

    # --- LLM-Powered Strategic Reflection (Phase 4) ---
    # Replaces generic rule-based advice with deep strategic analysis
    llm_insight = _try_llm_reflection(
        history, _load_outcome_history(), genome, current, leads
    )
    if llm_insight:
        report.recommendations.append(
            f"LLM STRATEGY: {llm_insight.get('diagnosis', 'N/A')[:200]}"
        )
        report.recommendations.append(
            f"LLM META-INSIGHT: {llm_insight.get('meta_insight', 'N/A')[:200]}"
        )
        # Store full LLM analysis for the plan generator to use
        report._llm_strategy = llm_insight

    return report


def _try_llm_reflection(
    fitness_history: list[dict],
    outcome_history: list[dict],
    genome: dict,
    current: FitnessScore,
    raw_leads: list[dict],
) -> dict | None:
    """Attempt LLM-powered strategic reflection. Returns None on failure."""
    try:
        _inject_path_lazy(_SOL_ROOT / "tools" / "sol-llm")
        from client import SolLLM
        if not SolLLM.is_available():
            return None

        from prompts import PromptLibrary

        # Collect open questions text from proof packets
        open_qs: list[str] = []
        if _DOMAINS_DIR.is_dir():
            for dp in sorted(_DOMAINS_DIR.glob("*.md")):
                try:
                    text = dp.read_text(encoding="utf-8")
                    in_q = False
                    for line in text.split("\n"):
                        if "Remaining Open Questions" in line:
                            in_q = True
                            continue
                        if in_q:
                            stripped = line.strip()
                            if stripped.startswith("---") or (
                                stripped.startswith("#") and "Open" not in stripped
                            ):
                                break
                            if stripped and stripped[0].isdigit() and "." in stripped[:4]:
                                if "[RESOLVED]" not in stripped:
                                    open_qs.append(stripped)
                except Exception:
                    pass

        system, user = PromptLibrary.strategic_reflection(
            fitness_trajectory=fitness_history[-10:],
            outcome_history=outcome_history[-10:],
            genome_state=genome,
            open_questions=open_qs or None,
            raw_leads=raw_leads[:5] if raw_leads else None,
        )

        llm = SolLLM(verbose=True)
        response = llm.complete_json(user, system=system, task="reflection")

        if response.success and response.parsed:
            return response.parsed
        return None
    except Exception:
        return None


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
    Apply strategy mutations based on reflection + outcome history.

    Phase 4 upgrade: mutations are REWARD-DRIVEN.  We read the outcome
    ledger to see which template types actually produced claim deltas,
    then boost winners and dim losers.  Random walk is the fallback when
    outcome data is sparse.
    """
    mutations = []
    rate = genome.get("mutation_rate", 0.15)
    now = datetime.now(timezone.utc).isoformat()

    # --- (A) REWARD-DRIVEN template preference update ---
    prefs = genome.get("template_preferences", {})
    outcomes = _load_outcome_history(last_n=20)

    # Build reward signal: for each template that appeared in a cycle,
    # attribute +claim_delta to it.  Average over recent cycles.
    template_rewards: dict[str, list[float]] = defaultdict(list)
    for oc in outcomes:
        claim_delta = oc.get("delta", {}).get("claims", 0)
        fitness_delta = oc.get("delta", {}).get("fitness", 0.0)
        # Composite reward: claims matter most, fitness delta secondary
        reward = claim_delta * 2.0 + fitness_delta * 0.1
        for tmpl in oc.get("templates_planned", []):
            template_rewards[tmpl].append(reward)

    has_reward_data = len(template_rewards) > 0

    for cat in prefs:
        if random.random() < rate:
            if has_reward_data and cat in template_rewards:
                # Reward-driven: boost templates with positive avg reward,
                # dim templates with negative
                avg_reward = sum(template_rewards[cat]) / len(template_rewards[cat])
                if avg_reward > 0:
                    delta = min(0.15, avg_reward * 0.05)
                elif avg_reward < 0:
                    delta = max(-0.15, avg_reward * 0.05)
                else:
                    delta = random.uniform(-0.05, 0.05)
                old_val = prefs[cat]
                prefs[cat] = max(0.1, min(2.0, old_val + delta))
                if abs(delta) > 0.01:
                    mutations.append(
                        f"REWARD template_pref[{cat}]: {old_val:.2f} -> "
                        f"{prefs[cat]:.2f} (avg_reward={avg_reward:+.2f})"
                    )
            else:
                # Fallback: random walk (same as Phase 3)
                if reflection.is_plateauing:
                    delta = random.uniform(-0.2, 0.2)
                elif reflection.is_improving:
                    delta = random.uniform(0.0, 0.1)
                else:
                    delta = random.uniform(-0.1, 0.1)
                old_val = prefs[cat]
                prefs[cat] = max(0.1, min(2.0, old_val + delta))
                if abs(delta) > 0.01:
                    mutations.append(
                        f"template_pref[{cat}]: {old_val:.2f} -> {prefs[cat]:.2f}"
                    )

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

    # --- (E) Fitness weight evolution ---
    # If one fitness component is lagging, increase its weight to steer
    # the loop toward improving it.  This lets the system learn what
    # to optimise for at each stage of its research lifecycle.
    fw = genome.get("fitness_weights", dict(DEFAULT_FITNESS_WEIGHTS))
    if random.random() < rate:
        # Find the weakest fitness component from the reflection
        component_scores = {
            "claim_density": getattr(reflection, "_claim_density", None),
            "question_ratio": getattr(reflection, "_question_ratio", None),
            "coverage_score": getattr(reflection, "_coverage_score", None),
            "productivity": getattr(reflection, "_productivity", None),
        }
        # If reflection carries live scores, boost the weakest
        live = {k: v for k, v in component_scores.items() if v is not None}
        if live:
            weakest = min(live, key=live.get)
            old_w = fw.get(weakest, 0.25)
            fw[weakest] = min(0.50, old_w + 0.03)
            # Re-normalise so weights sum to ~1.0
            total = sum(fw.values())
            if total > 0:
                fw = {k: v / total for k, v in fw.items()}
            genome["fitness_weights"] = fw
            mutations.append(
                f"FITNESS_WEIGHT boosted '{weakest}': {old_w:.2f} -> {fw[weakest]:.2f}"
            )

    # --- (F) Apply LLM strategy recommendations (Phase 4) ---
    llm_strat = getattr(reflection, "_llm_strategy", None)
    if llm_strat and isinstance(llm_strat, dict):
        genome_recs = llm_strat.get("genome_recommendations", {})
        # Apply recommended template boosts
        for tmpl, boost in genome_recs.get("template_boosts", {}).items():
            if tmpl in prefs and isinstance(boost, (int, float)):
                old_val = prefs[tmpl]
                prefs[tmpl] = max(0.1, min(2.0, old_val + boost))
                mutations.append(
                    f"LLM_BOOST template_pref[{tmpl}]: "
                    f"{old_val:.2f} -> {prefs[tmpl]:.2f}"
                )
        # Apply recommended template dims
        for tmpl, dim in genome_recs.get("template_dims", {}).items():
            if tmpl in prefs and isinstance(dim, (int, float)):
                old_val = prefs[tmpl]
                prefs[tmpl] = max(0.1, min(2.0, old_val - abs(dim)))
                mutations.append(
                    f"LLM_DIM template_pref[{tmpl}]: "
                    f"{old_val:.2f} -> {prefs[tmpl]:.2f}"
                )
        # Apply recommended rates (with bounds)
        if "mutation_rate" in genome_recs and isinstance(
            genome_recs["mutation_rate"], (int, float)
        ):
            rec_mr = max(0.05, min(0.5, genome_recs["mutation_rate"]))
            old_mr = genome.get("mutation_rate", 0.15)
            genome["mutation_rate"] = rec_mr
            mutations.append(f"LLM_RATE mutation_rate: {old_mr:.2f} -> {rec_mr:.2f}")
        if "exploration_rate" in genome_recs and isinstance(
            genome_recs["exploration_rate"], (int, float)
        ):
            rec_er = max(0.05, min(0.8, genome_recs["exploration_rate"]))
            old_er = genome.get("exploration_rate", 0.2)
            genome["exploration_rate"] = rec_er
            mutations.append(
                f"LLM_RATE exploration_rate: {old_er:.2f} -> {rec_er:.2f}"
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
        print("  Or re-run with --mode cron for automated execution.")
        return results

    # --- Automated execution (cron / persistent) ---
    print(f"\n  [{plan.mode.upper()}] Running orchestrator pipeline...")
    try:
        _inject_path_lazy(_ORCHESTRATOR_DIR)
        from orchestrator import PipelineConfig, PipelineRunner, run_pipeline

        # Translate RSI plan into orchestrator config
        config = PipelineConfig(
            cortex_max_protocols=plan.cortex_max_protocols,
            cortex_gap_type=plan.cortex_gap_type,
            verbose=True,
        )

        # Run the full pipeline: smoke → cortex → consolidate → hippocampus → report
        pipeline_summary = run_pipeline(config)

        # Extract execution statistics from the pipeline result
        results["pipeline_run_id"] = pipeline_summary.get("run_id", "")
        results["pipeline_verdict"] = pipeline_summary.get("pipeline_verdict", "UNKNOWN")
        results["core_immutability"] = pipeline_summary.get("core_immutability", "UNKNOWN")

        # Count what actually executed
        stages = pipeline_summary.get("stages", {})
        cortex_stage = stages.get("cortex", {})
        cortex_output = cortex_stage.get("output", {}) if isinstance(cortex_stage, dict) else {}

        protocols_run = cortex_output.get("protocols_run", 0)
        results["experiments_executed"] = protocols_run
        results["cortex_session_id"] = cortex_output.get("session_id", "")
        results["cortex_session_dir"] = cortex_output.get("session_dir", "")
        results["cortex_total_steps"] = cortex_output.get("total_steps", 0)
        results["cortex_hypotheses"] = cortex_output.get("hypotheses", 0)

        # Consolidation stage
        consolidate_stage = stages.get("consolidate", {})
        consolidate_output = consolidate_stage.get("output", {}) if isinstance(consolidate_stage, dict) else {}
        results["consolidation"] = consolidate_output

        # Hippocampus stage
        hippo_stage = stages.get("hippocampus", {})
        hippo_output = hippo_stage.get("output", {}) if isinstance(hippo_stage, dict) else {}
        results["dream_basins_discovered"] = hippo_output.get("basins_discovered", 0)

        results["pipeline_result"] = pipeline_summary

        print(f"    Pipeline: {results['pipeline_verdict']} "
              f"(run {results['pipeline_run_id']})")
        print(f"    Cortex executed {protocols_run} protocols, "
              f"{cortex_output.get('total_steps', 0)} steps")

    except ImportError as e:
        results["error"] = f"ImportError: {e}"
        print(f"  [WARNING] Orchestrator not available: {e}")
    except Exception as e:
        results["error"] = str(e)
        print(f"  [ERROR] Execution failed: {e}")
        import traceback
        traceback.print_exc()

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


# ---------------------------------------------------------------------------
# Cross-Experiment Synthesis (Phase 4)
# ---------------------------------------------------------------------------

def _try_cross_experiment_synthesis(cycle_id: int) -> dict | None:
    """Run LLM cross-experiment reasoning over recent proof packets.

    Scans domain packets and raw proof packets to build experiment
    summaries, then asks the LLM to identify meta-patterns,
    contradictions, and critical next experiments.

    Returns the parsed LLM JSON or None on failure.
    """
    try:
        _inject_path_lazy(_SOL_ROOT / "tools" / "sol-llm")
        from client import SolLLM
        if not SolLLM.is_available():
            return None

        from prompts import PromptLibrary

        # Build experiment summaries from proof packets
        experiment_summaries: list[dict] = []
        claim_excerpt_parts: list[str] = []

        # Domain packets
        if _DOMAINS_DIR.is_dir():
            for dp in sorted(_DOMAINS_DIR.glob("*.md")):
                try:
                    text = dp.read_text(encoding="utf-8")
                    # Extract experiment sections
                    for m in re.finditer(
                        r'## Experiment \d+[:\s—-]*(.+?)(?=\n## |\Z)',
                        text, re.DOTALL,
                    ):
                        title = m.group(1).split("\n")[0].strip()[:100]
                        body = m.group(1)[:500]
                        experiment_summaries.append({
                            "title": title,
                            "type": "domain_experiment",
                            "findings": body[:300],
                            "parameters": {},
                            "trials": 0,
                        })
                    # Extract claim table rows for context
                    for line in text.split("\n"):
                        if re.match(r'^\|\s*C\d+\s*\|', line.strip()):
                            claim_excerpt_parts.append(line.strip())
                except Exception:
                    pass

        # Raw proof packets (recent cortex output)
        if _RAW_PACKETS_DIR.is_dir():
            for pp in sorted(_RAW_PACKETS_DIR.glob("PP-*.md"))[-10:]:
                try:
                    text = pp.read_text(encoding="utf-8")
                    claim_m = re.search(r'\*\*Primary claim:\*\*\s*(.+)', text)
                    claim = claim_m.group(1).strip()[:200] if claim_m else pp.name
                    experiment_summaries.append({
                        "title": claim,
                        "type": "raw_proof_packet",
                        "findings": text[:400],
                        "parameters": {},
                        "trials": 0,
                    })
                except Exception:
                    pass

        if len(experiment_summaries) < 3:
            return None  # Need enough data for cross-experiment reasoning

        claim_excerpt = "\n".join(claim_excerpt_parts[:30])

        system, user = PromptLibrary.cross_experiment(
            experiment_summaries=experiment_summaries[:15],
            claim_ledger_excerpt=claim_excerpt,
        )

        llm = SolLLM(verbose=True)
        response = llm.complete_json(user, system=system, task="synthesis")

        if response.success and response.parsed:
            return response.parsed
        return None
    except Exception:
        return None


# ===================================================================
# 8. RSI MAIN LOOP
# ===================================================================

def rsi_cycle(cycle_id: int, mode: str = "interactive", dry_run: bool = False) -> FitnessScore:
    """
    Execute one complete RSI cycle:
        EVALUATE -> REFLECT -> MUTATE -> PLAN -> EXECUTE -> COMPILE -> SYNTHESIZE -> COMMIT
    """
    print(f"\n{'='*70}")
    print(f"  RSI CYCLE {cycle_id}")
    print(f"  Mode: {mode} | Dry-run: {dry_run}")
    print(f"{'='*70}")

    # --- EVALUATE ---
    print("\n  [1/8] EVALUATE: computing fitness score...")
    fitness = evaluate_fitness(cycle_id)
    pre_fitness = fitness  # snapshot for outcome delta
    print(f"    Fitness: {fitness.fitness:.1f}/100")
    print(f"    Claims: {fitness.claim_count} | Open Q: {fitness.open_questions} | "
          f"Experiments: {fitness.experiment_count}")
    print(f"    Trials: {fitness.trial_count} | Compute: {fitness.compute_minutes:.0f} min")
    print(f"    Density: {fitness.claim_density:.2f} | Coverage: {fitness.coverage_score:.2f} | "
          f"Productivity: {fitness.productivity:.2f}")

    # --- REFLECT ---
    print("\n  [2/8] REFLECT: analyzing trajectory...")
    reflection = reflect(fitness)
    print(f"    Delta: {reflection.fitness_delta:+.1f}")
    print(f"    Improving: {reflection.is_improving} | Plateauing: {reflection.is_plateauing}")
    for rec in reflection.recommendations:
        print(f"    -> {rec}")

    # --- MUTATE ---
    print("\n  [3/8] MUTATE: evolving strategy genome...")
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
    print("\n  [4/8] PLAN: generating experiment plan...")
    plan = generate_plan(genome, reflection, fitness, mode)
    print(f"    Planned experiments: {len(plan.experiments)}")
    for i, exp in enumerate(plan.experiments, 1):
        print(f"    {i}. [{exp['priority']:>6s}] {exp['type']}: {exp['description']}")

    # --- EXECUTE ---
    print("\n  [5/8] EXECUTE...")
    execution = execute_plan(plan, dry_run=dry_run)
    print(f"    Executed: {execution['experiments_executed']}/{len(plan.experiments)}")

    # --- COMPILE ---
    print("\n  [6/8] COMPILE: extracting claims from experiment data...")
    compile_result = None
    execution_produced_data = (
        not dry_run
        and execution.get("experiments_executed", 0) > 0
        and not execution.get("error")
    )
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
            else:
                print("    No new claims from overnight data (checking cortex path...)")
        except Exception as e:
            print(f"    [WARNING] Claim compilation failed: {e}")

        # Always re-evaluate fitness after execution produced data,
        # even if the claim compiler didn't find new overnight JSON.
        # The orchestrator's consolidation stage may have created new
        # raw proof packets with claims that evaluate_fitness() will see.
        if execution_produced_data or (compile_result and compile_result.proof_packet_updated):
            print("    Re-evaluating fitness after execution + compilation...")
            fitness = evaluate_fitness(cycle_id)
            print(f"    Updated fitness: {fitness.fitness:.1f}/100 "
                  f"(claims={fitness.claim_count}, open_q={fitness.open_questions})")
    else:
        print("    [DRY RUN] Skipping compilation.")

    # --- SYNTHESIZE (Phase 4: every 5 cycles) ---
    print("\n  [7/8] SYNTHESIZE: cross-experiment reasoning...")
    if not dry_run and cycle_id % 5 == 0:
        synthesis = _try_cross_experiment_synthesis(cycle_id)
        if synthesis:
            print(f"    Meta-patterns found: {len(synthesis.get('meta_patterns', []))}")
            print(f"    Contradictions: {len(synthesis.get('contradictions', []))}")
            print(f"    Critical experiments: {len(synthesis.get('critical_experiments', []))}")
            # Inject insights into genome for future planning
            genome = _load_genome()
            genome["synthesis_insights"] = {
                "cycle": cycle_id,
                "meta_patterns": synthesis.get("meta_patterns", [])[:5],
                "critical_experiments": synthesis.get("critical_experiments", [])[:3],
                "unifying_principles": synthesis.get("unifying_principles", [])[:3],
            }
            _save_genome(genome)
        else:
            print("    (LLM unavailable or insufficient data — skipped)")
    else:
        print(f"    (runs every 5 cycles — next at cycle {cycle_id + (5 - cycle_id % 5)})")

    # --- COMMIT ---
    print("\n  [8/8] COMMIT: persisting results...")
    log_fitness(fitness)
    log_cycle(cycle_id, fitness, reflection, plan, execution)
    _record_outcome(cycle_id, pre_fitness, fitness, plan, execution)
    print(f"    Fitness logged to {_FITNESS_LOG}")
    print(f"    Cycle logged to {_CYCLE_LOG}")
    print(f"    Outcome logged to {_OUTCOME_LEDGER}")
    print(f"    Genome saved to {_GENOME_FILE}")

    return fitness


def run_rsi(
    mode: str = "interactive",
    cycles: int = 1,
    budget_hours: float = 0.0,
    budget_dollars: float = 0.0,
    dry_run: bool = False
):
    """
    Run the RSI engine for N cycles or until budget exhausted.

    Args:
        mode: interactive, cron, or persistent.
        cycles: Max number of RSI cycles.
        budget_hours: Stop after this many hours (0 = unlimited).
        budget_dollars: Stop after this many USD in LLM costs (0 = unlimited).
        dry_run: Evaluate + plan only, no execution.
    """
    print("\n" + "=" * 70)
    print("  SOL RECURSIVE SELF-IMPROVEMENT ENGINE")
    print(f"  Mode: {mode} | Cycles: {cycles} | Budget: {budget_hours}h"
          + (f" / ${budget_dollars}" if budget_dollars > 0 else ""))
    print("=" * 70)

    # --- Crash-safe resume ---
    checkpoint = _load_checkpoint() if mode == "persistent" else None
    if checkpoint and checkpoint.get("mode") == mode:
        completed = checkpoint.get("completed_cycles", 0)
        print(f"\n  [RESUME] Found checkpoint: {completed} cycles completed previously.")
        resume_offset = completed
    else:
        resume_offset = 0

    # Determine starting cycle ID
    history = _load_fitness_history()
    start_cycle = len(history) + 1

    t0 = time.time()
    cost_at_start = _load_session_cost()
    results = []

    for i in range(resume_offset, cycles):
        cycle_id = start_cycle + (i - resume_offset)

        # --- Time budget check ---
        if budget_hours > 0:
            elapsed_hours = (time.time() - t0) / 3600
            if elapsed_hours >= budget_hours:
                print(f"\n  [STOP] Time budget exhausted ({elapsed_hours:.1f}h >= {budget_hours}h).")
                break

        # --- Cost budget check ---
        if budget_dollars > 0:
            cost_now = _load_session_cost()
            session_spend = cost_now - cost_at_start
            if session_spend >= budget_dollars:
                print(f"\n  [STOP] Cost budget exhausted (${session_spend:.3f} >= ${budget_dollars}).")
                break

        # --- Heartbeat ---
        _write_heartbeat(cycle_id, "running", {
            "cycle_index": i + 1,
            "total_cycles": cycles,
            "elapsed_sec": round(time.time() - t0, 1),
        })

        # --- Execute cycle ---
        try:
            fitness = rsi_cycle(cycle_id, mode=mode, dry_run=dry_run)
            results.append(fitness)
        except Exception as e:
            print(f"\n  [ERROR] Cycle {cycle_id} failed: {e}")
            import traceback
            traceback.print_exc()
            _write_heartbeat(cycle_id, "error", {"error": str(e)})
            if mode != "persistent":
                raise
            # In persistent mode, log the error and continue
            print("  [RECOVER] Persistent mode — continuing to next cycle...")
            continue

        # --- Checkpoint ---
        if mode == "persistent":
            _save_checkpoint({
                "mode": mode,
                "completed_cycles": i + 1,
                "total_cycles": cycles,
                "start_cycle": start_cycle,
                "last_fitness": fitness.fitness,
                "elapsed_sec": round(time.time() - t0, 1),
            })

        # --- Smart cooldown between cycles (persistent mode) ---
        if mode == "persistent" and i < cycles - 1:
            cooldown = _compute_cooldown(cycles_remaining=cycles - i - 1)
            print(f"\n  Cycle {cycle_id} complete. "
                  f"Cooling down {cooldown:.0f}s before next cycle...")
            _write_heartbeat(cycle_id, "cooldown", {
                "cooldown_sec": cooldown,
                "next_cycle_at": (
                    datetime.now(timezone.utc).isoformat()
                ),
            })
            time.sleep(cooldown)

    # --- Clean up ---
    _clear_checkpoint()
    _write_heartbeat(
        start_cycle + len(results) - 1 if results else start_cycle,
        "complete",
        {"total_cycles_run": len(results)},
    )

    # Final summary
    elapsed = time.time() - t0
    total_cost = _load_session_cost() - cost_at_start
    print(f"\n{'='*70}")
    print(f"  RSI SESSION COMPLETE")
    print(f"  Cycles: {len(results)} | Time: {elapsed:.0f}s | Cost: ${total_cost:.3f}")
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
  python rsi_engine.py --mode persistent --budget-dollars 1.0
  python rsi_engine.py --dry-run                    # Evaluate only
  python rsi_engine.py --status                     # Status report
        """
    )

    parser.add_argument("--mode", choices=["interactive", "cron", "persistent"],
                        default="interactive", help="Execution mode")
    parser.add_argument("--cycles", type=int, default=1, help="Number of RSI cycles")
    parser.add_argument("--budget-hours", type=float, default=0.0,
                        help="Maximum runtime in hours (0 = unlimited)")
    parser.add_argument("--budget-dollars", type=float, default=0.0,
                        help="Maximum LLM spend in USD (0 = unlimited)")
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
        budget_dollars=args.budget_dollars,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
