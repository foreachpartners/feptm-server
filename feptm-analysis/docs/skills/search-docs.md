# search-docs — Search across <project> sources

<project> ships no dedicated search wrapper. Use `rg` (ripgrep) — or `grep -rn` if `rg` is not available — scoped to specific source roots. Iterate until convergence.

## Sources

| Source | Path (relative to workspace root) | When to use |
|---|---|---|
| `proto` | `../<proto-repo>/openapi/` | OpenAPI operations, request/response schemas, enum values |
| `proto-sdk` | `../<proto-repo>/sdk/` | Generated Rust DTOs, generated TypeScript SDK |
| `backend-code` | `../<backend-repo>/src/` | Rust handlers, domain model, mappers, db |
| `storefront-code` | `../<webapp-repo>/{app,lib}/` | Next.js pages, API client, components |
| `ar-specs` | `../<analysis-repo>/ar-specs/` | Coding standards, audit rules, prohibitions |
| `fr-specs` | `../<analysis-repo>/fr-specs/` | Functional requirements with acceptance criteria |
| `workflows` | `../<analysis-repo>/workflows/` | Past + active workflow plans, tasks, decisions |
| `analysis-docs` | `../<analysis-repo>/docs/` | Skill procedures, session-context, tools, narrative |
| `readmes` | `../<project>-*/README.md` `../<project>-*/CLAUDE.md` | Repo-level overviews and run instructions |
| `configs` | `../<project>-*/{Cargo.toml,package.json,*.config.*}` | Dependency versions, build config, lint config |

## Procedure

### Step 1 — Initialize

Parse the user's topic into 3-6 keywords. Include domain synonyms. Examples:
- "checkout race" → `checkout`, `concurrent`, `race`, `lock`, `transaction`, `RwLock`
- "OpenAPI x-requirement" → `x-requirement`, `requirement`, `FR-`, `operation`, `path`
- "Cyrillic ban" → `cyrillic`, `non-english`, `AR-WRITING-001`, `language`

Pick 3-5 sources from the table. Track:
- `SEEN_FILES` — paths already encountered (initially empty)
- `USED_KEYWORDS` — terms already searched (initially empty)

### Step 2 — Search (per iteration, max 5 iterations)

For each new keyword, against each selected source path:

```bash
rg -l "<keyword>" <source-path>         # files-only first pass
rg -n -C 2 "<keyword>" <source-path>    # then content with 2-line context
```

Add the keyword to `USED_KEYWORDS`. New files (not in `SEEN_FILES`) get added to `SEEN_FILES`.

If no new files found in this iteration → converged → go to Step 4.

### Step 3 — Expand keywords

Read the most relevant new files. Extract additional keywords from their content: type names, function names, error variants, AR/FR IDs, config keys, file paths cited. Add new keywords to the list. Add new source paths if content cites them.

Increment iteration. If iteration > 5 → stop. Otherwise → back to Step 2.

### Step 4 — Return results

Group by relevance, most relevant first. For each file:

```
**<path>**
<5-15 line excerpt — the most relevant block>
Why: <one line explaining the connection to the topic>
```

Drop tangential matches.

## Constraints

- Read-only — the skill never edits files.
- Use `rg` over `grep` when available (faster, respects `.gitignore`, better unicode).
- Do **not** search inside `target/`, `node_modules/`, `.git/`, or generated trees (`sdk/rust/src/api/_gen/`, `sdk/typescript/src/_gen/`) unless the user explicitly asks — `rg` skips these by default.
- Convergence is expected at 2-3 iterations. If iteration 5 still produces new files, the topic is over-broad; ask the user to narrow.
