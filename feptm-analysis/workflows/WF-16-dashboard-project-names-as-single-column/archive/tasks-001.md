# WF-16: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Web: in `feptm-web/src/app/globals.css` set `.project-name-list` to `display: grid; gap: var(--space-sm)` with no `grid-template-columns`; set `.project-name-list__link` padding to `var(--space-md) var(--space-lg)`. Leave `.project-name-list__item` and `.project-name-list__link:hover` unchanged. Do not edit `feptm-web/src/features/projects/ProjectNameList.tsx`, `ProjectDashboard.tsx`, or `ProjectCardTables.tsx`. | FR-PROJECT-001 | — | done | 2026-09-05T21:12 |
| T-02 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-PROJECT-001 | T-01 | done | 2026-09-05T21:13 |
