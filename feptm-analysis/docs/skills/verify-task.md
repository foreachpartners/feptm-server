# verify-task — SDD Verification Gate

CLI tool: `./scripts/sdd-cli.sh`
Workflow directory: `<analysis-repo>/workflows/WF-*-*/`

Drives the three-phase verification gate that fep-sdd ships with: capture baseline → re-check on implementation → final lock-down before merge. Each phase produces a different set of checks and uses `WF-*/baseline.yaml` to distinguish pre-existing findings from regressions introduced by the current workflow.

## Phases

| Phase | Purpose | Checks |
|---|---|---|
| `init` | Snapshot pre-existing audit findings + traceability orphans into `baseline.yaml`. Run once per workflow before implementation. | AR audit + orphan scan; serialised to `baseline.yaml`. |
| `implement` | Periodic gate during implementation. | Build/lint suite (full mode) + AR audit delta vs baseline + tasks.md vs git diff (`task_patterns:`). |
| `finalize` | Lock-down before merge. | Build/lint suite + AR audit delta + task-diff + traceability orphan delta. |

## Step 1: Pick or create the baseline

Run `init` once when a workflow begins:

```bash
./scripts/sdd-cli.sh verify --wf-dir <analysis-repo>/workflows/WF-N-slug --phase init
```

Writes `WF-N-slug/baseline.yaml`. Commit this file alongside `session.yaml`.

A clean baseline has empty `findings` and `orphans` arrays per repo — meaning the workflow starts with no audit debt. A non-empty baseline records pre-existing findings that the workflow is *not* required to fix; later phases compare against this baseline to flag only regressions introduced by the workflow.

## Step 2: Periodic checks during implementation

```bash
./scripts/sdd-cli.sh verify --wf-dir <analysis-repo>/workflows/WF-N-slug --phase implement --mode fast
```

`--mode fast` skips the heavy build/test suite (useful for iteration). Use `--mode full` to also run the project's build / lint / test commands against repos with uncommitted changes.

`task_patterns:` blocks on each effective AR spec drive the task-diff check: tasks marked `done` whose description matches a keyword set must produce a file change matching one of the listed glob patterns. Tasks with `skip: true` auto-pass (e.g. audit/review tasks that don't touch code).

## Step 3: Finalize before merge

```bash
./scripts/sdd-cli.sh verify --wf-dir <analysis-repo>/workflows/WF-N-slug --phase finalize --mode full
```

Adds the traceability orphan delta on top of the implement-phase checks: any new `@req`-less handler / contract endpoint since `baseline.yaml` is reported as a regression.

Exit `0` = pass; exit `2` = at least one check failed.

## Step 4: Inspect failures

The command prints `NEW <severity> [<repo>] <check>: <message>` for each new finding and `ORPHAN <kind> <name>` for each new traceability orphan. Resolve each failure by either fixing the code OR updating `audit-exceptions.yaml` (with a justified entry per the project's review-checklist AR-spec) before re-running.

---
