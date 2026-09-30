# Contributing to SOL

Thanks for your interest in SOL. This repository is a **live research engine**,
not a stable product, so the contribution model is biased toward small,
testable, well-documented changes that respect the existing audit trail.

## Working style

- **Small, testable changes.** Prefer one focused PR over a sweeping refactor.
- **Keep experiments isolated.** New explorations belong in `sandBox/` or a
  scoped folder under `solKnowledge/working/`. Promote reusable code into
  `tools/` only after it has stabilized.
- **Document a minimal run recipe.** Inputs → steps → expected outputs.
- **Preserve the audit trail.** Don't delete versioned artifacts (e.g.
  `sol_dashboard_v3_*.html`, phase iterations under `solEngine/`, prior proof
  packets) without a written rationale.

## Repo layout (where things go)

| You're adding…                          | Put it in…                                      |
| --------------------------------------- | ----------------------------------------------- |
| Reusable Python module                  | `tools/<package>/`                              |
| One-off experiment script               | repo root (`*.py`) or `sandBox/`                |
| Engine prototype iteration              | `solEngine/`                                    |
| Curated knowledge / consolidations      | `solKnowledge/consolidated/`                    |
| Proof packet                            | `solKnowledge/proof_packets/domains/<domain>/`  |
| Custom agent / skill / prompt           | `.github/agents|skills|prompts/`                |
| Always-on project guidance              | `.github/instructions/`                         |
| CI workflow                             | `.github/workflows/`                            |
| Tests                                   | `tests/<area>/`                                 |

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env       # secrets stay local
pytest -m "not slow"
```

For LLM-driven workflows you will need a GitHub fine-grained PAT with
**Models** access set as `GITHUB_TOKEN` in `.env`.

## Tests

- Run the fast suite locally before opening a PR: `pytest -m "not slow"`.
- New tooling under `tools/` should ship with tests under `tests/<area>/`.
- Mark slow / network / model-calling tests with `@pytest.mark.slow`.

## Agent-driven contributions

Much of the work in this repo is orchestrated through the **SolTech** /
**SOL lab** agent kit under `.github/`. If you are touching agent or skill
definitions, follow the model documented in
[`.github/README_SolTech.md`](.github/README_SolTech.md):

- **Instructions** = always-on project guidance.
- **Prompt files** = reusable short workflows (loaded into the user prompt).
- **Custom agents** = persistent behavior overrides.
- **Skills** = bundled instruction + scripts/templates, progressively loaded.

## Working with the automated workflows

This repo runs scheduled GitHub Actions that **commit research artifacts
directly to the default branch** (see the *Automated workflows* section in
[`README.md`](README.md) for the full schedule). A few practical implications
for contributors:

- **Rebase often.** `main` moves on its own — daily for `sol-hippocampus`,
  weekly for `sol-cortex` and `sol-pipeline`. Long-lived branches will rot
  quickly. Prefer `git pull --rebase` before pushing.
- **Don't fight the bots.** If you see commits authored by `sol-*[bot]`
  touching files under `data/`, `solKnowledge/`, or `tests/regression/golden/`,
  those are intentional pipeline outputs — leave them alone.
- **Fork PRs won't trigger the automation.** None of the workflows have a
  `pull_request` trigger, so a CI run on your fork PR is *not* expected. A
  maintainer will run the relevant workflow manually after merge if needed.
- **If you change a workflow**, validate it with a `workflow_dispatch` run on
  a branch first. Pay attention to the `permissions:`, `concurrency:`, and
  trigger blocks — they are deliberately scoped for public-repo safety.
- **Adding a new auto-committing workflow?** Match the existing pattern:
  - Explicit `permissions:` (no `write-all`).
  - A `concurrency:` group to prevent overlapping runs.
  - A `git pull --rebase` retry loop around the push.
  - A `[bot]` git identity using `users.noreply.github.com` (preferred).
  - Update the workflow table in `README.md`.

## Commit / PR conventions

- Use **clear, scoped commit messages** (e.g. `cortex: add dream-session adapter to ledger`).
- Keep PRs focused; if a change pulls in unrelated cleanups, split them.
- Reference any related proof packet, run bundle, or chronicle entry in the PR body.

## Security & secrets

- **Never commit secrets.** `.env` is git-ignored; use `.env.example` to
  document new variables.
- For vulnerability reports, see [`SECURITY.md`](SECURITY.md).

## Code of Conduct

By participating, you agree to abide by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Questions

Open a GitHub Discussion or Issue. For research collaboration or funding-related
inquiries, contact Techman Studios via [techmanstudios.com](https://techmanstudios.com).
