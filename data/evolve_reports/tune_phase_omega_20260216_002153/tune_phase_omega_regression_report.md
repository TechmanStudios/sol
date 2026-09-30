# SOL Evolution Report: tune_phase_omega

**Date:** 2026-02-16 00:21 UTC
**Verdict:** PASS
**Runtime:** 3.9s

## Candidate Details

- **Name:** tune_phase_omega
- **Type:** param_tune
- **Target:** phase_cfg
- **Sacred Math Impact:** none

**Description:** Increase lighthouse frequency from 0.15 to 0.25

**Hypothesis:** Faster oscillation should create more frequent surface/deep exchange, potentially improving mixing.

**Parameters changed:**
- `phase_cfg.omega` → `0.25`

**Expected improvements:**
- More even mass distribution
- Faster convergence

**Acceptable regressions:**
- May reduce phase-gated separation effects

---

## Regression Results

### single_inject_baseline

#### Condition: `baseline`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 300):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.985735 | 0.985594 | -0.0143% | ✓ |
| totalFlux | 1.311033 | 1.312370 | +0.1020% | ✓ |
| mass | 29.992099 | 29.862082 | -0.4335% | ✓ |
| maxRho | 0.382003 | 0.381135 | -0.2273% | ✓ |
| activeCount | 127.000000 | 127.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=132, candidate=132 (match ✓)

### damping_sweep_smoke

#### Condition: `damping=0.05`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.804756 | 0.803551 | -0.1497% | ✓ |
| totalFlux | 6.966144 | 6.995513 | +0.4216% | ✓ |
| mass | 45.255505 | 45.075774 | -0.3971% | ✓ |
| maxRho | 13.737507 | 13.736578 | -0.0068% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.1`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.802231 | 0.800998 | -0.1537% | ✓ |
| totalFlux | 6.877613 | 6.905930 | +0.4117% | ✓ |
| mass | 42.862288 | 42.690824 | -0.4000% | ✓ |
| maxRho | 13.131403 | 13.130563 | -0.0064% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.2`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.797864 | 0.796575 | -0.1616% | ✓ |
| totalFlux | 6.700689 | 6.726883 | +0.3909% | ✓ |
| mass | 38.499715 | 38.343174 | -0.4066% | ✓ |
| maxRho | 11.977050 | 11.976369 | -0.0057% | ✓ |
| activeCount | 128.000000 | 127.000000 | -0.7812% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.5`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.790732 | 0.789281 | -0.1836% | ✓ |
| totalFlux | 6.167300 | 6.188132 | +0.3378% | ✓ |
| mass | 28.141593 | 28.019761 | -0.4329% | ✓ |
| maxRho | 8.941703 | 8.941370 | -0.0037% | ✓ |
| activeCount | 110.000000 | 110.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

### dual_inject_timing

#### Condition: `baseline`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 300):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.985735 | 0.985594 | -0.0143% | ✓ |
| totalFlux | 1.311033 | 1.312370 | +0.1020% | ✓ |
| mass | 29.992099 | 29.862082 | -0.4335% | ✓ |
| maxRho | 0.382003 | 0.381135 | -0.2273% | ✓ |
| activeCount | 127.000000 | 127.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=132, candidate=132 (match ✓)

---

## Summary

- **Overall Verdict:** PASS
- **Conditions tested:** 6
- **PASS:** 6
- **IMPROVE:** 0
- **REGRESS:** 0
- **MIXED:** 0