# feptm-server

service

## Config

- Prefix: `FEPTM_FEPTM_SERVER__`
- HTTP port: 8000

## Rules Reference

Repo-specific AR specs:

- `AR-LINEAGE-001` — @req Annotation Format
- `AR-LINEAGE-002` — Commit Message Format
- `AR-SECRETS-001` — Secret Protection
- `AR-WORKSPACE-001` — Workspace Overview
- `AR-WRITING-001` — LLM-Oriented Writing Style

Always-apply specs also included: AR-LINEAGE-001, AR-LINEAGE-002, AR-SECRETS-001, AR-WORKSPACE-001, AR-WRITING-001.

See AR specs: `../feptm-analysis/ar-specs/`

## Run

```bash
uv run uvicorn feptm.main:app --host 0.0.0.0 --port 8000 --reload
```

## Test

```bash
make lint && make typecheck && make test
```

## DO NOT

- @req in service/business logic layer functions (traced through handler).
- @req in repository / storage layer functions (infrastructure, traced through handler).
- @req on shared utility functions unless the utility exists solely for one requirement.
- Behavioral commits (feat, fix, refactor) without a requirement ID reference.
- Requirement IDs outside brackets or not at the end of the subject line.
- Multiple bracket blocks on one subject. Always combine IDs into a single comma-separated bracket.
- Log secrets (encryption keys, API keys, tokens, DB credentials) via logging.debug, print, or any logging path.
- Include secrets in error messages or error types.
- Hardcode secrets in source — load from env at startup or from a secret store.
- Commit backup/scratch files (*.bak, *.backup, *.orig) that may carry pre-redaction content.
- Duplicate workspace structure information — link to feptm-workspace/README.md instead.
- Hardcode absolute paths in scripts — resolve from $0 or use workspace-relative paths.
- Motivational phrases: 'Great job!', 'Perfect!', 'Excellent!'.
- Uncertainty markers: 'maybe', 'perhaps', 'I think'.
- Filler words: 'basically', 'essentially', 'actually'.
- Apologies: 'sorry', 'unfortunately'.
- Conversational check-ins: 'Make sense?', 'Got it?'.
- Subjective qualifiers: 'elegant', 'beautiful', 'clean'.
- Non-English text in rules and documentation.