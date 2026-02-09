# SOL Proof Packet Standard

Every promoted claim must be written as:

**Location:** store domain proof packets in `solKnowledge/proof_packets/domains/`.
**Ledger:** master index at `solKnowledge/proof_packets/LEDGER.md`.
**Raw audit trail:** individual PP files in `solKnowledge/proof_packets/raw/`.

## CLAIM
One sentence. No hedging. No multiple claims in one packet.

## EVIDENCE
- Run IDs:
- Export files:
- Key metrics (values + units + where in the file):
- Notes about detector windows/definitions:

## ASSUMPTIONS
List the invariants and hidden dependencies:
- baselineMode:
- dt/damp/pressC/capLawHash:
- dashboard/harness version:
- detector window positions:
- session conditions (fresh vs continued session):

## FALSIFY
The smallest test that would break the claim:
- what to run
- expected failure signature
- how it would appear in exports

## STATUS
One of:
- provisional (seen once or weak controls)
- supported (replicated with controls)
- robust (cross-session + counterbalanced + stable detectors)
- deprecated (known wrong, superseded, or artifact-induced)

### Proof packet hygiene
- Do not promote if evidence is missing.
- Do not merge packets across run series unless provenance is explicit.
