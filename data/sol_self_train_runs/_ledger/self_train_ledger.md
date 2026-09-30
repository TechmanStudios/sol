# Self-Train Consolidation Ledger

Generated: 2026-02-17T07:02:42.593028+00:00
Root: data/sol_self_train_runs

## Global

- Total runs: 9
- Total generations: 1138
- Accepted generations: 25
- Acceptance rate: 2.20%

## By Mode

| Mode | Runs | Gens | Accepted | Acceptance | Best dA | Mean dA | Best dF | Mean dF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fast | 2 | 6 | 2 | 33.33% | 0.0192 | 0.0012 | 0.0184 | 0.0009 |
| full | 3 | 1103 | 21 | 1.90% | 0.1789 | -0.3121 | 0.1191 | -0.2301 |
| overnight | 4 | 29 | 2 | 6.90% | 0.0141 | -0.0022 | 0.0110 | -0.0014 |

## Top Runs by Anchor Delta

| Source | Mode | Run | Gens | Best dA | Latest dA | Latest dF |
|---|---|---|---:|---:|---:|---:|
| github-actions | full | 22053459642 | 1000 | 0.1789 | -0.0226 | -0.0197 |
| github-actions | full | 22052118217 | 100 | 0.0238 | 0.0013 | -0.0000 |
| github-actions | fast | 22083103067 | 3 | 0.0192 | -0.0191 | -0.0175 |
| github-actions | fast | 22051991831 | 3 | 0.0191 | -0.0194 | -0.0176 |
| github-actions | full | 22052059066 | 3 | 0.0163 | -0.0193 | -0.0262 |
| github-actions | overnight | 22088819534 | 13 | 0.0141 | -0.0036 | 0.0046 |
| github-actions | overnight | 22053054662 | 10 | 0.0042 | -0.0027 | -0.0035 |
| github-actions | overnight | 22052842191 | 3 | 0.0023 | -0.0043 | -0.0073 |
| github-actions | overnight | 22085408552 | 3 | -0.0025 | -0.0070 | -0.0089 |

## Promotion Ready Runs

- github-actions/fast/22051991831 (best dA=0.0191, best dF=0.0184)
- github-actions/fast/22083103067 (best dA=0.0192, best dF=0.0176)
- github-actions/full/22052059066 (best dA=0.0163, best dF=0.0232)
- github-actions/full/22052118217 (best dA=0.0238, best dF=0.0230)
- github-actions/full/22053459642 (best dA=0.1789, best dF=0.1191)
- github-actions/overnight/22088819534 (best dA=0.0141, best dF=0.0110)

## Near Miss Runs

- github-actions/overnight/22053054662 (best dA=0.0042, latest reason: Anchor delta -0.0027 below minimum 0.0050)
- github-actions/overnight/22052842191 (best dA=0.0023, latest reason: Anchor delta -0.0043 below minimum 0.0050)
- github-actions/overnight/22085408552 (best dA=-0.0025, latest reason: Anchor delta -0.0070 below minimum 0.0050)
