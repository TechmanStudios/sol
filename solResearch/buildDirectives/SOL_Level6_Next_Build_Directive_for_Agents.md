# SOL Level 6+ Next Build Directive for Agents

**Audience:** Antigravity agents, Gemini collaborator agents, SOL build agents  
**Date:** 2026-06-05  
**Purpose:** Align today's build session around the next best engineering direction after the Level 6 pointer-bus / 4-bit serial adder breakthrough.

---

## 0. Executive thesis

SOL has crossed from isolated analog-physics experiments into a layered computing architecture.

The immediate mission is no longer "find another cool primitive." The mission is to harden Level 6 into a reproducible, testable software-on-substrate layer.

The next build direction is:

1. **Stabilize Level 6.1:** exhaustively and randomly validate the current 4-bit serial adder / 2-bit pointer bus under noise, jitter, timing drift, and repeated execution.
2. **Extend Level 6.1:** add a 4-bit subtractor with borrow propagation, then an 8-bit serial adder if stability holds.
3. **Prototype Level 6.2:** move from host-side hardcoded program lists toward a stored-program substrate: instruction basins, program counter, fetch/decode/execute loop, and pointer-addressed instruction memory.
4. **Upgrade the philosophy:** treat every new primitive as an architectural component with invariants, falsifiers, tolerance bands, and promotion gates.

Plain version: **make Level 6 boring, repeatable, and extensible before chasing Level 7.**

---

## 1. Current architecture reading

The working architecture should be treated as a six-level stack:

| Level | Name | Role | Promotion question |
|---:|---|---|---|
| 1 | Nano-folds | Memristive battery latches, transistor gates, local state cells | Can one physical state be written, held, reset, and read? |
| 2 | Micro-folds | Local ALU, clock, register logic | Can local gates compute truth tables with stable timing? |
| 3 | Sub-manifolds | Specialized memory or agent pockets | Can isolated pockets store and recall state without cross-talk? |
| 4 | Manifolds | Global dual-bus coordinator systems | Can long-range routing, arbitration, and handshake protocols stabilize? |
| 5 | Manifold-Systems | Orchestrated semantic + blank manifolds | Can memory stay stable while clean blank cores compute? |
| 6 | Basic Software | Compiler, VM, control flow, pointers, loops, subroutines | Can physical state host a programmable runtime? |

Key interpretation:

- **Semantic manifold = memory landscape.** It is rich, high-capacitance, and data-dependent.
- **Blank processing manifold = compute core.** It is cleaner, lower-noise, and more predictable.
- **Wormholes = buses.** They move state between memory and compute pockets.
- **Belief / psi = gate control.** It opens, closes, freezes, or overrides physical channels.
- **Density / pressure / flux = signal.** These are the physical carriers of computation.
- **Compiler / VM = Level 6 control layer.** It schedules physical operations into a program.

The recent 2-bit pointer address bus is the first strong sign that SOL can support index-addressed memory rather than only hardcoded routing.

---

## 2. Philosophy upgrade for today's agents

### 2.1 Physics first, software second, proof always

Agents should not treat the VM as an ordinary Python VM that happens to call a simulator. Treat it as a compiler targeting a weird physical machine.

Every feature should answer:

- What physical state carries the bit?
- What physical transition performs the operation?
- What timing window makes it reliable?
- What invariant proves it did not cheat?
- What perturbation falsifies it?

### 2.2 Components are not enough; build the ladder

The conjectures have become a parts catalog. The job now is to turn parts into an architecture.

Bad next step:

```text
Add another isolated conjecture with a one-off script.
```

Good next step:

```text
Promote a primitive into a level, define its invariants, test its tolerance band,
and connect it to the next layer of the stack.
```

### 2.3 Every poetic primitive needs an engineering form

Poetic language is valuable for discovery, but every poetic object must have a hard technical counterpart.

| Poetic term | Engineering interpretation |
|---|---|
| Wormhole | Gated high-conductance routing edge or manifold bridge |
| Battery | Stateful memristive latch / binary reservoir |
| Star / Jeans collapse | Nonlinear density phase-change memory / attractor hardening |
| Phonon | Modulated density or belief wave packet |
| Thought loop | Self-routing recurrent flow with convergence or latch behavior |
| Manifold lobe | Semi-independent memory or compute substrate |
| Semantic gravity | Pressure / density / topology induced routing bias |

Agents may use poetic language in comments or reports, but tests must use measurable quantities: rho, psi, b_state, flux, conductance, mass, entropy, step count, failure rate.

### 2.4 The data is the hardware

Do not treat corpus, topology, or basin layout as passive data. In SOL, the populated graph creates the physical landscape. Different data means different capacitance distribution, routing geometry, attractor basins, and latency profiles.

Therefore, Level 6 tests should be separated into:

- **Blank-core tests:** clean processor behavior.
- **Semantic-memory tests:** real data / basin behavior.
- **Hybrid tests:** compute in blank core, store in semantic layer.

---

## 3. Next best build direction

### Build target A: Level 6.1 hardening - current 4-bit serial adder

Current status: the latest Level 6 build validates a 2-bit pointer bus and 4-bit serial adder on representative boundary cases. The next step is to turn this from a milestone into a reliable primitive.

Create:

```text
scratch/test_logos_vm_4bit_adder_exhaustive.py
solResearch/nextBestTest/logos_vm_4bit_adder_exhaustive_results.json
solResearch/nextBestTest/logos_vm_4bit_adder_exhaustive_report.md
```

Minimum test set:

```text
x in 0..15
y in 0..15
cin in {0,1}
Total = 512 cases
```

Required checks per case:

- SUM bits equal `(x + y + cin) & 0xF`.
- Cout equals `(x + y + cin) >> 4`.
- Final register battery states collapse cleanly to `-1` unless intentionally preserved.
- Source input basins remain semantically insulated.
- Output basins contain expected final states.
- Active registers never drop below the active mass safety threshold during required active windows.
- Residual flux and bus mass after program exit stay below thresholds.

Success criterion:

```text
512 / 512 exact arithmetic correctness
0 source-basin mutations
0 unplanned live registers at exit
No critical mass-threshold violations
```

### Build target B: Level 6.1 tolerance sweep

After exact correctness passes, make it harder.

Create:

```text
scratch/test_logos_vm_4bit_adder_tolerance.py
solResearch/nextBestTest/logos_vm_4bit_adder_tolerance_results.json
solResearch/nextBestTest/logos_vm_4bit_adder_tolerance_report.md
```

Sweep dimensions:

| Dimension | Suggested values | Purpose |
|---|---|---|
| dt | baseline +/- 5%, 10%, 20% | Detect integration sensitivity |
| damping | baseline x 0.5, 0.75, 1.0, 1.25, 1.5 | Detect friction dependence |
| instruction timing | +/- 1, 2, 5, 10 steps | Detect schedule fragility |
| initial mass noise | 0, 0.1, 0.5, 1.0, 2.0 | Detect write/read robustness |
| psi noise | 0, 0.01, 0.05, 0.1 | Detect belief leakage |
| repeated runs | 1, 5, 20 sequential executions | Detect residual accumulation |

Report not just pass/fail but **safe operating envelope**:

```text
The primitive remains correct for dt drift <= X%, timing jitter <= Y steps,
noise <= Z, and repeated execution count <= N.
```

### Build target C: Level 6.1 extension - 4-bit subtractor

Implement a 4-bit subtractor using borrow propagation.

Canonical equations:

```text
Diff = A xor B xor Bin
Bout = ((not A) and (B or Bin)) or (B and Bin)
```

Test set:

```text
x in 0..15
y in 0..15
bin in {0,1}
Total = 512 cases
Expected = x - y - bin modulo 16
Bout = 1 if x < y + bin else 0
```

Why subtractor before 8-bit adder?

- It tests a different carry-like chain: borrow logic.
- It requires NOT / inversion paths to behave correctly.
- It exposes whether the compiler can schedule a more complex boolean expression under register scarcity.

### Build target D: Level 6.1 scale - 8-bit serial adder

Only after A and B are stable, scale the pointer bus.

Options:

1. **3-bit pointer bus:** registers or saved context represent indices 0..7.
2. **Two-pass 2-bit window:** keep 2-bit pointer but page high/low nibbles through a page bit.

Recommendation: use the **two-pass 2-bit window first** because it stresses context management without forcing a bigger address decoder immediately.

Success criterion:

```text
Exhaustive 8-bit full addition is 131,072 cases, so start with randomized 2,048 cases
plus boundary cases. Move to exhaustive later if runtime is acceptable.
```

### Build target E: Level 6.2 stored-program prototype

This is the most important next conceptual milestone.

Goal: stop treating the program as a Python list of instructions. Store a tiny program in semantic basins and fetch it through the pointer bus.

Minimum viable stored-program experiment:

```text
Instruction basins: Instr_0, Instr_1, Instr_2, Instr_3
Program counter: PC0, PC1
Fetch: FETCH_INDIRECT PC -> current instruction basin
Decode: instruction basin activates one opcode gate
Execute: LOAD / CLEAR / STORE / JUMP_IF_ACTIVE subset
Increment: PC = PC + 1 unless branch overrides
```

Start with a tiny program:

```text
0: LOAD A, Basin_X0
1: JUMP_IF_ACTIVE A, 3
2: LOAD C, Basin_One
3: STORE C, Basin_Out
```

Expected outcome:

- With X0 active, branch skips instruction 2.
- With X0 collapsed, instruction 2 runs.
- Output basin matches expected branch path.

This is the leap from **VM controlling analog hardware** to **program stored in analog/semantic memory**.

---

## 4. Agent task assignments

Use these roles in Antigravity or any multi-agent orchestration.

### Agent 1 - Architecture/spec agent

Deliver:

```text
solKnowledge/level_architecture/SOL_Level_Architecture_v0_1.md
```

Responsibilities:

- Define Level 1 through Level 6 precisely.
- List primitives per level.
- Define promotion gates for each level.
- Add a dependency graph showing which primitives support Level 6.
- Mark each primitive status: sim-local, cross-seed, cross-topology, noise-hardened, integrated.

### Agent 2 - VM/ISA agent

Deliver:

```text
solKnowledge/agent_coding_guide/isa_level6.md
```

Responsibilities:

- Normalize instruction syntax.
- Document timing per instruction.
- Document which instructions are host-side symbolic vs physically substrate-backed.
- Define register allocation constraints.
- Add examples for 4-bit adder, subtractor, loop, and call/return.

### Agent 3 - Harness agent

Deliver:

```text
scratch/test_logos_vm_4bit_adder_exhaustive.py
scratch/test_logos_vm_4bit_adder_tolerance.py
```

Responsibilities:

- Exhaustive 512-case arithmetic test.
- Tolerance sweep harness.
- JSON result export.
- Compact report table.
- Failure-case minimization: store the smallest failing x/y/cin and perturbation config.

### Agent 4 - Physics/failure-mode agent

Deliver:

```text
solResearch/nextBestTest/logos_vm_failure_modes_report.md
```

Responsibilities:

- Identify failure modes: residual flux, belief leakage, destructive readout, mass threshold drops, context-stack drift, pointer decode ambiguity.
- Propose thresholds and monitors.
- Add counters to the harness.
- Define which failures are recoverable vs architecture-breaking.

### Agent 5 - Docs/proof agent

Deliver:

```text
solResearch/nextBestTest/logos_vm_4bit_adder_exhaustive_report.md
solResearch/conJecture/conjecture_level6_1_hardening.txt
```

Responsibilities:

- Convert test output into proof-style language.
- Include assumptions, falsifiers, and status.
- Avoid overclaiming beyond simulation scope.
- Update the master chronicle only after tests pass.

---

## 5. Promotion gates

### Gate 1 - Existing 4-bit adder becomes Level 6.1 stable

Required:

- 512/512 exact correctness.
- No critical mass-threshold failures.
- No output/source basin corruption.
- Clean register collapse at exit.
- At least one tolerance envelope reported.

Status label after pass:

```text
Level 6.1 arithmetic primitive: sim-local robust
```

### Gate 2 - 4-bit subtractor becomes Level 6.1 extended

Required:

- 512/512 exact correctness.
- Borrow-out correct.
- Same invariants as adder.
- Compiler or VM scheduling documented.

Status label after pass:

```text
Level 6.1 arithmetic family: add/sub sim-local robust
```

### Gate 3 - 8-bit serial adder becomes Level 6.1 scaled

Required:

- Boundary cases pass.
- Randomized >= 2,048 cases pass.
- Pointer/page strategy documented.
- Runtime and scaling bottlenecks measured.

Status label after pass:

```text
Level 6.1 arithmetic scaled: randomized robust
```

### Gate 4 - Stored-program prototype becomes Level 6.2 candidate

Required:

- Program stored in basins, not only Python instruction list.
- Fetch/decode/execute loop demonstrated.
- Branch path depends on substrate register state.
- Program counter increments or branches correctly.
- Minimal instruction subset documented.

Status label after pass:

```text
Level 6.2 stored-program substrate: candidate
```

---

## 6. Required metrics schema

Every Level 6 report should include this table:

| Metric | Meaning | Required? |
|---|---|---|
| `cases_total` | Number of test cases run | Yes |
| `cases_passed` | Number of exact correctness passes | Yes |
| `failure_rate` | `(total - passed) / total` | Yes |
| `min_active_register_mass` | Lowest active register mass during active windows | Yes |
| `max_source_basin_delta` | Maximum unintended source memory mutation | Yes |
| `max_residual_flux_exit` | Largest edge flux after exit | Yes |
| `max_bus_rho_exit` | Residual bus density after program exit | Yes |
| `final_register_states` | Battery states at program end | Yes |
| `steps_per_case` | Runtime length | Yes |
| `runtime_seconds` | Wall-clock runtime | Yes |
| `safe_dt_band` | Passing dt perturbation interval | Tolerance tests |
| `safe_noise_band` | Passing noise interval | Tolerance tests |
| `safe_timing_jitter` | Passing timing jitter interval | Tolerance tests |

Suggested JSON structure:

```json
{
  "schema": "sol.level6.verification.v1",
  "run_id": "logos_vm_4bit_adder_exhaustive_YYYYMMDD_HHMMSS",
  "primitive": "4bit_serial_adder",
  "level": "6.1",
  "cases_total": 512,
  "cases_passed": 512,
  "failure_rate": 0.0,
  "invariants": {
    "source_insulation": true,
    "register_exit_clean": true,
    "mass_threshold_ok": true,
    "residual_flux_ok": true
  },
  "failures": []
}
```

---

## 7. Coding rules for agents

1. **Do not hide physical decisions in Python.** If Python performs a step, label it host-side. If the substrate performs it, label it physical.
2. **Do not change prior passing behavior silently.** Add tests before changing VM or sequencer semantics.
3. **Keep source memory immutable unless the instruction is STORE.** Source-basin mutation is a serious bug.
4. **Track residuals.** Flux, bus mass, battery charge, and belief residue are common corruption sources.
5. **Prefer additive files.** Create new harnesses and reports before refactoring core VM code.
6. **Every new primitive gets a report and a falsifier.** No undocumented victories.
7. **Use promotion labels.** Do not call something robust unless it passed robustness gates.

---

## 8. Failure modes to hunt aggressively

| Failure mode | Symptom | Likely cause | Monitor |
|---|---|---|---|
| Residual flux carryover | Later cases fail after earlier cases pass | Edge inertia not reset | `max_residual_flux_exit` |
| Belief leakage | Collapsed basins drift positive | Unweighted psi diffusion or open topology | source-basin psi delta |
| Destructive readout | Input registers lose state | Read window too long or gate too conductive | active register mass curve |
| Pointer ambiguity | Wrong memory index loaded/stored | MSB/LSB state not cleanly latched | pointer decode trace |
| Context-stack drift | Subroutine returns corrupted state | Host-side stack mismatch or incomplete backup | register snapshot diff |
| Timing brittleness | Small step jitter breaks arithmetic | Narrow compute threshold window | timing sweep |
| Overfit constants | Works only in one damping/dt | Calibrated too tightly | dt/damping sweep |
| Python cheating | Result is correct but not physically carried | Host reads/writes too much state | physical-vs-host operation audit |

---

## 9. Today's recommended build order

Follow this order unless a blocking bug appears.

```text
1. Create branch: feature/level6-1-hardening
2. Add Level Architecture v0.1 doc skeleton
3. Add 4-bit exhaustive adder harness
4. Run 512 arithmetic cases
5. Fix only minimal VM/sequencer bugs needed for exact correctness
6. Add JSON export + report generation
7. Add tolerance sweep harness
8. Run dt/timing/noise mini-sweep
9. Summarize safe envelope
10. Only then start subtractor or stored-program prototype
```

Recommended stop point for today:

```text
A clean 512/512 4-bit adder report plus a first tolerance envelope.
```

That gives tomorrow's agents a solid platform.

---

## 10. Suggested agent kickoff prompt

Use this directly in Antigravity:

```text
We are hardening SOL Level 6, not chasing novelty.

Read:
- SOL_Master_Chronicle.md Phase 4.0 Level 6 section
- solKnowledge/agent_coding_guide/README.md
- solResearch/walkthroughs/walkthrough_d9d97c9f-bc9e-4364-9b2c-fd8c9939fe89.md
- solResearch/activeResearch/combinatory_physics_analysis.md
- scratch/test_logos_vm_4bit_adder.py

Task:
Build Level 6.1 hardening around the current 2-bit pointer bus and 4-bit serial adder.
First target is exhaustive 512-case verification with invariant monitors.
Second target is a tolerance sweep for dt, damping, timing jitter, and noise.
Do not overclaim. Label every result by robustness status.
Produce JSON results and a markdown report under solResearch/nextBestTest.
```

---

## 11. North star

The north star is not merely an analog adder.

The north star is:

```text
A stored-program semantic/analog substrate where memory, routing, control flow,
and arithmetic are all physically represented in manifold state, while the
compiler simply schedules and verifies those physical transitions.
```

Level 6 is the bridge from component physics to software.

The next two milestones should make that bridge load-bearing.
