# PP-2026-01-24 — ψ Resonance A (25Hz tick): square-wave cadence shifts rho90_frac

## CLAIM
In `sol_H82_90_psiResonanceA_25HzTick_V1_summary_2026-01-07T21-14-56-862Z.csv`, for `pattern=strobe`, `dreamBudgetRhoPerTick=240`, `psiMode=square`, `psiAmp=1`, `psiBias=0`, `psiDC=0` (with `psiMean=-0.02`, `psiRMS=1` in both rows), increasing `psiFreqHz` from 6 → 9 reduces `rho90_frac` from 0.4958333 → 0.4729167 (Δ=-0.0229167).

## EVIDENCE
- Run IDs:
  - (Not recorded in the export filename; this packet is anchored to export filenames + in-file parameters.)
- Export files:
  - `solData/testResults/sol_H82_90_psiResonanceA_25HzTick_V1_summary_2026-01-07T21-14-56-862Z.csv`
- Key metrics (values + where in the file):
  - Row 1 (cadence = 6 Hz):
    - `pattern=strobe`, `dreamBudgetRhoPerTick=240`, `psiMode=square`, `psiFreqHz=6`, `psiAmp=1`, `psiBias=0`, `psiDC=0`, `psiMean=-0.02`, `psiRMS=1`
    - Outcomes: `rho90_frac=0.49583333333333335`, `rho82_frac=0.5041666666666667`, `rhoSwitch_frac=0.4948766467921026`
  - Row 2 (cadence = 9 Hz):
    - `pattern=strobe`, `dreamBudgetRhoPerTick=240`, `psiMode=square`, `psiFreqHz=9`, `psiAmp=1`, `psiBias=0`, `psiDC=0`, `psiMean=-0.02`, `psiRMS=1`
    - Outcomes: `rho90_frac=0.47291666666666665`, `rho82_frac=0.5270833333333333`, `rhoSwitch_frac=0.47486423858631244`
  - Derived comparison:
    - Δ `rho90_frac` (9 Hz − 6 Hz) = -0.022916666666666696

## ASSUMPTIONS
- `rho90_frac` is the fraction of samples/time assigned to the rho=90 basin/state in this experiment series, and its semantics are stable within this export.
- The two rows are directly comparable because they match on `pattern`, `dreamBudgetRhoPerTick`, `psiMode`, `psiAmp`, `psiBias`, `psiDC`, `psiMean`, and `psiRMS`, differing only in `psiFreqHz`.

## FALSIFY
- Re-run the ψ Resonance A protocol with the same settings and export a summary with the same columns.
- Expected failure signature: the direction/magnitude does not reproduce (e.g., `rho90_frac` at 9 Hz is equal to or greater than at 6 Hz by more than noise).
- How it would appear in exports: matched rows (same controls as above) show Δ `rho90_frac` close to 0 or with the opposite sign.

## STATUS
provisional
