"""
End-to-end test: agent calls auto_run programmatically.
Verifies the full Phase 1 pipeline works from Python imports.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_run import execute_protocol
from analysis.metrics import summarize_condition, compare_conditions, time_to_threshold
from analysis.sanity import run_standard_checks

# ---- Test 1: Programmatic protocol execution ----
protocol = {
    "seriesName": "api_test",
    "question": "Does the API work end-to-end?",
    "invariants": {"dt": 0.12, "c_press": 0.1, "rng_seed": 42},
    "knobs": {"damping": [0.1, 0.3]},
    "injections": [{"label": "grail", "amount": 50}],
    "steps": 100,
    "reps": 2,
    "baseline": "fresh",
    "metrics_every": 5,
}

results = execute_protocol(protocol)

# Verify structure
assert "summary" in results, "Missing summary"
assert "conditions" in results, "Missing conditions"
assert "sanity" in results, "Missing sanity"
assert "run_bundle" in results, "Missing run_bundle"
assert results["sanity"]["all_passed"], f"Sanity failed: {results['sanity']}"
assert len(results["conditions"]) == 2, f"Expected 2 conditions, got {len(results['conditions'])}"

# Verify comparison exists (>1 condition)
assert results["comparison"] is not None, "Comparison should exist for multi-condition"

# Verify mass ordering: lower damping → higher mass
conds = list(results["conditions"].items())
mass_0 = conds[0][1]["final_metrics"]["mass"]
mass_1 = conds[1][1]["final_metrics"]["mass"]
assert mass_0 > mass_1, f"Lower damping should retain more mass: {mass_0} vs {mass_1}"

print("Test 1: Programmatic protocol execution — PASS")

# ---- Test 2: Metrics analysis functions ----
trace = results["conditions"][conds[0][0]].get("analysis", {})
assert "entropy" in trace, "Analysis should contain entropy stats"
assert trace["entropy"]["count"] > 0, "Should have entropy data points"

print("Test 2: Metrics analysis — PASS")

# ---- Test 3: time_to_threshold ----
# Build a simple time series
fake_rows = [{"entropy": i * 0.1, "step": i} for i in range(10)]
idx = time_to_threshold(fake_rows, "entropy", 0.5, "above")
assert idx == 5, f"Expected step 5, got {idx}"

print("Test 3: time_to_threshold — PASS")

# ---- Test 4: Run bundle is valid Markdown ----
bundle = results["run_bundle"]
assert "# RUN BUNDLE" in bundle, "Run bundle should have header"
assert "api_test" in bundle, "Run bundle should contain series name"
assert "Sanity Checks" in bundle, "Run bundle should have sanity section"

print("Test 4: Run bundle generation — PASS")

# ---- Test 5: Single condition (no knobs) ----
single_protocol = {
    "seriesName": "single_test",
    "question": "Single condition test",
    "invariants": {"dt": 0.12, "c_press": 0.1, "damping": 0.2, "rng_seed": 42},
    "injections": [{"label": "grail", "amount": 50}],
    "steps": 50,
    "baseline": "fresh",
}

single_results = execute_protocol(single_protocol)
assert single_results["sanity"]["all_passed"], "Single condition should pass sanity"
assert len(single_results["conditions"]) == 1, "Should have exactly 1 condition"
assert single_results["comparison"] is None, "No comparison for single condition"

print("Test 5: Single condition (no knobs) — PASS")

print("\n=== All Phase 1 API tests PASSED ===")
