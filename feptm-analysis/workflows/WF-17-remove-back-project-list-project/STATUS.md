# WF-17: Status

**Date**: 2026-09-06
**Ceremony**: medium
**FRs**: FR-PROJECT-001, FR-SHEET-001

## History

| # | Plan | Tasks | Date | Outcome |
|---|------|-------|------|---------|
| 001 | [plan-001.md](archive/plan-001.md) | [tasks-001.md](archive/tasks-001.md) | 2026-09-06 | Implemented |

## Plan summary

Cycle 1: remove `Back to project list` from the project card. Wrap the ForEach Partners logo and wordmark in `AppHeader` as one `<a href="https://foreachpartners.com/">` on the dashboard and the card. Colors, styles, size, and placement of the logo and wordmark MUST NOT change; CSS adds only `text-decoration: none`. feptm-server unchanged.

## Baseline audit

- Policy: `fix_err`
- web: 0 ERR, 1 WARN (`.gitignore` missing `.DS_Store`)
- No ERR remediation in this workflow

## Implementation

Cycle 1: 4/4 tasks done.

| Task | Status | Note |
|------|--------|------|
| T-01 | done | FR-PROJECT-001 AC + v3; FR-SHEET-001 no-Back AC |
| T-02 | done | `AppHeader` brand link; `.app-header__brand` `text-decoration: none` |
| T-03 | done | Back control and `.project-card__back` removed |
| T-04 | done | verify implement OK; touched files 0 ERR, 0 new WARN; baseline WARN `.DS_Store` unchanged |

## Progress

- 2026-09-06T17:57 header brand link: `target="_blank"` `rel="noopener noreferrer"`
- 2026-09-06T17:50 cycle 1 implement complete: 4/4 done, 0 blocked
- 2026-09-06T17:50 T-04 done — audit touched files: 0 ERR; WARNs only in untouched files
- 2026-09-06T17:48 T-02/T-03 done — header link + Back removed; `pnpm typecheck` OK
- 2026-09-06T17:47 T-01 done — FR ACs updated
