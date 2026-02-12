# SOL Overnight RSI — Q13-Q15 Investigation Report

**Run timestamp:** 20260211_075419
**Total runtime:** 181.4s (0.05h)
**Total trials:** 79
**Budget used:** 100.0%

## Suite Runtimes

| Suite | Runtime |
|-------|--------:|
| q13 | 181.4s (3.0m) |

---

## q13_structural_census

### Correlations

| Metric | r |
|--------|--:|
| eigenvector_vs_flicker | 0.5405 |
| degree_vs_flicker | 0.3946 |
| betweenness_vs_flicker | 0.3275 |
| clustering_vs_flicker | -0.1336 |

---

## Provisional Answers

### Q13: What structural property determines heavy flickerers?

_See q13_structural_census.json and q13_basin_boundary.json for full data._
_Check the `best_predictor` field in each result for the winning metric._

### Q14: Can d=50 basins be predicted analytically?

_See q14_accuracy.json for prediction accuracy across methods._
_Compare static, phase-gated, and multi-hop prediction strategies._

### Q15: Can any intervention close the identity gap?

_See q15_param_tuning.json, q15_topology_surgery.json, etc._
_Look for the largest positive delta in self-attraction %._

---

*Report generated at 2026-02-11T07:57:20.505097+00:00*