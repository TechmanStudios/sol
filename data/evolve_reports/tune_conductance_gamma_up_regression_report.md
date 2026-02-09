# SOL Evolution Report: tune_conductance_gamma_up

**Date:** 2026-02-08 04:19 UTC
**Verdict:** IMPROVE
**Runtime:** 5.4s

## Candidate Details

- **Name:** tune_conductance_gamma_up
- **Type:** param_tune
- **Target:** conductance
- **Sacred Math Impact:** none

**Description:** Increase conductance psi-sensitivity from 0.75 to 1.0

**Hypothesis:** Higher gamma should make psi routing more selective, potentially sharpening basin formation.

**Parameters changed:**
- `conductance_gamma` → `1.0`

**Expected improvements:**
- Sharper entropy gradients between basins
- Faster basin lock-in

**Acceptable regressions:**
- Slightly lower total flux (more selective routing)

---

## Regression Results

### single_inject_baseline

#### Condition: `baseline`
**Verdict:** IMPROVE — 2 metrics improved, 0 regressions

**Final checkpoint (step 300):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.985735 | 0.987023 | +0.1307% | ✓ |
| totalFlux | 1.311033 | 1.164246 | -11.1963% | ✗ |
| mass | 29.992099 | 29.734557 | -0.8587% | ✓ |
| maxRho | 0.382003 | 0.312947 | -18.0774% | ✗ |
| activeCount | 127.000000 | 127.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=132, candidate=132 (match ✓)

### damping_sweep_smoke

#### Condition: `damping=0.05`
**Verdict:** IMPROVE — 2 metrics improved, 0 regressions

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.804756 | 0.821067 | +2.0268% | ✓ |
| totalFlux | 6.966144 | 7.067550 | +1.4557% | ✓ |
| mass | 45.255505 | 45.127465 | -0.2829% | ✓ |
| maxRho | 13.737507 | 12.803725 | -6.7973% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.1`
**Verdict:** IMPROVE — 1 metrics improved, 0 regressions

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.802231 | 0.818987 | +2.0887% | ✓ |
| totalFlux | 6.877613 | 6.975256 | +1.4197% | ✓ |
| mass | 42.862288 | 42.698079 | -0.3831% | ✓ |
| maxRho | 13.131403 | 12.213620 | -6.9892% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.2`
**Verdict:** IMPROVE — 2 metrics improved, 0 regressions

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.797864 | 0.815515 | +2.2124% | ✓ |
| totalFlux | 6.700689 | 6.790189 | +1.3357% | ✓ |
| mass | 38.499715 | 38.273504 | -0.5876% | ✓ |
| maxRho | 11.977050 | 11.091154 | -7.3966% | ✓ |
| activeCount | 128.000000 | 128.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

#### Condition: `damping=0.5`
**Verdict:** IMPROVE — 1 metrics improved, 0 regressions

**Final checkpoint (step 200):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.790732 | 0.811111 | +2.5772% | ✓ |
| totalFlux | 6.167300 | 6.228819 | +0.9975% | ✓ |
| mass | 28.141593 | 27.793940 | -1.2354% | ✓ |
| maxRho | 8.941703 | 8.150614 | -8.8472% | ✓ |
| activeCount | 110.000000 | 117.000000 | +6.3636% | ✓ |

**RhoMaxId:** golden=1, candidate=1 (match ✓)

### dual_inject_timing

#### Condition: `baseline`
**Verdict:** IMPROVE — 2 metrics improved, 0 regressions

**Final checkpoint (step 300):**

| Metric | Golden | Candidate | Delta | Within Tol |
|--------|--------|-----------|-------|-----------|
| entropy | 0.985735 | 0.987023 | +0.1307% | ✓ |
| totalFlux | 1.311033 | 1.164246 | -11.1963% | ✗ |
| mass | 29.992099 | 29.734557 | -0.8587% | ✓ |
| maxRho | 0.382003 | 0.312947 | -18.0774% | ✗ |
| activeCount | 127.000000 | 127.000000 | +0.0000% | ✓ |

**RhoMaxId:** golden=132, candidate=132 (match ✓)

---

## Summary

- **Overall Verdict:** IMPROVE
- **Conditions tested:** 6
- **PASS:** 0
- **IMPROVE:** 6
- **REGRESS:** 0
- **MIXED:** 0

> **RECOMMENDATION:** This candidate shows improvement without regression. Consider promoting to a proof-packet-backed claim.