# Security Policy

## Supported versions

SOL is **pre-1.0 research software** and is developed on the default branch.
Only the latest commit on the default branch receives security attention.

| Version          | Supported          |
| ---------------- | ------------------ |
| `main` (latest)  | :white_check_mark: |
| Older snapshots  | :x:                |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report privately via one of the following channels:

1. **GitHub private vulnerability reporting** — preferred.
   Go to the repository's **Security** tab → **Report a vulnerability**.
2. **Email** — contact Techman Studios via the address listed on
   [techmanstudios.com](https://techmanstudios.com) with the subject line
   `SOL security report`.

When reporting, please include:

- A description of the issue and its potential impact.
- Steps to reproduce, or a minimal proof of concept.
- The commit SHA / branch you observed it on.
- Any suggested mitigation, if you have one.

## What to expect

- We will acknowledge receipt within **5 business days**.
- We will provide an initial assessment within **14 days**.
- Coordinated disclosure: we will work with you on a fix and a disclosure
  timeline. We ask that you do not publicly disclose the issue until a fix is
  released or until **90 days** have passed, whichever is sooner.

## Scope

In-scope:

- Code in this repository (Python tooling under `tools/`, JS engine prototypes
  under `solEngine/`, CI workflows under `.github/workflows/`).
- Documented configuration patterns (`.env.example`, agent / skill definitions).

Out of scope:

- Vulnerabilities in third-party dependencies (please report those upstream;
  we will track and patch where applicable).
- Issues that require already-compromised credentials or local machine access.
- Findings against archived experiment scripts or historical dashboards that
  are kept for audit purposes only.

## Secrets

If you discover a credential or token committed to this repository, please
report it via the private channels above so we can rotate and purge it.
