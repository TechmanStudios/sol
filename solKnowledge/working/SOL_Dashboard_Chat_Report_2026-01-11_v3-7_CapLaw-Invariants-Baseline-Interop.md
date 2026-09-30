# SOL Dashboard Chat Report — 2026-01-11

## Scope
This report consolidates the work completed in a single chat session focused on upgrading the SOL Dashboard from **v3.6 → v3.7** to prevent a specific failure mode:

- **Failure mode addressed:** baseline restores can re-pin `semanticMass` / `semanticMass0` and **skip CapLaw-derived recomputation**, preventing the system from reliably entering the intended **bus–rail manifold** (observed symptom: “90→92 dominating; bus rails never capture”).

The session’s objective was to make CapLaw and other derived fields effectively **non-optional** by enforcing a canonical recompute step after any restore path, and by exposing a minimal runtime API so external harness scripts and baseline tooling can’t bypass recompute.

## Non-negotiables (constraints honored)
- **UI-neutral behavior:** no new camera/graph movement (no `focus`, `fit`, `moveTo`, recenter/zoom mutations introduced).
- **Behavior preservation:** existing behavior was kept intact except where it conflicted with derived-field correctness.
- **Version bump:** all visible labels updated to v3.7.

## Primary deliverable
- Created a new dashboard artifact: **v3.7** saved as a separate single-file HTML.
- Kept the original **v3.6** file untouched.

### Files involved
- Source (unchanged): `sol_dashboard_v3_6.html`
- New artifact (created/edited): `sol_dashboard_v3_7.html`

## Summary of changes implemented (v3.7)

### 1) Version bump (v3.6 → v3.7)
Updated visible strings and examples:
- Page title bumped to v3.7.
- Console banner in the saccade harness bumped to v3.7.
- Example URL comments updated from `sol_dashboard_v3_6.html?...` to `sol_dashboard_v3_7.html?...`.

### 2) Added a Derived Fields Policy block (documentation + future toggle)
Added near `App.config.capLaw`:

- `App.config.derivedPolicy = { recomputeAfterRestore: true, derivedKeys: ["semanticMass","semanticMass0"], notes: ... }`

Purpose:
- Declare that `semanticMass` and `semanticMass0` are **derived invariants**, not baseline-trusted values.
- Provide a structured future toggle without changing current runtime behavior.

### 3) Introduced a single canonical derived-field recompute API
Added:

- `App.sim.recomputeDerivedFields(physics, opts = {})`

Behavior:
- If CapLaw is enabled, recompute applies it through the canonical path.
- Chooses `dtUsed` deterministically:
  - `opts.dt ?? App.config.capLaw.dt0 ?? App.config.dt ?? 0.12`
- Returns a compact report object:
  - `{ capLawApplied: boolean, dtUsed, capLawSig, capLawHash }`

Design intent:
- **One source of truth** for derived-field recompute.
- All restore/reload/interop paths route through this method so invariants cannot be bypassed.

### 4) Added a stable CapLaw signature + deterministic hash
Added two helpers:

- `App.sim.getCapLawSignature()`
  - Returns a stable JSON string of “physics-relevant” CapLaw parameters for apples-to-apples comparability.
  - Included keys:
    - `enabled`, `lawFamily`, `proxy`, `alpha`, `k0`, `dt0`, `kDtGamma`, `lambda`, `clampMin`, `clampMax`, `anchor.nodeId`, `anchor.smRef`, `includeBackgroundEdges`, `writeTo`

- `App.sim.hashStringDjb2(str)`
  - Simple deterministic hash (DJB2) used to produce `capLawHash` from the signature.

These values are included in `recomputeDerivedFields()` return output for logging and comparisons.

### 5) Replaced ad-hoc CapLaw applications with the canonical recompute function
Updated key call sites that previously did:

- `App.sim.applyCapLaw(App.state.physics, App.config.capLaw, App.config.capLaw?.dt0)`

and replaced them with:

- `App.sim.recomputeDerivedFields(App.state.physics)`

Locations updated:
- Boot sequence (`App.init`) pre-viz and post-Ouroboros
- `App.reloadGraph()` pre-viz and post-Ouroboros

Important note:
- Existing `try/catch` “no-op on failure” behavior was preserved.

### 6) Baseline interop hook (SOLBaseline restore cannot bypass recompute)
Implemented:

- `App.sim.installBaselineInterop(opts = {})`

What it does:
- Detects `window.SOLBaseline.restore()`.
- Wraps it exactly once (guard: `SOLBaseline.__solWrapped = true`).
- Calls original `restore(...)`.
- After restore completes, calls:
  - `App.sim.recomputeDerivedFields(App.state.physics)`
- Works for both sync and async restore results:
  - If restore returns a Promise, recompute happens in `.then(...)` / `.catch(...)` path.

Robustness for late-loading baseline:
- Installs at boot.
- Uses a short polling interval (default ~9s window) to wrap if SOLBaseline appears after page load.
- Also listens for an optional event hook: `sol:baseline-ready`.

### 7) Updated internal snapshot/restore helper to enforce recompute
Located a `restoreState(physics, snap)` helper that restores node fields including:
- `n.semanticMass = s.semanticMass`
- `n.semanticMass0 = s.semanticMass0`

After restore completes, added:
- `try { App.sim.recomputeDerivedFields(physics); } catch(e) {}`

Effect:
- Even if snapshots/baselines restore pinned mass values, the canonical derived policy re-applies CapLaw when enabled.

### 8) Exposed a minimal global runtime API for harnesses
Added `window.SOLRuntime` helpers:

- `SOLRuntime.recomputeDerived()`
  - Calls `App.sim.recomputeDerivedFields(App.state.physics)`

- `SOLRuntime.getInvariants()`
  - Returns:
    - `dt` (last tick dt, if available)
    - `pressC` and `damp` from sliders (or `null` if sliders not available)
    - `capLawSig` and `capLawHash`
    - `visibilityState` and `hidden`

Also added:
- `App.state.lastDtSec` captured each animation tick to support invariant logging.

## Acceptance tests (manual console checks)

### A) Recompute works and is callable
In browser console:
- `SOLRuntime.recomputeDerived()`

Expected:
- Returns an object containing:
  - `capLawApplied: true` (when CapLaw enabled)
  - `capLawSig` and `capLawHash`

### B) Baseline restore triggers recompute automatically
If SOLBaseline is loaded:
- `await SOLBaseline.restore()`

Expected:
- No errors
- `SOLRuntime.recomputeDerived().capLawHash` remains stable across repeated restores.

### C) reloadGraph still applies CapLaw (via recomputeDerivedFields)
Reload a graph (UI action or console entry used by the dashboard).

Expected:
- Graph loads
- Visualization renders
- CapLaw signature/hash is present

### D) No new camera movement
No new calls to recenter/zoom/focus were introduced as part of this upgrade.

## Notes and follow-ups
- Some existing camera movement utilities already existed in the file (e.g., internal focus/shift logic); they were **not modified** as part of the v3.7 work.
- If you have external harness scripts (Phase 3.8 runners, baseline tools, CSV exporters), the new `SOLRuntime.getInvariants()` is intended as the canonical logging hook going forward.

---

## Quick reference (APIs added)
- `App.config.derivedPolicy`
- `App.sim.getCapLawSignature()`
- `App.sim.hashStringDjb2(str)`
- `App.sim.recomputeDerivedFields(physics, opts)`
- `App.sim.installBaselineInterop(opts)`
- `window.SOLRuntime.recomputeDerived()`
- `window.SOLRuntime.getInvariants()`
