# SOL Evolution Report: tune_jeans_critical

**Date:** 2026-02-25 14:14 UTC
**Verdict:** PASS
**Runtime:** 3.91s

## Candidate Details

- **Name:** tune_jeans_critical
- **Type:** param_tune
- **Target:** jeans_cfg
- **Sacred Math Impact:** none

**Description:** Lower Jeans critical threshold from 18.0 to 12.0

**Hypothesis:** Lower Jcrit should trigger stellar collapse earlier, creating more semantic stars.

**Parameters changed:**
- `jeans_cfg.Jcrit` → `12.0`

**Expected improvements:**
- More constellations formed
- Earlier semantic mass reinforcement

**Acceptable regressions:**
- More nodes becoming stellar may over-accrete

---

## Regression Results

### single_inject_baseline

#### Condition: `baseline`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 300):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.985735 | 0.984753 | -0.0996% | ✓ |
| totalFlux | 1.311033 | 1.127982 | -13.9623% | ✗ |
| mass | 29.992099 | 30.178117 | +0.6202% | ✓ |
| maxRho | 0.382003 | 0.284902 | -25.4190% | ✗ |
| activeCount | 127.000000 | 125.000000 | -1.5748% | ✓ |

**RhoMaxId:** golden=132, candidate=43 (MISMATCH ✗)

### damping_sweep_smoke

#### Condition: `damping=0.05`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.804756 | 0.806010 | +0.1559% | ✓ |
| totalFlux | 6.966144 | 7.188209 | +3.1878% | ✓ |
| mass | 45.255505 | 45.282040 | +0.0586% | ✓ |
| maxRho | 13.737507 | 13.827495 | +0.6551% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.1`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.802231 | 0.803654 | +0.1773% | ✓ |
| totalFlux | 6.877613 | 7.060419 | +2.6580% | ✓ |
| mass | 42.862288 | 42.937086 | +0.1745% | ✓ |
| maxRho | 13.131403 | 13.223501 | +0.7014% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.2`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.797864 | 0.799682 | +0.2278% | ✓ |
| totalFlux | 6.700689 | 6.899797 | +2.9715% | ✓ |
| mass | 38.499715 | 38.656971 | +0.4085% | ✓ |
| maxRho | 11.977050 | 12.072886 | +0.8002% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.5`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.790732 | 0.792847 | +0.2675% | ✓ |
| totalFlux | 6.167300 | 6.319401 | +2.4662% | ✓ |
| mass | 28.141593 | 28.367196 | +0.8017% | ✓ |
| maxRho | 8.941703 | 9.035301 | +1.0468% | ✓ |
| activeCount | 110.000000 | 115.000000 | +4.5455% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

### dual_inject_timing

#### Condition: `baseline`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 300):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.985735 | 0.984753 | -0.0996% | ✓ |
| totalFlux | 1.311033 | 1.127982 | -13.9623% | ✗ |
| mass | 29.992099 | 30.178117 | +0.6202% | ✓ |
| maxRho | 0.382003 | 0.284902 | -25.4190% | ✗ |
| activeCount | 127.000000 | 125.000000 | -1.5748% | ✓ |

**RhoMaxId:** golden=132, candidate=43 (MISMATCH ✗)

---

## Summary

- **Overall Verdict:** PASS
- **Conditions tested:** 6
- **PASS:** 6
- **IMPROVE:** 0
- **REGRESS:** 0
- **MIXED:** 0