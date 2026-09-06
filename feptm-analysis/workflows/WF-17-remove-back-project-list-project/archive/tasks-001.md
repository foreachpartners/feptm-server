# WF-17: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Spec: add header-link AC + revision v3 in `feptm-analysis/fr-specs/FR-PROJECT-001.yaml`; add no-Back AC in `feptm-analysis/fr-specs/FR-SHEET-001.yaml` | FR-PROJECT-001, FR-SHEET-001 | — | done | 2026-09-06T17:47 |
| T-02 | Header: wrap logo + wordmark in `<a href="https://foreachpartners.com/">` in `feptm-web/src/components/AppHeader.tsx`; add only `text-decoration: none` to `.app-header__brand` in `feptm-web/src/app/globals.css` | FR-PROJECT-001 | T-01 | done | 2026-09-06T17:47 |
| T-03 | Card: delete Back control and `Link` import in `feptm-web/src/features/projects/ProjectCard.tsx`; delete `.project-card__back` and `:disabled` in `feptm-web/src/app/globals.css` | FR-SHEET-001 | T-01 | done | 2026-09-06T17:47 |
| T-04 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-PROJECT-001, FR-SHEET-001 | T-02, T-03 | done | 2026-09-06T17:50 |
