# SOL Dashboard Chat Report (Consolidated)

Date range covered (from chat context): 2025-12-20 → 2025-12-21
Date compiled: 2026-01-15

Scope: This report summarizes everything discussed and implemented in this chat related to the SOL Engine / `sol_dashboard_test_original.html`, focused on (1) Diagnostics Recorder export formats and size-efficiency under upload limits, and (2) making the in-browser knowledge-base compiler more general-purpose (less “esoteric phrase” biased), including adding UI tuning knobs for different KB styles.

---

## 1) Executive summary

This chat started with a practical constraint:

- Diagnostics exports became ~103–104 MB for ~120s recordings when all-to-all background edges were enabled.
- The downstream analysis tool had a 100 MB upload limit and did not accept compressed JSON.

Work completed in this chat:

1) **Diagnostics export format redesign**
- Started from JSON export and explored compression.
- Pivoted to **CSV exports** because the analysis tool accepts CSV.
- Iterated through CSV designs:
  - Single JSON → gzip JSON (rejected due to tool limitations)
  - Single CSV with recordType rows
  - Multiple “tidy tables” CSVs
  - Back to single combined CSV (one upload) with a `table` column
  - Automatic multi-part splitting under ~95 MB per file
  - Added an always-generated **manifest CSV** describing files + joins

2) **Compiler generalization**
- Identified explicit esoteric bias in the compiler (a whitelist and marker-based boosts).
- Removed special-case esoteric boosting.
- Strengthened general keyword/phrase extraction (added trigrams).
- Improved “structured KB” handling (heading-derived concepts + template phrase suppression).
- Added UI knobs so you can tune compilation behavior per KB.

Primary file modified:
- `g:\docs\TechmanStudios\sol\sol_dashboard_test_original.html`

---

## 2) Repo / workspace context

Work was performed in:
- `g:\docs\TechmanStudios\sol\`

The SOL dashboard is a single-file HTML artifact that includes:
- UI controls
- In-browser compilation of uploaded KBs (MD/TXT/RTF)
- SOL simulation
- vis-network visualization
- Diagnostics recorder + exporter

---

## 3) Chronological timeline (high-level)

### 2025-12-20 — Diagnostics export size problem + compression attempt
- Problem statement: exporting ~120s diagnostics with all-to-all edges produced ~103–104 MB JSON.
- Proposed: keep fidelity but compress via gzip; implemented browser-side gzip download via `CompressionStream('gzip')` with fallback to plain JSON.
- Blocker discovered: the user’s analysis tool does not accept zipped JSON.

### 2025-12-20 — Pivot to CSV exports (fidelity-preserving)
- Requirement: “same recordings / same fidelity” but in CSV.
- Implemented relational CSV export that preserved full per-node + per-edge state but avoided repeating static metadata in every row.
- Added automatic file splitting under ~95 MB to satisfy 100 MB upload caps.

### 2025-12-20 — CSV layout optimized for AI parsing
- Requirement: layout that’s easiest for LLM-based analysis tools (GPT 5.2 / Gemini / Grok).
- Implemented “tidy table” multi-file layout (nodes, edges, samples, node_values, edge_values, top summaries) so joins are clean and schema is consistent.

### 2025-12-21 — Single-upload requirement + final export ergonomics
- Requirement: “join it into one file so I only upload one file.”
- Implemented combined CSV format with a `table` column so all data can live in one file.
- User then requested: “split into multiple files if it exceeds the ~95MB margin.”
- Implemented automatic multi-part combined CSV splitting with repeated headers.
- Added a manifest file (always) to describe:
  - recording settings
  - how to join indices
  - exact filenames/byte sizes

### 2025-12-21 — Compiler: reduce esoteric bias + improve general KB mapping
- Identified and removed explicit “esoteric singleton whitelist” and scoring boosts.
- Added trigram extraction.
- Broadened group classification markers to be generally applicable (humanities/religion/philosophy rather than specific proper nouns).

### 2025-12-21 — Compiler: structured Markdown KB support + UI knobs
- Example KB provided: large structured philosophy KB.
- Implemented heading-as-concept candidates and boosted them.
- Suppressed common repeated KB scaffolding phrases.
- Added two UI knobs under “Load Knowledge Base”:
  - “Use headings as concepts” (checkbox)
  - “Repetition filter” (slider) + explanation for structured vs informal notes

---

## 4) Diagnostics Recorder export: design and final behavior

### 4.1 Original problem
- With background edges (all-to-all) enabled, edge count scales ~O(N²).
- Exporting full per-edge state at a moderate sample rate rapidly becomes huge.

### 4.2 Compression option (implemented, but later superseded)
- Implemented gzip JSON export using browser `CompressionStream('gzip')`.
- Fallback to plain JSON if gzip stream unsupported.
- Ultimately not usable for the user’s tool because it did not accept compressed JSON.

### 4.3 CSV export iterations (implemented and retained in final form)

#### Combined CSV schema (final)
- Exports one logical combined CSV schema with:
  - A `table` column identifying row type:
    - `meta`, `node`, `edge`, `sample`, `node_value`, `edge_value`, `top_node`, `top_edge`
  - Index-based references:
    - `nodeIndex` and `edgeIndex` used instead of repeating labels everywhere
  - Per-sample metrics columns:
    - `entropy`, `totalFlux`, `maxFluxAbs`, `mass`, `avgRho`, `maxRho`, `activeCount`, `pressureC`, `damping`, `bias`, `gamma`
  - Per-node state columns:
    - `rho`, `p`, `psi`, `psi_bias`
  - Per-edge state columns:
    - `conductance`, `flux`

#### Automatic multi-part splitting
- Target limit per file: ~95 MB (margin under typical 100 MB caps).
- Behavior:
  - If combined CSV fits: one `sol_diagnostics_YYYYMMDD_HHMMSS.csv`
  - If not: multiple parts:
    - `sol_diagnostics_YYYYMMDD_HHMMSS_part001.csv`, `..._part002.csv`, etc.
  - Each part repeats the CSV header so it can be parsed independently.

#### Manifest output (always generated)
- Always downloads alongside the CSV/parts:
  - `sol_diagnostics_YYYYMMDD_HHMMSS_manifest.csv`
- Manifest structure:
  - `key,value` rows for settings + quick usage notes
  - A second section `file,bytes` listing exact produced filenames and sizes
- Manifest includes:
  - schema, createdAt, durationMs, sampleEveryMs, includeBackgroundEdges
  - nodeCount, edgeCount
  - join guidance:
    - nodeIndex joins `node_value`/`top_node` → node defs
    - edgeIndex joins `edge_value`/`top_edge` → edge defs
    - sampleIndex joins values → samples

#### Memory / blob URL hygiene
- Since multi-file downloads create multiple blob URLs, added tracking:
  - `state.lastBlobUrls[]`
- Revoke prior blob URLs before new downloads to avoid memory leaks.

### 4.4 Diagnostics UI updates
- Updated the Diagnostics section copy to explain:
  - CSV export
  - auto-splitting under ~95 MB
- Updated download button label to “DOWNLOAD LAST RECORDING (CSV)”.

---

## 5) Compiler generalization (less esoteric, more general keyword mapping)

### 5.1 What was causing “esoteric leaning”
The compiler contained explicit bias toward esoteric terms:
- A hard-coded `ESOTERIC_SINGLETON_WHITELIST`
- Extra boosts in TF-IDF scoring for those whitelisted unigrams
- Group classification that prioritized “spirit” markers heavily tied to ThothStream vocabulary

### 5.2 Changes made for general-purpose behavior

#### Removed esoteric special-casing
- Removed `ESOTERIC_SINGLETON_WHITELIST` entirely.
- Removed scoring logic that boosted those terms.

#### Improved phrase extraction
- Added trigram extraction in addition to:
  - unigram tokens
  - bigram tokens
  - “proper phrase” extraction
- This helps general-domain concepts emerge as single nodes:
  - e.g., “neural network model”, “supply chain risk”, “climate change policy”, etc.

#### Adjusted scoring to be less “proper noun dominated”
- Reduced `properBoost` and `properPhraseBoost` to avoid a graph dominated by names.
- Increased phrase preference to produce cleaner concept nodes.
- Softened penalties for unigrams and high-document-frequency tokens to avoid losing central topic words.

#### Group classification broadened
- Replaced the narrowly esoteric “spirit” marker list with broader humanities/religion/philosophy/culture markers.
- Kept tech markers (software/data/ML/etc.).
- Default remains `bridge` if neither category matches.

#### Structured Markdown KB handling
For large structured KBs (like the philosophy file):
- Headings are now captured on each doc segment (`doc.heading`).
- Heading-derived candidates are added as concept candidates.
- Heading-derived candidates receive an explicit boost.
- Added additional boilerplate/template suppression:
  - penalize very high-document-frequency phrases
  - expand lists of generic scaffolding terms and excluded “meta headings”

---

## 6) Added UI knobs for KB compilation

These were added to reduce the need to edit code per KB.

### 6.1 “Use headings as concepts” (checkbox)
- Default: enabled.
- When enabled, heading-derived candidates are included and boosted.
- Recommended:
  - ON for structured Markdown encyclopedias / manuals / well-sectioned notes.
  - OFF for messy plaintext dumps where headings are unreliable or missing.

### 6.2 “Repetition filter” (slider)
- Default: 60%.
- Higher is better for big structured documents; lower is better for smaller informal note-style documents.
- Under the hood it influences:
  - how aggressively common “template-y” phrases are suppressed
  - how tight the max document-frequency threshold is
  - how strong the heading boost is (since headings are often the semantic backbone in structured KBs)

### 6.3 Wiring
- UI values are read in `compileAndLoadKnowledgeBase()` and passed to:
  - `App.compiler.compileTextToGraph(text, { preferHeadings, boilerplateStrength, ... })`

---

## 7) Practical usage notes

### Recommended settings for your philosophy KB
- Use headings as concepts: ON
- Repetition filter: 60–90%
- This should yield nodes like “Metaphysics”, “Epistemology”, “Ethics”, “Being”, etc., rather than repeated scaffolding phrases.

### Recommended settings for messy informal notes
- Use headings as concepts: OFF (or ON if headings are meaningful)
- Repetition filter: 0–40%
- This helps avoid over-suppressing the author’s recurring vocabulary.

---

## 8) Files changed in this chat

Primary file:
- `g:\docs\TechmanStudios\sol\sol_dashboard_test_original.html`

Key modules touched:
- `App.diagnostics` (export format, splitting, manifest, blob URL tracking)
- `App.compiler` (token/phrase extraction, bias removal, heading support)
- `App.ui` (new KB tuning controls + wiring into compiler options)

---

## 9) Open follow-ups (optional)

If desired, the next high-value improvements would be:
- Add a “target max MB” input for diagnostics export so the splitter targets any upload cap.
- Add a “maxNodes / topKEdges” UI control for KB compilation.
- Add an optional “edge strategy” selector (PMI over section-docs vs. sliding-window co-occurrence) for better general-purpose graph topology.
