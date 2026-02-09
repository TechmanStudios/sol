---
name: SOL CSV Analysis (Python Scaffolds)
description: Produce reproducible analysis outputs from SOL exports.
---

# Skill: CSV Analysis (Python Scaffolds)
## Purpose
Produce reproducible analysis outputs from SOL exports.

## Inputs
- summary CSV
- busTrace CSV (optional for deeper traces)
- repTransition curve CSV (optional for timing/curves)
- target question

## Procedure
1) Load CSVs with explicit dtypes where possible.
2) Verify invariants are constant across compared conditions:
   - dt/damp/pressC/capLawHash/baseline mode
3) Compute sample sizes per cell and reject underpowered cells (or flag them).
4) Compute primary outcomes:
   - winner probability
   - timing distributions
   - threshold bracket (see .github/skills/skill-threshold-bracketing/skill.md)
5) Export derived tables as CSV and write a Markdown report.

## Outputs
- analysis_report_<series>.md
- derived_tables_<series>.csv
- analyze_<series>.py (optional)

## Skeleton (pasteable)
```python
import pandas as pd

summary = pd.read_csv("..._MASTER_summary.csv")
# Optional:
# bus = pd.read_csv("..._MASTER_busTrace.csv")
# curve = pd.read_csv("..._repTransition_curve.csv")

# 1) invariants check
inv_cols = ["dtUsed","dampUsed","pressCUsed","capLawHash","baselineModeUsed"]
present = [c for c in inv_cols if c in summary.columns]
invariants = summary[present].drop_duplicates()

# 2) sample size per cell (example keys)
keys = [c for c in ["multBUsed","dir","passLabel"] if c in summary.columns]
n = summary.groupby(keys).size().reset_index(name="n")

# 3) primary outcome placeholder
# Replace 'winnerNode' with your actual column name in summary
if "winnerNode" in summary.columns:
    p = (summary.assign(is114=summary["winnerNode"].eq(114))
               .groupby(keys)["is114"].mean()
               .reset_index(name="P_winner114"))
else:
    p = pd.DataFrame()

# 4) write outputs
invariants.to_csv("derived_invariants.csv", index=False)
n.to_csv("derived_counts.csv", index=False)
p.to_csv("derived_primary.csv", index=False)
