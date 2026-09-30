# SOL / qFoamInspection CSV→TXT Consolidation Report (2025-12-22)

## Context and intent
This work session focused on preparing SOL diagnostics exports for easier human review and downstream ingestion by tools that prefer plain text rendering over CSV handling.

The user had a diagnostics directory containing 20 subfolders (named `damp1` through `damp20`) under:

- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection`

Each `damp*` folder contained one or more CSV files (including multi-part exports and manifest files). The request was:

1. Copy every CSV in that directory tree.
2. Convert the file extension from `.csv` to `.txt`.
3. Preserve the *data content exactly* (i.e., no transformation—just extension change via copying).
4. Then, create a single consolidated folder containing all resulting TXT files for easier browsing.

## Work performed (chronological)

### 1) Recursive CSV discovery and `.txt` copy creation
**Goal:** Ensure every `*.csv` has a sibling `*.txt` file with the same content.

**Action:** Recursively enumerated all `.csv` files under `qFoamInspection` and copied each to the same path/name but with extension changed to `.txt`.

**Important behavior:**
- Originals were left intact (`.csv` files were not deleted or renamed).
- Each `.txt` file is a direct copy of the `.csv` file bytes (no parsing, no delimiter changes).
- Copies were only created if the `.txt` did not already exist.

### 2) Verification output written to a summary file
**Goal:** Provide a durable, in-folder audit artifact proving counts and showing sample outputs.

**Action:** Created a summary file at the root of `qFoamInspection`:

- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection\qfoam_csv_to_txt_summary.txt`

**Recorded counts at the time of summary creation:**
- `CSV count: 61`
- `TXT count (all): 61`

This confirmed a 1:1 creation of TXT copies alongside every CSV found at that time.

### 3) Consolidated “all_txt” folder creation
**Goal:** Provide a single location where all TXT files can be found quickly (instead of navigating damp folders).

**Action:** Created a new folder:

- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection\all_txt`

Then copied all TXT files from the `qFoamInspection` tree into that folder.

**Collision prevention approach:**
- Destination filenames were prefixed with the immediate source folder name to avoid name collisions.
  - Example: `damp10_sol_diagnostics_20251221_215843_part001.txt`
- A fallback collision handler was also included (adds `__2`, `__3`, etc.) but no collisions occurred.

### 4) Consolidated copy summary created
**Goal:** Provide an audit file for the consolidated folder.

**Action:** Created:

- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection\all_txt\all_txt_copy_summary.txt`

**Recorded counts at the time of consolidated copy:**
- `Source TXT files found: 62`
- `Copied into all_txt: 62`
- `Name collisions handled: 0`
- `Skipped (already existed): 0`

**Note on the count difference (61 vs 62):**
- After creating the initial CSV→TXT summary file (`qfoam_csv_to_txt_summary.txt`), that file itself is a `.txt` located under `qFoamInspection`.
- The later “copy all TXT files” step included that summary TXT as well, producing 62 total TXT files copied into `all_txt`.

## Output artifacts (what was created)

### TXT copies next to the CSVs
For each CSV like:
- `...\dampX\something.csv`

A corresponding TXT was created alongside it:
- `...\dampX\something.txt`

This includes:
- `*_manifest.csv` → `*_manifest.txt`
- `*_part001.csv`, `*_part002.csv`, etc. → matching `.txt`
- Single-file exports (no `partNNN`) → matching `.txt`

### Consolidated folder
All TXT files were copied into:
- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection\all_txt`

Destination filename format:
- `<dampFolder>_<originalTxtFileName>`

### Summary files
- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection\qfoam_csv_to_txt_summary.txt`
- `G:\docs\TechmanStudios\sol\sol_diagnostics\qFoamInspection\all_txt\all_txt_copy_summary.txt`

## Operational notes / rationale
- The approach intentionally avoided parsing CSVs. This guarantees:
  - No quoting/escaping changes
  - No delimiter normalization
  - No numeric formatting changes
  - No line-ending conversion beyond what `Copy-Item` naturally preserves (byte-for-byte copy)
- The consolidated `all_txt` folder was added purely for ergonomics and faster review.

## Suggested follow-ups (optional)
- Create an `all_csv` folder mirroring the TXT consolidation if a single “source of truth” CSV bundle is also helpful.
- Zip `all_txt` for archival/sharing.
- Add a lightweight script (`.ps1` or Python) to repeat this workflow for future diagnostics drops.
