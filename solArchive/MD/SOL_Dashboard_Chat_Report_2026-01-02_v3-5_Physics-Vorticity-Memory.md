# SOL Dashboard Chat Report — v3.5 Physics / Vorticity / Memory Upgrade

Date compiled: 2026-01-15

Chat date (chronological anchor): 2026-01-02

Primary artifact modified: `g:\docs\TechmanStudios\sol\sol_dashboard_v3_5.html`

Scope: This report covers the work and discussion in this chat thread centered on SOL v3.5: promoting canonical (graph-native) vorticity into the physics engine, making Jeans collapse taxonomy-independent, adding long-term per-node “memory channels” (EMA), adding multiple leaderboards (Hot Now / Surges / Drops / Persistent / Hybrid), upgrading Hot Now to a variance-aware z-score using mean+mean-absolute-deviation tracking, and adding a small console helper for inspecting leaderboards.

Related report (same chronological anchor, different thread focus):

- v3.0–v3.2 merge line + Binary Battery + Lighthouse Protocol + Logos Console: `SOL_Dashboard_Chat_Report_2026-01-02.md`

---

## 1) Executive summary

This thread pushed SOL’s “metrics and meaning” closer to the engine.

Key outcomes:

- **Canonical vorticity is now a physics variable**, derived from **flux circulation in short cycles (triangles)**, rather than inferred from screen-space layout motion.
- **Jeans collapse is now physics-threshold based for any node**, not only constellation taxonomy nodes.
- **SOLPhysics now retains long-term state** relevant to “identity” and “flow memory”:
  - swirl hotspot memory (`vortNorm_ema[nodeId]`)
  - circulation magnitude memory (`circAbs_ema[nodeId]`)
  - river memory (`fluxAbs_ema[nodeId]`)
- **Leaderboards exist in multiple modes**:
  - “Hot Now” (anomaly/surprise) via z-score vs baseline
  - directional Hot Surges / Hot Drops
  - “Persistent Attractors” (EMA hall-of-fame)
  - Hybrid score (0.65 EMA + 0.35 current)
- Added a **console helper**: `solMotion.dumpLeaders()` for fast inspection.

---

## 2) Core conceptual decision: “meaning lives in flux, not layout”

We explicitly separated two notions of rotation:

1) **Canonical/semantic vorticity (meaningful)**
- Defined as a proxy for curl/circulation in the *graph*.
- Computed from **edge flux** around short cycles.
- Stored and evolved **inside `SOLPhysics`**.

2) **Layout omega (diagnostic-only)**
- Screen-space angular drift of node positions.
- Useful as a *health/solver diagnostic* during dream/settle windows.
- Not treated as meaning-bearing.

The engine now publishes canonical vorticity to `window.SOLMetrics.vorticity_cycle` / `_ema`, while `vorticity_layout` remains diagnostic.

---

## 3) Chronological timeline (what happened in this chat)

### 3.1 Promote vorticity into SOLPhysics

- Added engine-side vorticity config and storage:
  - `vortCfg` with sampling parameters and EMA settings
  - `vortNorm_local` (Map of nodeId → local circulation magnitude proxy)
  - `vortNorm_global` and `vortNorm_global_ema` (EMA of top‑K local values)
- Implemented `SOLPhysics.updateVorticityFromFlux(dt)`:
  - Builds adjacency and directed flux lookup from current edge flux.
  - Samples triangles rooted at each node, computing circulation:
    - `circ = flux(i→j) + flux(j→k) + flux(k→i)`
  - Stores per-node local magnitude as `n.vortNorm_local` and in `vortNorm_local`.
  - Computes top‑K mean and updates global EMA.

### 3.2 Move canonical vorticity publication to use engine data

- Updated the UI loop to publish:
  - `SOLMetrics.vorticity_cycle = physics.vortNorm_global`
  - `SOLMetrics.vorticity_cycle_ema = physics.vortNorm_global_ema`
- Left the older helper `computeVorticityCycle()` in the file (currently unused), to avoid a broad refactor mid-stream.

### 3.3 Make Jeans collapse taxonomy-independent

Previously Jeans collapse logic only applied to nodes with `isConstellation`.

Change:

- Any node with $J = \rho / (|p| + \epsilon) \ge J_{crit}$ can promote.
- Promotions:
  - If a node wasn’t a constellation and crosses the threshold:
    - `isConstellation = true`
    - `protoStar = true`
  - If it crosses the threshold:
    - `isStellar = true`

Intent: collapse is determined by physics thresholds, not compiler taxonomy.

### 3.4 Add long-term memory channels inside SOLPhysics

Added per-node EMA “memory” maps:

- `vortNorm_ema: Map(nodeId → float)` — swirl hotspot memory
- `circAbs_ema: Map(nodeId → float)` — circulation magnitude memory
- `fluxAbs_ema: Map(nodeId → float)` — river memory (incident |flux|)

Implementation notes:

- `fluxAbs_ema` uses incident flux sum (for each node, sum of `|edge.flux|` over incident edges).
- These memory channels are updated inside `updateVorticityFromFlux()`.

### 3.5 Add leaderboards: Hot Now vs Persistent vs Hybrid

We added an explicit split:

- **Persistent Attractors**: rank by EMA
- **Hot Now**: rank by anomaly score
- **Hybrid**: rank by `0.65*EMA + 0.35*current`

Leaderboards are updated periodically (default `0.75s`) to avoid constant sorting cost.

### 3.6 Upgrade “Hot Now” to variance-aware z-score

Hot Now ranking was upgraded from a simple relative deviation to a more robust baseline comparison.

Added:

- `SOLPhysics.updateMeanAbsDev(state, x, a=0.05, b=0.05)`
- Per-node state maps:
  - `vortNorm_zState: Map(nodeId → {mu, absDev})`
  - `circAbs_zState: Map(nodeId → {mu, absDev})`

Computation:

- Update baseline mean: `mu ← mu + a*(x - mu)`
- Update mean absolute deviation: `absDev ← absDev + b*(|x-mu| - absDev)`
- Convert to sigma: `sigma = 1.2533 * absDev` (robust-ish)
- Z-score: `z = (x - mu) / sigma`

### 3.7 Surface negative anomalies (drops) as first-class

We agreed on directional channels and implemented them:

- Keep signed z as core signal.
- Define:
  - `z_pos = max(0, z)`
  - `z_neg = max(0, -z)`
  - `z_abs = |z|`

Leaderboards now include:

- Hot Now: rank by `z_abs`
- Hot Surges: rank by `z_pos`
- Hot Drops: rank by `z_neg`

### 3.8 Add console helper for quick inspection

Added on `window.solMotion`:

- `solMotion.getLeaders()` — returns the raw leaderboard arrays from the active physics instance.
- `solMotion.dumpLeaders({ k=10, which='both'|'vort'|'circ' })` — prints tables to the console.
  - Includes ↑/↓ direction indicators.
  - Displays label (from vis nodes if available) plus metrics:
    - `score`, `z`, `z_abs`, `z_pos`, `z_neg`, `current`, `ema`, `mu`, `sigma`.

---

## 4) Current engine storage (as-built)

### 4.1 Per-node storage

- Local instantaneous:
  - `node.vortNorm_local` (also in `physics.vortNorm_local` Map)
- EMA “memory”:
  - `physics.vortNorm_ema.get(nodeId)`
  - `physics.circAbs_ema.get(nodeId)`
  - `physics.fluxAbs_ema.get(nodeId)`
- Z-score baseline state:
  - `physics.vortNorm_zState.get(nodeId) → {mu, absDev}`
  - `physics.circAbs_zState.get(nodeId) → {mu, absDev}`

### 4.2 Global storage

- Canonical vorticity aggregate:
  - `physics.vortNorm_global`
  - `physics.vortNorm_global_ema`

### 4.3 Leaderboards

Vorticity:

- `topK_vortNorm_hotNow`
- `topK_vortNorm_hotSurge`
- `topK_vortNorm_hotDrop`
- `topK_vortNorm_persistent`
- `topK_vortNorm_hybrid`

Circulation:

- `topK_circAbs_hotNow`
- `topK_circAbs_hotSurge`
- `topK_circAbs_hotDrop`
- `topK_circAbs_persistent`
- `topK_circAbs_hybrid`

Entry schema (per leaderboard row):

- `{ id, current, ema, score, z, z_pos, z_neg, z_abs, sigma, mu, direction }`

Back-compat:

- `topK_vortNorm` and `topK_circAbs` remain populated and now mirror the persistent (EMA) attractor lists.

---

## 5) Configuration knobs added

Inside `SOLPhysics.vortCfg`:

- `pairsPerNode` — neighbor-pair attempts when searching for closeable triangles
- `trianglesPerNode` — number of triangle samples per node
- `topK` — global aggregation K (also used for leaderboard length)
- `emaAlpha` — EMA update rate for vorticity and memory channels
- `leaderboardIntervalSec` — how often leaderboards re-sort
- `zMuAlpha` — alpha for baseline mean update
- `zAbsDevAlpha` — alpha for baseline absDev update

---

## 6) Practical usage / “how to inspect”

From the browser console:

- Dump everything:
  - `solMotion.dumpLeaders()`
- Just vorticity:
  - `solMotion.dumpLeaders({ which: 'vort', k: 8 })`
- Just circulation:
  - `solMotion.dumpLeaders({ which: 'circ', k: 8 })`

Programmatic access:

- `const leaders = solMotion.getLeaders();`

---

## 7) Notable caveats / future refinements discussed

- The legacy helper `computeVorticityCycle()` is still present but unused; it can be removed later for clarity.
- Current implementation uses **triangle sampling**; this is stochastic and “good enough” for hotspot detection, not a rigorous curl operator.
- `circAbs_ema` currently tracks the same local proxy as vorticity (stored separately so it can be swapped later).
- Hot Now currently ranks by |z| and uses z-score state that adapts; if you want a more stationary baseline, consider using slower alphas for `zMuAlpha` / `zAbsDevAlpha`.

---

## 8) Net result

After this chat, SOL v3.5 gained a stable engine-level “memory + anomaly” subsystem:

- Meaning-bearing vorticity is computed from flux cycles and stored in the solver.
- Collapse behavior is physics-only (Jeans threshold) rather than taxonomy-gated.
- The engine now supports both:
  - **fast anomaly capture** (“Hot Now”, Surges, Drops)
  - **stable identity characterization** (“Persistent Attractors”, EMA)
- Debugging and inspection is simpler via `solMotion.dumpLeaders()`.
