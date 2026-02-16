# SOL Evolution Report: tune_psi_relax_base

**Date:** 2026-02-16 00:22 UTC
**Verdict:** PASS
**Runtime:** 3.89s

## Candidate Details

- **Name:** tune_psi_relax_base
- **Type:** param_tune
- **Target:** psi
- **Sacred Math Impact:** none

**Description:** Increase psi relax rate from 0.12 to 0.20

**Hypothesis:** Faster relaxation toward bias should help nodes return to baseline psi quicker.

**Parameters changed:**
- `psi_relax_base` → `0.2`

**Expected improvements:**
- Faster recovery after perturbation
- More distinct group boundaries

**Acceptable regressions:**
- Less dynamic psi response to injections

---

## Regression Results

### single_inject_baseline

#### Condition: `baseline`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 300):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.985735 | 0.985755 | +0.0020% | ✓ |
| totalFlux | 1.311033 | 1.310268 | -0.0583% | ✓ |
| mass | 29.992099 | 29.989743 | -0.0079% | ✓ |
| maxRho | 0.382003 | 0.381580 | -0.1106% | ✓ |
| activeCount | 127.000000 | 127.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=132, candidate=132 (match ✓)

### damping_sweep_smoke

#### Condition: `damping=0.05`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.804756 | 0.804823 | +0.0084% | ✓ |
| totalFlux | 6.966144 | 6.967336 | +0.0171% | ✓ |
| mass | 45.255505 | 45.253366 | -0.0047% | ✓ |
| maxRho | 13.737507 | 13.733663 | -0.0280% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.1`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.802231 | 0.802301 | +0.0087% | ✓ |
| totalFlux | 6.877613 | 6.878800 | +0.0173% | ✓ |
| mass | 42.862288 | 42.860111 | -0.0051% | ✓ |
| maxRho | 13.131403 | 13.127618 | -0.0288% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.2`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.797864 | 0.797938 | +0.0092% | ✓ |
| totalFlux | 6.700689 | 6.701824 | +0.0169% | ✓ |
| mass | 38.499715 | 38.497478 | -0.0058% | ✓ |
| maxRho | 11.977050 | 11.973384 | -0.0306% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.5`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.790732 | 0.790819 | +0.0110% | ✓ |
| totalFlux | 6.167300 | 6.168289 | +0.0160% | ✓ |
| mass | 28.141593 | 28.139264 | -0.0083% | ✓ |
| maxRho | 8.941703 | 8.938388 | -0.0371% | ✓ |
| activeCount | 110.000000 | 110.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

### dual_inject_timing

#### Condition: `baseline`
**Verdict:** PASS — Candidate produces results within tolerance of golden

**Final checkpoint (step 300):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.985735 | 0.985755 | +0.0020% | ✓ |
| totalFlux | 1.311033 | 1.310268 | -0.0583% | ✓ |
| mass | 29.992099 | 29.989743 | -0.0079% | ✓ |
| maxRho | 0.382003 | 0.381580 | -0.1106% | ✓ |
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