---
description: Design a SOL Auto Mapper sweep plan (grid + baselines + outputs)
---

You are designing a SOL Auto Mapper run.

Ask only the minimum clarifying questions needed.

Produce:
1. A `masterName`
2. Defaults (basins, replicates, scenario, measurement, timing)
3. A `sweeps` list in sequential order (each sweep has `sweepName` + `grid` and optional overrides)
4. A reproducibility note (baseline/restore expectations)
5. File naming / output expectations

Return a ready-to-run JSON plan compatible with `solAutoMap.runMaster(masterPlan)`.
