"""
SOL LLM — Prompt Library
===========================
Domain-specific prompt templates for the SOL RSI pipeline.

Each prompt function assembles a system prompt + user prompt pair,
grounded in the SOL engine's physics and research context.

Prompt categories:
  1. HYPOTHESIS GENERATION — Gap → novel, falsifiable hypothesis
  2. RESULT INTERPRETATION — Experiment JSON → semantic analysis
  3. CLAIM DRAFTING — Interpreted results → structured claims
  4. CONSOLIDATION — Session findings → proof packet drafts
  5. QUESTION GENERATION — Knowledge gaps → new research questions
  6. CROSS-EXPERIMENT REASONING — Multiple results → meta-patterns
"""
from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# Shared system context — injected into all SOL prompts
# ---------------------------------------------------------------------------

SOL_SYSTEM_CONTEXT = """\
You are an autonomous research scientist working on the SOL Engine — a \
discrete phonon-Faraday simulation on a fixed 140-node directed graph. \
The engine models energy (rho) flowing through nodes connected by \
conductance-weighted edges, governed by:

  - Discrete Faraday induction: ΔΦ/Δt → EMF → current flow
  - Pressure-driven redistribution: ΔP = c_press · Σ(ρ_in - ρ_out)
  - Damping: per-step energy dissipation factor (0 = no loss, 84 = total loss)
  - Conservation of mass: total ρ is strictly conserved (injection adds, nothing removes)

Key observables:
  - entropy: Shannon entropy of ρ distribution across 140 nodes
  - mass: total ρ in the system (conserved)
  - maxRho / rhoMaxId: peak density node (dominant basin)
  - totalFlux: net energy flow per step
  - activeCount: nodes with ρ > threshold

Known regime structure:
  - damping 0-10: turbulent, high-entropy regime
  - damping 10-15: transition zone
  - damping 15-40: "dead zone" — poorly understood, low activity
  - damping 40-55: re-activation zone
  - damping 55-84: extinction approach

The core graph (default_graph.json) and engine (sol_engine.py) are IMMUTABLE. \
All experiments observe the system; none modify its laws. \
Claims must be backed by specific trial data with reproducible parameters.
"""


# ===================================================================
# 1. HYPOTHESIS GENERATION
# ===================================================================

def hypothesis_prompt(
    gap: dict,
    knowledge_context: str = "",
    existing_claims: str = "",
    genome_state: dict | None = None,
    prior_hypotheses: list[dict] | None = None,
    available_templates: list[dict] | None = None,
) -> tuple[str, str]:
    """
    Generate a system + user prompt for LLM-powered hypothesis creation.

    Args:
        gap: Knowledge gap dict (gap_type, description, metadata, etc.)
        knowledge_context: Relevant excerpts from proof packets / claims
        existing_claims: Summary of current claim ledger
        genome_state: Current RSI genome (template preferences, etc.)
        prior_hypotheses: Previously generated hypotheses this session (for diversity)
        available_templates: List of experiment template types the engine supports

    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = SOL_SYSTEM_CONTEXT + """
Your task is to generate a NOVEL, FALSIFIABLE hypothesis for a SOL engine \
experiment. The hypothesis must:
1. Address a specific knowledge gap
2. Specify an independent variable (knob) and its test values
3. Include concrete falsification criteria
4. Be executable as a headless engine run (no GUI needed)
5. Go beyond simple parameter sweeps when possible — think about WHY \
   the system behaves as it does

Respond with a JSON object:
{
  "question": "One-sentence falsifiable question",
  "knob": "primary independent variable name",
  "knob_values": [list of test values],
  "injection": {"label": "node_name", "amount": energy_value},
  "steps": number_of_simulation_steps,
  "reps": number_of_repetitions,
  "falsifiers": ["condition that would disprove this hypothesis", ...],
  "rationale": "Why this experiment matters and what it could reveal",
  "predicted_outcome": "What you expect to observe if hypothesis is correct",
  "novelty": "How this differs from existing experiments"
}

IMPORTANT: Your hypothesis MUST be DIFFERENT from any prior hypotheses listed \
below. Use a different knob, different parameter range, or a fundamentally \
different experimental approach. Vary the injection target, step count, and \
experimental design — do NOT repeat the same template or question.
"""

    user_parts = [
        "## Knowledge Gap to Address",
        f"- **Type:** {gap.get('gap_type', 'unknown')}",
        f"- **Description:** {gap.get('description', 'No description')}",
        f"- **Priority:** {gap.get('priority', 'unknown')}",
    ]

    if gap.get("claim_id"):
        user_parts.append(f"- **Related claim:** {gap['claim_id']}")

    if gap.get("suggested_action"):
        user_parts.append(f"- **Suggested action:** {gap['suggested_action']}")

    meta = gap.get("metadata", {})
    if meta:
        user_parts.append(f"- **Metadata:** {json.dumps(meta, indent=2)}")

    if knowledge_context:
        user_parts.extend([
            "",
            "## Relevant Knowledge Context",
            knowledge_context,
        ])

    if existing_claims:
        user_parts.extend([
            "",
            "## Existing Claims (avoid duplication)",
            existing_claims,
        ])

    if genome_state:
        prefs = genome_state.get("template_preferences", {})
        top_prefs = sorted(prefs.items(), key=lambda x: x[1], reverse=True)[:5]
        user_parts.extend([
            "",
            "## Current Research Strategy (genome)",
            f"- Top template preferences: {top_prefs}",
            f"- Exploration rate: {genome_state.get('exploration_rate', 0.2)}",
            f"- Frontier types: {genome_state.get('experiment_types', {}).get('scope_frontier', [])}",
        ])

    if prior_hypotheses:
        user_parts.extend([
            "",
            "## Prior Hypotheses This Session (DO NOT REPEAT)",
        ])
        for i, ph in enumerate(prior_hypotheses, 1):
            user_parts.append(
                f"{i}. [{ph.get('template', '?')}] knob={ph.get('knob', '?')} "
                f"question: {ph.get('question', '?')[:120]}"
            )
        user_parts.append("")
        user_parts.append(
            f"You MUST choose a DIFFERENT approach from all {len(prior_hypotheses)} "
            "hypotheses above. Use a different knob, different template type, or "
            "a fundamentally different experimental design."
        )

    if available_templates:
        user_parts.extend([
            "",
            "## Available Experiment Templates",
            "Choose the most appropriate template type for your hypothesis:",
        ])
        for tmpl in available_templates:
            user_parts.append(f"- **{tmpl['name']}**: {tmpl.get('description', '')}")

    user_parts.extend([
        "",
        "Generate a hypothesis that addresses this gap. Be creative but grounded.",
        "Return ONLY the JSON object.",
    ])

    return system, "\n".join(user_parts)


# ===================================================================
# 2. RESULT INTERPRETATION
# ===================================================================

def interpretation_prompt(
    experiment_data: dict,
    hypothesis: dict | None = None,
    knowledge_context: str = "",
) -> tuple[str, str]:
    """
    Generate prompts for LLM-powered experiment result interpretation.

    Args:
        experiment_data: Parsed experiment JSON (conditions, metrics, sanity)
        hypothesis: The hypothesis that drove this experiment
        knowledge_context: Relevant existing claims/findings

    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = SOL_SYSTEM_CONTEXT + """
Your task is to interpret SOL engine experiment results. You must:
1. Identify meaningful patterns in the data (not just describe it)
2. Explain WHAT happened and WHY (mechanistic reasoning)
3. Connect findings to existing knowledge (confirm, refute, or extend)
4. Flag any anomalies or unexpected behaviors
5. Assess whether any falsification criteria were triggered

Respond with a JSON object:
{
  "summary": "2-3 sentence executive summary of what was found",
  "key_findings": [
    {"finding": "description", "evidence": "specific data points", "confidence": 0.0-1.0}
  ],
  "mechanistic_explanation": "Why does the system behave this way?",
  "connections_to_known": ["How this relates to existing claim X", ...],
  "anomalies": ["Unexpected observation", ...],
  "falsifiers_triggered": ["Which falsification criteria were met, if any"],
  "suggested_followup": ["Next experiment that would deepen understanding"],
  "claim_candidates": [
    {"claim": "Precise claim statement", "evidence": "Supporting data", "confidence": 0.0-1.0}
  ]
}
"""

    user_parts = ["## Experiment Results"]

    # Include hypothesis context
    if hypothesis:
        user_parts.extend([
            "",
            "### Hypothesis",
            f"- **Question:** {hypothesis.get('question', 'Unknown')}",
            f"- **Knob:** {hypothesis.get('knob', 'Unknown')}",
            f"- **Values tested:** {hypothesis.get('knob_values', [])}",
            "",
            "### Falsification Criteria",
        ])
        for f in hypothesis.get("falsifiers", []):
            user_parts.append(f"- {f}")

    # Summarize results compactly
    user_parts.extend(["", "### Results Data"])

    # Summary
    summary = experiment_data.get("summary", {})
    if summary:
        user_parts.append(f"- Conditions: {summary.get('total_conditions', '?')}")
        user_parts.append(f"- Reps: {summary.get('total_reps', '?')}")
        user_parts.append(f"- Steps: {summary.get('total_steps', '?')}")
        user_parts.append(f"- Runtime: {summary.get('runtime_sec', '?')}s")

    # Sanity checks
    sanity = experiment_data.get("sanity", {})
    if sanity:
        user_parts.append(f"- Sanity: {'PASS' if sanity.get('all_passed') else 'FAIL'} "
                          f"({sanity.get('failures', 0)} failures)")

    # Per-condition final metrics (compact table)
    conditions = experiment_data.get("conditions", {})
    if conditions:
        user_parts.append("")
        user_parts.append("### Per-Condition Final Metrics")
        for label, cdata in conditions.items():
            fm = cdata.get("final_metrics", {})
            parts = [f"{k}={v}" for k, v in fm.items()
                     if k not in ("condition", "rep") and isinstance(v, (int, float))]
            user_parts.append(f"  [{label}] {', '.join(parts[:8])}")

    # Comparison
    comparison = experiment_data.get("comparison", {})
    if comparison:
        user_parts.extend([
            "",
            "### Cross-Condition Comparison",
            json.dumps(comparison, indent=2, default=str)[:2000],
        ])

    if knowledge_context:
        user_parts.extend([
            "",
            "## Existing Knowledge for Context",
            knowledge_context[:3000],
        ])

    user_parts.extend([
        "",
        "Interpret these results. Focus on mechanistic understanding, not just reporting.",
        "Return ONLY the JSON object.",
    ])

    return system, "\n".join(user_parts)


# ===================================================================
# 3. CLAIM DRAFTING
# ===================================================================

def claim_draft_prompt(
    interpretation: dict,
    experiment_source: str = "",
    existing_claims: str = "",
    trial_count: int = 0,
) -> tuple[str, str]:
    """
    Generate prompts to draft formal claims from interpreted results.

    Args:
        interpretation: Output from the interpretation step
        experiment_source: File/session identifier
        existing_claims: Current claim table for dedup checking
        trial_count: Number of supporting trials

    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = SOL_SYSTEM_CONTEXT + """
Your task is to draft formal, evidence-backed CLAIMS for the SOL proof packet. \
Each claim must:
1. Be a precise, falsifiable statement about the SOL engine's behavior
2. Cite specific parameter values, metric ranges, and trial counts
3. Include an evidence summary suitable for a research log
4. NOT duplicate existing claims (check the existing claims list)
5. Be conservative — only claim what the data robustly supports

Respond with a JSON object:
{
  "claims": [
    {
      "claim_text": "Precise claim statement with parameters",
      "evidence": "Supporting evidence including trial counts, parameter ranges, key metrics",
      "confidence": 0.0-1.0,
      "pattern": "BASIN_STABILITY | ENTROPY_PROFILE | GATE_FUNCTIONAL | NOISE_RESILIENCE | CAPACITY_BITS | CASCADE_FIDELITY | ENERGY_THRESHOLD | DEAD_ZONE_LOCK | NOVEL",
      "parameters": {"key": "value pairs from the experiment"},
      "suggested_tag": "C-auto-NN format"
    }
  ],
  "open_questions": [
    "Questions raised by these findings that warrant future experiments"
  ],
  "dedup_notes": "Which existing claims this overlaps with, if any"
}
"""

    user_parts = [
        "## Interpreted Results",
        f"- **Source:** {experiment_source}",
        f"- **Trials:** {trial_count}",
        "",
        "### Summary",
        interpretation.get("summary", "No summary"),
        "",
        "### Key Findings",
    ]

    for kf in interpretation.get("key_findings", []):
        user_parts.append(f"- [{kf.get('confidence', 0):.0%}] {kf.get('finding', '')}")
        user_parts.append(f"  Evidence: {kf.get('evidence', '')}")

    user_parts.extend([
        "",
        "### Mechanistic Explanation",
        interpretation.get("mechanistic_explanation", "None provided"),
        "",
        "### Candidate Claims from Interpretation",
    ])
    for cc in interpretation.get("claim_candidates", []):
        user_parts.append(f"- {cc.get('claim', '')} (confidence: {cc.get('confidence', 0):.0%})")

    if existing_claims:
        user_parts.extend([
            "",
            "## Existing Claims (DO NOT DUPLICATE)",
            existing_claims[:3000],
        ])

    user_parts.extend([
        "",
        "Draft formal claims. Be conservative — only claim what the data strongly supports.",
        "Return ONLY the JSON object.",
    ])

    return system, "\n".join(user_parts)


# ===================================================================
# 4. CONSOLIDATION — Proof Packet Enhancement
# ===================================================================

def consolidation_prompt(
    session_findings: list[dict],
    raw_proof_packets: list[str],
    domain_packet_summary: str = "",
) -> tuple[str, str]:
    """
    Generate prompts for LLM-powered proof packet consolidation.

    Args:
        session_findings: List of finding dicts from cortex session
        raw_proof_packets: Content of raw proof packet markdown files
        domain_packet_summary: Summary of existing domain packet

    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = SOL_SYSTEM_CONTEXT + """
Your task is to synthesize cortex session findings into a coherent update \
for the SOL domain proof packet. You must:
1. Identify which findings strengthen, extend, or challenge existing claims
2. Draft new experiment sections with proper formatting
3. Suggest claim table updates (new rows or status changes)
4. Propose updates to open questions (resolved, partially answered, or new)
5. Maintain the rigorous, evidence-based tone of the proof packet

Respond with a JSON object:
{
  "new_experiment_sections": [
    {"title": "Experiment N: Description", "content": "Markdown content with parameters, results, and analysis"}
  ],
  "claim_updates": [
    {"action": "add|strengthen|challenge", "claim_id": "C-nn or new", "text": "claim text", "evidence": "summary"}
  ],
  "question_updates": [
    {"question_number": N, "status": "resolved|partially_answered|still_open", "evidence": "what was found"}
  ],
  "new_questions": [
    "New research questions raised by these findings"
  ],
  "synthesis_notes": "How these findings connect to the broader research narrative"
}
"""

    user_parts = [
        "## Cortex Session Findings",
        "",
    ]

    for i, finding in enumerate(session_findings, 1):
        user_parts.extend([
            f"### Finding {i}",
            f"- Hypothesis: {finding.get('question', 'Unknown')}",
            f"- Knob: {finding.get('knob', 'Unknown')}",
            f"- Sanity: {'PASS' if finding.get('sanity_passed') else 'FAIL'}",
            f"- Claim anchor: {finding.get('claim_id', 'exploratory')}",
            "",
        ])

    if raw_proof_packets:
        user_parts.extend([
            "## Raw Proof Packet Content",
            "(These are the auto-generated packets from this session)",
            "",
        ])
        for pp in raw_proof_packets[:3]:  # Limit to 3 to control context size
            user_parts.append(pp[:2000])
            user_parts.append("")

    if domain_packet_summary:
        user_parts.extend([
            "## Current Domain Packet Summary",
            domain_packet_summary[:3000],
            "",
        ])

    user_parts.extend([
        "Synthesize these findings. Focus on what is genuinely NEW and significant.",
        "Return ONLY the JSON object.",
    ])

    return system, "\n".join(user_parts)


# ===================================================================
# 5. QUESTION GENERATION
# ===================================================================

def question_generation_prompt(
    current_questions: list[str],
    recent_findings: str = "",
    coverage_gaps: list[str] | None = None,
) -> tuple[str, str]:
    """
    Generate prompts for LLM-powered research question generation.

    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = SOL_SYSTEM_CONTEXT + """
Your task is to generate novel, productive research questions about the \
SOL engine. Each question should:
1. Be answerable by a headless engine experiment
2. Target an unexplored aspect of the system's behavior
3. Build on existing findings (not repeat already-answered questions)
4. Be specific enough to design a concrete experiment around

Respond with a JSON object:
{
  "questions": [
    {
      "question": "Precise research question",
      "rationale": "Why this matters and what it could reveal",
      "experiment_type": "parameter_sweep | threshold_scan | injection_comparison | ...",
      "priority": "HIGH | MEDIUM | LOW",
      "estimated_effort": "quick (< 5 min) | medium (5-30 min) | deep (30+ min)"
    }
  ]
}
"""

    user_parts = [
        "## Currently Open Questions",
    ]

    if current_questions:
        for i, q in enumerate(current_questions, 1):
            user_parts.append(f"{i}. {q}")
    else:
        user_parts.append("(All current questions are resolved)")

    if recent_findings:
        user_parts.extend([
            "",
            "## Recent Findings",
            recent_findings[:3000],
        ])

    if coverage_gaps:
        user_parts.extend([
            "",
            "## Known Coverage Gaps",
        ])
        for gap_desc in coverage_gaps:
            user_parts.append(f"- {gap_desc}")

    user_parts.extend([
        "",
        "Generate 3-5 novel research questions that would advance SOL understanding.",
        "Avoid duplicating existing open questions.",
        "Return ONLY the JSON object.",
    ])

    return system, "\n".join(user_parts)


# ===================================================================
# 6. STRATEGIC REFLECTION
# ===================================================================

def strategic_reflection_prompt(
    fitness_trajectory: list[dict],
    outcome_history: list[dict],
    genome_state: dict,
    open_questions: list[str] | None = None,
    raw_leads: list[dict] | None = None,
) -> tuple[str, str]:
    """
    Generate prompts for LLM-powered strategic reflection.

    Instead of rule-based "plateau detected", the LLM analyzes the full
    fitness trajectory, outcome history, and genome state to produce deep
    strategic recommendations for the next RSI cycle.

    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = SOL_SYSTEM_CONTEXT + """
Your task is to act as a STRATEGIC ADVISOR for a recursive self-improvement \
(RSI) loop running autonomous experiments on the SOL engine. Analyze the \
research trajectory and recommend the most productive next steps.

You have access to:
1. Fitness trajectory — recent fitness scores showing trend
2. Outcome history — which experiment types produced new claims vs nothing
3. Current genome — template weights, exploration rate, frontier types
4. Open questions — unresolved research threads

Your analysis should:
1. Diagnose WHY the current trajectory is what it is (plateauing, improving, regressing)
2. Identify which experiment types are most productive and which are dead ends
3. Recommend specific strategic shifts (not generic "try new things")
4. Suggest parameter regions or experiment types that are underexplored
5. Propose a priority ordering for the next 3-5 cycles

Respond with a JSON object:
{
  "diagnosis": "What is happening with the research trajectory and why",
  "productive_templates": ["templates that are working well"],
  "dead_templates": ["templates that should be deprioritized"],
  "strategic_shifts": [
    {"action": "specific change to make", "rationale": "why this will help"}
  ],
  "priority_experiments": [
    {"type": "experiment type", "target": "specific parameter or question", "priority": "HIGH|MEDIUM|LOW"}
  ],
  "genome_recommendations": {
    "mutation_rate": 0.0-1.0,
    "exploration_rate": 0.0-1.0,
    "template_boosts": {"template_name": delta_value},
    "template_dims": {"template_name": delta_value}
  },
  "meta_insight": "One-sentence insight about the research program overall direction"
}
"""

    user_parts = ["## Fitness Trajectory (recent cycles)"]
    for entry in fitness_trajectory[-10:]:
        user_parts.append(
            f"  Cycle {entry.get('cycle_id', '?')}: "
            f"fitness={entry.get('fitness', 0):.1f} "
            f"claims={entry.get('claim_count', 0)} "
            f"open_q={entry.get('open_questions', 0)}"
        )

    user_parts.extend(["", "## Outcome History (what each cycle produced)"])
    for oc in outcome_history[-10:]:
        delta = oc.get("delta", {})
        user_parts.append(
            f"  Cycle {oc.get('cycle_id', '?')}: "
            f"templates={oc.get('templates_planned', [])} "
            f"claim_delta={delta.get('claims', 0):+d} "
            f"fitness_delta={delta.get('fitness', 0):+.2f} "
            f"executed={oc.get('experiments_executed', 0)}"
        )

    user_parts.extend(["", "## Current Genome State"])
    prefs = genome_state.get("template_preferences", {})
    sorted_prefs = sorted(prefs.items(), key=lambda x: x[1], reverse=True)
    for name, weight in sorted_prefs:
        user_parts.append(f"  {name}: {weight:.2f}")
    user_parts.append(f"  mutation_rate: {genome_state.get('mutation_rate', 0.15)}")
    user_parts.append(f"  exploration_rate: {genome_state.get('exploration_rate', 0.2)}")

    frontier = genome_state.get("experiment_types", {}).get("scope_frontier", [])
    if frontier:
        user_parts.append(f"  frontier_types: {frontier}")

    if open_questions:
        user_parts.extend(["", "## Open Research Questions"])
        for i, q in enumerate(open_questions, 1):
            user_parts.append(f"  {i}. {q}")

    if raw_leads:
        user_parts.extend(["", "## Unexplored Raw Leads"])
        for lead in raw_leads[:5]:
            user_parts.append(
                f"  - {lead.get('topic', '?')} [{lead.get('status', '?')}] "
                f"params={lead.get('parameters', [])}"
            )

    user_parts.extend([
        "",
        "Analyze this trajectory and provide strategic recommendations.",
        "Be specific and actionable — not generic advice.",
        "Return ONLY the JSON object.",
    ])

    return system, "\n".join(user_parts)


# ===================================================================
# 7. CROSS-EXPERIMENT REASONING
# ===================================================================

def cross_experiment_prompt(
    experiment_summaries: list[dict],
    claim_ledger_excerpt: str = "",
) -> tuple[str, str]:
    """
    Generate prompts for reasoning across multiple experiments.

    Returns:
        (system_prompt, user_prompt) tuple
    """
    system = SOL_SYSTEM_CONTEXT + """
Your task is to reason across MULTIPLE SOL engine experiments to identify \
meta-patterns, contradictions, and emergent insights that no single \
experiment reveals alone. You must:
1. Look for correlations across different parameter regimes
2. Identify potential unifying principles
3. Flag contradictions between experiments
4. Propose experiments that would test cross-cutting hypotheses

Respond with a JSON object:
{
  "meta_patterns": [
    {"pattern": "description", "supporting_experiments": ["exp1", "exp2"], "confidence": 0.0-1.0}
  ],
  "contradictions": [
    {"claim_a": "from experiment X", "claim_b": "from experiment Y", "resolution_hypothesis": "..."}
  ],
  "unifying_principles": [
    {"principle": "description", "scope": "which regime/parameters", "evidence": "..."}
  ],
  "critical_experiments": [
    {"experiment": "description", "what_it_would_resolve": "which pattern/contradiction"}
  ]
}
"""

    user_parts = [
        "## Experiment Summaries",
        "",
    ]

    for i, exp in enumerate(experiment_summaries, 1):
        user_parts.extend([
            f"### Experiment {i}: {exp.get('title', 'Unknown')}",
            f"- Type: {exp.get('type', 'Unknown')}",
            f"- Key findings: {exp.get('findings', 'None')}",
            f"- Parameters: {exp.get('parameters', {})}",
            f"- Trials: {exp.get('trials', 0)}",
            "",
        ])

    if claim_ledger_excerpt:
        user_parts.extend([
            "## Current Claim Ledger",
            claim_ledger_excerpt[:3000],
            "",
        ])

    user_parts.extend([
        "Reason across ALL experiments above. What patterns emerge?",
        "Return ONLY the JSON object.",
    ])

    return system, "\n".join(user_parts)


# ===================================================================
# Convenience: Prompt Library class
# ===================================================================

class PromptLibrary:
    """Namespace for all SOL LLM prompt generators."""
    hypothesis = staticmethod(hypothesis_prompt)
    interpretation = staticmethod(interpretation_prompt)
    claim_draft = staticmethod(claim_draft_prompt)
    consolidation = staticmethod(consolidation_prompt)
    question_generation = staticmethod(question_generation_prompt)
    strategic_reflection = staticmethod(strategic_reflection_prompt)
    cross_experiment = staticmethod(cross_experiment_prompt)
