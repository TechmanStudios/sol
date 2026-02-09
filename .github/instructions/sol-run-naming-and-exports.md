# SOL Run Naming and Export Standards

## Run ID discipline
Every conclusion must cite run IDs and filenames. Never use “that run from last week.”

## Recommended export trio
When applicable, produce:
- *_MASTER_summary.csv
- *_MASTER_busTrace.csv
- *_repTransition_curve.csv

## Part file discipline
If exports split into parts:
- keep all parts together
- keep the export manifest file
- reference the manifest in the run bundle

## Derived outputs
Derived outputs must retain runTag/seriesName in the filename:
- analysis_report_<series>.md
- derived_tables_<series>.csv
- analyze_<series>.py

## Minimum required metadata
Each run bundle must include:
- dashboard version identifier
- harness schema identifier
- baseline mode
- invariants (dt/damp/pressC/capLawHash/baseline mode)
- detector definitions/windows (or [UNKNOWN])
