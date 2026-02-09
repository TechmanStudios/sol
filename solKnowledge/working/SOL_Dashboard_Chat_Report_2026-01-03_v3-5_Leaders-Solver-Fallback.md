# SOL Dashboard Chat Report — v3.5 Leaders (Solver-Based Fallback)

Date compiled: 2026-01-15

Chat date (chronological anchor): 2026-01-03

Scope: This report covers the work in this chat thread focused on fixing/augmenting SOL Dashboard v3.5 “leaderboard” logic so console leader queries do not return empty results. The change adds a solver-based fallback that computes leaderboards directly from the live physics solver (nodes/edges/flux), and updates the console print helper to use that output.

---

## 1) Executive summary

Goal (user request):

- Integrate an additional JavaScript block into the dashboard HTML so `solMotion.getLeaders()` computes meaningful leaderboards directly from the solver, rather than relying on precomputed arrays that may be missing/empty.

Outcome:

- `window.solMotion.getLeaders()` is overridden with a solver-based implementation that:
  - Reads the active solver from `window.solver` or `window.SOLDashboard.state.physics`.
  - Computes triangle-circulation statistics (circulation proxy) and a normalized “vorticity” proxy.
  - Maintains a persistent EMA baseline per node so z-scores become meaningful over time.
- `window.solMotion.dumpLeaders()` was updated to print from `solMotion.getLeaders()` results (rather than `phy.topK_*`), so the console tables match the fallback.

---

## 2) Files modified

- `g:\docs\TechmanStudios\sol\sol_dashboard_v3_5.html`

No new files were created as part of the dashboard code change itself.

---

## 3) What the dashboard had before this patch

Inside the v3.5 vis-network setup, the dashboard already exposed console hooks:

- `window.solNetwork` — the vis-network instance
- `window.solVisNodes` / `window.solVisEdges` — vis DataSets
- `window.solMotion` — a small console utility object

`window.solMotion.getLeaders()` existed, but it primarily returned arrays from `App.state.physics` (examples):

- `phy.topK_vortNorm_hotNow`
- `phy.topK_circAbs_hotNow`

Problem:

- If the physics engine did not populate those `topK_*` arrays yet (or they were disabled/empty), `solMotion.getLeaders()` returned empty sets, making console inspection confusing.

---

## 4) What we added (solver-based fallback)

### 4.1 Placement / integration strategy

We integrated the provided logic in a safe place where required globals already exist:

- Inserted immediately after the existing `window.solMotion = { ... }` hook is created.
- This ensures `window.SOLDashboard` and the physics solver are already available (or will become available soon).

Implementation detail:

- The patch is wrapped in an IIFE that overrides `solMotion.getLeaders` while preserving the rest of `solMotion` (enable/disable/pulse/tractorStep).

### 4.2 Solver selection

The fallback locates the active solver using:

- `window.solver` (if present), else
- `window.SOLDashboard?.state?.physics`

This matches the runtime reality that different dashboard versions sometimes expose the physics solver under different globals.

### 4.3 Graph flux adjacency model

The fallback builds a lightweight adjacency representation from `solver.edges`:

- Ignores background edges (`e.background`) to focus on meaningful structure.
- Stores:
  - `neigh`: undirected neighbor lists
  - `und`: an undirected edge set for quick “does j–k exist?” checks
  - `flow`: a directed flux map where `a->b = flux` and `b->a = -flux`

This representation enables quick triangle sampling without requiring additional indices from the main engine.

### 4.4 Metric definitions (as implemented)

Two metrics are computed per node:

1) **Circulation magnitude (triangle-based)**

- For a node `i`, the code randomly samples neighbor pairs `(j,k)` where triangle `(i,j,k)` exists.
- For each triangle, it computes the signed loop sum:

  - `cij + cjk + cki`

  where each term is read from `flow`.

- Stores `circAbsMean` as the mean absolute loop sum over sampled triangles.

2) **Normalized vorticity proxy**

- Computes incident flux scale:

  - `inc = Σ |flux|` over edges incident to the node

- Defines:

  - `vort = circ / (inc + EPS)`

This creates a dimensionless “how rotational is this node relative to how much flux touches it?” proxy.

### 4.5 Baselines + z-scores (EMA + abs deviation)

To make leaders “temporal” (hot-now vs persistent), the patch keeps a cache:

- `solMotion._leaderCache.vort` (Map per node)
- `solMotion._leaderCache.circ` (Map per node)

For each node and metric, it maintains:

- `mu`: EMA mean
- `absDev`: EMA absolute deviation

Then it derives:

- `sigma ≈ 1.2533 * absDev` (normal-ish scaling)
- `z = (x - mu) / sigma`

This supports:

- Hot-now: high `|z|`
- Surges: high positive `z`
- Drops: large negative `z`
- Persistent: high `ema` (mu)
- Hybrid: `0.65 * ema + 0.35 * current`

### 4.6 Filtering rules

To avoid noisy artifacts, the fallback skips nodes that are:

- `n.background` or `n.isBattery`
- synth nodes by multiple checks:
  - `n.group === "synth"` or `n.type === "synth"` or `n.isSynth`

---

## 5) Console helper update: dumpLeaders()

We updated `window.solMotion.dumpLeaders({k, which})` to:

- Call `window.solMotion.getLeaders({ k, which })`
- Print the returned arrays (vort and/or circ) using the existing `console.table` formatting

This removes dependency on `phy.topK_*` fields and guarantees that `dumpLeaders()` reflects the fallback’s computed results.

The label resolution behavior was preserved:

- Prefer `visNodes.get(id).label` if available
- Else prefer `phy.nodes` label
- Else fallback to stringified id

---

## 6) How to use / verify

In the browser console:

- Compute leaders (returns object with `vort` and `circ` packs):
  - `solMotion.getLeaders({ k: 5, which: 'both' })`

- Quick “is it empty?” sanity check:
  - `solMotion.getLeaders({ k: 5 }).vort.hotNow.length`

- Print formatted leaderboards:
  - `solMotion.dumpLeaders({ k: 10, which: 'both' })`

Note: Because baselines are EMA-based, the first call for a node initializes its baseline and will show `z = 0` for that metric. Subsequent calls become more informative as the cache learns.

---

## 7) Notes / implications

- The fallback uses random triangle sampling (`Math.random()`), so results are “stable-ish” over time but not strictly deterministic per call.
- It intentionally focuses on non-background edges to avoid all-to-all dilution.
- Because the cache is stored on `window.solMotion`, it persists for the page lifetime and improves as the simulation runs.

---

## 8) Deliverable recap

- v3.5 dashboard now has a reliable, solver-based `solMotion.getLeaders()` fallback and a `dumpLeaders()` that prints those results.
- This resolves the practical issue: leaderboards should no longer be empty simply because the solver didn’t precompute `topK_*` arrays.
