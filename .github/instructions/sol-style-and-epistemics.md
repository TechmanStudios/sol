# SOL Style and Epistemics (Anti-Drift Standard)

## 1) The Prime Directive
Do not manufacture certainty. SOL is a complex dynamical system: it will gladly create illusions if you let it.

## 2) Required tags
Use these tags to separate observation from story:
- [EVIDENCE] — direct outputs, run IDs, filenames, measured values
- [INTERPRETATION] — your explanation of evidence
- [HYPOTHESIS] — testable guess about mechanism
- [SPECULATION/POETIC] — inspiration, metaphor, non-testable ideas

## 3) The [UNKNOWN] rule
If any of the following is missing, label it [UNKNOWN]:
- run IDs
- dashboard version/harness schema
- baseline mode
- dt/damp/pressC/capLawHash
- detector definitions/windows
- export filenames

Never guess missing values.

## 4) Promotion rule
Nothing becomes “true” until it is:
- tied to run IDs + export filenames, and
- summarized as a proof packet, and
- includes a falsification plan.

## 5) Order-effect paranoia (healthy paranoia)
If results could plausibly depend on:
- sweep direction,
- pass order,
- dwell time,
- session age,
- baseline restore frequency,

then order effects must be tested via controls (AB/BA, cross-session, window shifts).

## 6) Writing style
- Crisp sentences.
- Prefer tables over paragraphs for invariants and results.
- Keep everything reconstructible.
