# Proof Packet — LatchIdentityV1 (last injector selects start basin)

## CLAIM
In LatchIdentityV1 runs, the start-basin readout at t0 (`rhoMaxId_t0`) equals the last injector used at dream stop (`lastInjector`).

## EVIDENCE
- Run IDs:
  - Aggregated in the export below; each row is one trial with an `injectorOrder`, `blocks`, and `lastInjector`.
- Export files:
  - `solData/testResults/sol_latchIdentity_2026-01-09T04-46-33-131Z.csv`
- Key metrics (from the export above; columns: `injectorOrder`, `blocks`, `lastInjector`, `rhoMaxId_t0`, `rhoMaxId_t0p15`):
  - Trial 0 (`injectorOrder=82|90`, `blocks=5`): `lastInjector=82`, `rhoMaxId_t0=82`, `rhoMaxId_t0p15=82`
  - Trial 1 (`injectorOrder=82|90`, `blocks=6`): `lastInjector=90`, `rhoMaxId_t0=90`, `rhoMaxId_t0p15=90`
  - Trial 2 (`injectorOrder=90|82`, `blocks=5`): `lastInjector=90`, `rhoMaxId_t0=90`, `rhoMaxId_t0p15=90`
  - Trial 3 (`injectorOrder=90|82`, `blocks=6`): `lastInjector=82`, `rhoMaxId_t0=82`, `rhoMaxId_t0p15=82`
- Notes about detector windows/definitions:
  - `rhoMaxId_t0` is the max-ρ node identity at t0, used as the start-basin readout.

## ASSUMPTIONS
- baselineMode:
  - Baseline restore is not recorded in this export; treat as unknown.
- dt/damp/pressC/capLawHash:
  - Not recorded in this export; treat as unknown.
- dashboard/harness version:
  - Not recorded in this export; treat as unknown.
- detector window positions:
  - Assumes “t0” is measured immediately after dream stop with `postSteps=0` semantics.
- session conditions:
  - Assumes `injectP=0`, `injectRho=400`, `injectPsi=0` were held constant across these trials (recorded columns).

## FALSIFY
- Run the same harness with controlled end-on-X (choose X) and `postSteps=0`.
- Falsification signature: any trial where `lastInjector = X` but `rhoMaxId_t0 != X`.

## STATUS
robust

## SOURCES
- [rd28.md](solKnowledge/working/rd28.md#L1)
