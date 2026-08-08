---
name: audit
description: Run workspace audit checks and evaluate compliance against rules.
context: fork
agent: Explore
model: haiku
allowed-tools: Bash(env -u VIRTUAL_ENV uv run --project */sdd-cli sdd-cli *), Read
---

# audit

Read and follow the procedure in [`../feptm-analysis/docs/skills/audit.md`](../feptm-analysis/docs/skills/audit.md).
