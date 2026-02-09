# SOL Pipeline Contract
*Run Bundle → Analysis Pack → Promotion (Compiler)*

This contract makes the SOL lab workflow behave like an auditable machine instead of a rumor mill.

---

## 0) Purpose
Define the **required inputs/outputs** and **minimum metadata** for each pipeline stage so:
- every result is reconstructible,
- comparisons are valid,
- claims can be promoted without guessing.

---

## 1) Roles and responsibilities

### 1.1 Experiment Runner
**Goal:** Execute protocols consistently and produce exports + a Run Bundle that fully describes what happened.

### 1.2 Data Analyst
**Goal:** Turn exports into sanity-checked derived results suitable for promotion.

### 1.3 Knowledge Compiler
**Goal:** Convert run bundles + analysis packs into canonical knowledge: RN/RD notes, proof packets, master-log inserts, and manifest updates.

---

## 2) Stage 1 Output: RUN BUNDLE (required)
**Artifact type:** Markdown  
**Template:** `.github/prompts/run-bundle-template.md`

### 2.1 Must include (minimum contract fields)
**Identity**
- seriesName
- runIDs
- dashboardVersion
- harnessSchema
- baselineModeUsed
- operator

**Invariants (explicit)**
- dt
- damp
- pressC
- capLawHash
- detectorWindows (or `[UNKNOWN]`)
- repsPerCell

**Protocol**
- step-by-step schedule (holds/pulses/settles) sufficient to re-run

**Knobs (independent variables)**
- what was varied and the tested levels

**Exports (filenames)**
- `*_MASTER_summary.csv`
- `*_MASTER_busTrace.csv` (if produced)
- `*_repTransition_curve.csv` (if produced)
- any other exports + part manifests

**Deviations / Incidents**
- crashes, restarts, manual interventions, mid-run changes

**External artifact registration**
- where bulky exports were stored (if not in repo)
- whether manifest entry is needed

### 2.2 Contract fail conditions (Run Bundle)
Fail the handoff if any are missing:
- baselineModeUsed
- at least one export filename
- runIDs (or an explicit `[UNKNOWN]` with explanation)
- invariants list (can include `[UNKNOWN]`, but must be present)

---

## 3) Stage 2 Output: ANALYSIS PACK (required)
**Artifact types:**
- `analysis_report_<series>.md`
- `derived_tables_<series>.csv`
- (optional) `analyze_<series>.py` (Python preferred)

### 3.1 Must include (minimum analysis requirements)
**Inputs used**
- exact filenames + runIDs referenced (no vague references)

**Sanity checks (must appear before interpretation)**
- invariants check: confirm invariants are constant across compared conditions  
  - if not constant, mark comparisons as confounded
- sample size check: reps per cell, missing cells
- detector/window check: clipping, saturation, window sensitivity
- order-effect confound check where plausible (AB/BA or reasoning)

**Primary results**
- tables of the key dependent variable(s) (winner probability / timing / threshold bracket / basin selection)
- uncertainty or stability notes (even if qualitative)

### 3.2 Contract fail conditions (Analysis Pack)
Fail the handoff if:
- it interprets before sanity checks
- it merges multiple run series without explicit provenance
- it doesn’t cite the exact input files
- it assumes detector semantics without stating source or marking `[UNKNOWN]`

---

## 4) Stage 3 Output: PROMOTION PACK (Compiler output)
**Artifact types:**
- RN/RD note (Markdown)
- proof packets (in RN/RD or separate doc)
- master-log insert snippet (Markdown)
- external manifest update notes (if applicable)

### 4.1 Promotion prerequisites
A claim may be promoted only if:
- it has runIDs + export filenames
- it has measured metrics (not just narrative)
- baseline handling is consistent across compared conditions OR baseline is explicitly treated as a knob
- detector/window artifacts are ruled out or the claim is marked provisional

### 4.2 Proof packet format (required)
Each promoted claim must be written as:
- CLAIM
- EVIDENCE (runIDs, filenames, metrics, where in files)
- ASSUMPTIONS (invariants, baseline mode, versioning)
- FALSIFY (smallest breaking test)
- STATUS (provisional | supported | robust | deprecated)

### 4.3 Contract fail conditions (Promotion)
Fail promotion if:
- missing runIDs or filenames
- missing baseline mode
- orphan artifact references (not in repo and not in manifest)
- mixing evidence and interpretation without tags

---

## 5) Progress reporting format (required for agents)
For any multi-step task, report:
- NOW: what was done
- INPUTS USED: exact artifacts referenced
- OUTPUTS PRODUCED: artifacts emitted
- OPEN ITEMS: remaining `[UNKNOWN]` / unverified points
- NEXT ACTIONS: minimal steps (max 5)

---

## 6) Quick “Definition of Done”
A run series is “done” when:
1) Run Bundle exists and is complete  
2) Analysis Pack exists with sanity checks + derived tables  
3) Compiler has produced RN/RD + proof packets + master-log insert  
4) External artifacts are referenced in the manifest (if any)

---
