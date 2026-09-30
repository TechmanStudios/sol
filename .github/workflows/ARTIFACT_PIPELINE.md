# SOL GitHub Actions Artifact Pipeline Convention

Use this convention for **all current and future workflows** so artifacts can be synced locally with one shared pipeline (`tools/analysis/sync_github_artifacts.py`).

## Artifact naming format

`<artifact_kind>-<run_source>-<github.run_id>`

Examples:
- `self-train-full-phone-22053459642`
- `pipeline-server-22060000000`
- `rsi-cycle-desktop-22070000000`

## Required fields

- `artifact_kind`: short, stable workflow-specific slug (`self-train-fast`, `cortex-session`, `evolve`, `pipeline`, `dream-session`, `rsi-cycle`)
- `run_source`: one of `phone`, `desktop`, `server`
- `github.run_id`: always include the numeric run id as the final token

## Workflow trigger policy

- `workflow_dispatch`: expose `run_source` as an input (`phone|desktop|server`)
- `schedule`, `workflow_run`, and issue-label automation: set `run_source=server`

## Upload step template

```yaml
- name: Upload artifacts
  uses: actions/upload-artifact@v4
  with:
    name: <artifact_kind>-${{ <resolved_run_source> }}-${{ github.run_id }}
    path: |
      <artifact paths>
    retention-days: 90
```

## Sync compatibility

The local sync tool can filter artifacts by source:

```bash
python tools/analysis/sync_github_artifacts.py --required-run-source phone
```

Supported values are `any`, `phone`, `desktop`, `server`.
