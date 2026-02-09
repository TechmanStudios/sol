---
name: SOL Claim Promotion Checklist
description: Checklist to decide whether a SOL claim can be promoted to a proof packet.
model: GPT-5.2
agent: sol-knowledge-compiler
---

# CLAIM PROMOTION CHECKLIST (SOL)

A claim is ready to promote only if:

## Evidence completeness
- [ ] Run IDs listed
- [ ] Export filenames listed
- [ ] Detector windows/definitions listed (or [UNKNOWN] and not required)
- [ ] Invariants listed (dt/damp/pressC/capLawHash/baseline mode)

## Controls
- [ ] Baseline handling is consistent across compared conditions OR explicitly studied
- [ ] Order effects controlled (AB/BA or argument why not needed)
- [ ] Detector clipping checked (window shift or saturation test)
- [ ] Within-session repeatability shown OR declared provisional
- [ ] Cross-session repeatability shown for robust claims

## Proof packet quality
- [ ] CLAIM is one sentence and falsifiable
- [ ] EVIDENCE includes measured values
- [ ] ASSUMPTIONS enumerated
- [ ] FALSIFY test described
- [ ] STATUS assigned honestly

## Provenance
- [ ] No orphan references
- [ ] External artifacts are in the manifest
