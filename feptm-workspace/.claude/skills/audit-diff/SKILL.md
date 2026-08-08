---
name: audit-diff
description: Run audit on changed files only. Reports new violations vs baseline. No commit.
context: fork
agent: Explore
model: haiku
allowed-tools: Bash(env -u VIRTUAL_ENV uv run --project */sdd-cli sdd-cli *), Read
---

# audit-diff

Read and follow the procedure in [`../feptm-analysis/docs/skills/audit-diff.md`](../feptm-analysis/docs/skills/audit-diff.md).
