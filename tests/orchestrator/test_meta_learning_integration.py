from __future__ import annotations

from gap_detector import Gap
import hypothesis_templates
import run_loop


def test_meta_learning_reorders_ranked_gaps(monkeypatch):
    low_yield = Gap(
        gap_type="unexplored_param",
        priority=1,
        description="low yield gap",
        metadata={"param": "damping"},
    )
    high_yield = Gap(
        gap_type="unpromoted",
        priority=2,
        claim_id="CL-7",
        description="high yield gap",
    )

    class FakeMeta:
        def suggest_gap_priority_boost(self, gaps):
            return [gaps[1], gaps[0]]

    monkeypatch.setattr(run_loop, "scan_knowledge", lambda: [low_yield, high_yield])
    monkeypatch.setattr(run_loop, "rank_gaps", lambda gaps: gaps)

    session = run_loop.CortexSession(run_loop.SessionConfig(verbose=False))
    session._meta = FakeMeta()

    ranked = session.init()

    assert ranked == [high_yield, low_yield]


def test_preferred_template_guides_static_hypothesis(monkeypatch):
    monkeypatch.setattr(hypothesis_templates, "_try_llm_hypothesis", lambda *args, **kwargs: None)
    gap = {
        "gap_type": "unexplored_param",
        "preferred_template": "threshold_scan",
        "metadata": {"param": "damping"},
    }

    hypothesis = hypothesis_templates.generate_hypothesis(gap, "H-meta")

    assert hypothesis.id == "H-meta"
    assert hypothesis.template == "threshold_scan"


def test_invalid_preferred_template_falls_back(monkeypatch):
    monkeypatch.setattr(hypothesis_templates, "_try_llm_hypothesis", lambda *args, **kwargs: None)
    gap = {
        "gap_type": "unexplored_param",
        "preferred_template": "not_a_template",
        "metadata": {"param": "damping"},
    }

    hypothesis = hypothesis_templates.generate_hypothesis(gap, "H-fallback")

    assert hypothesis.template == "parameter_sweep"
