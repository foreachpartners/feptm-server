# WF-13: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Web deps: add zustand and @tanstack/react-query in feptm-web/package.json; QueryClient retry 0 in src/app/providers.tsx; wrap src/app/layout.tsx | FR-PROJECT-001 | — | done | 2026-09-04T09:48 |
| T-02 | Types + API: add ProjectListItem and ProjectListResponse in src/types/project.ts; fetchProjectList in src/lib/api/projects.ts with // @req FR-PROJECT-001 | FR-PROJECT-001 | T-01 | done | 2026-09-04T09:50 |
| T-03 | Feature: useProjectList.ts, projectDashboardStore.ts, ProjectDashboard.tsx, ProjectNameList.tsx, CreateProjectOverlay.tsx in src/features/projects/ | FR-PROJECT-001 | T-02 | done | 2026-09-04T09:50 |
| T-04 | UI chrome: AppHeader.tsx, PrimaryButton.tsx, globals.css tokens, public logo | FR-PROJECT-001 | T-03 | done | 2026-09-04T09:50 |
| T-05 | Routes: compose dashboard in src/app/page.tsx; redirect src/app/projects/new/page.tsx to /; Link to /projects/[projectId] | FR-PROJECT-001 | T-04 | done | 2026-09-04T09:50 |
| T-06 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-PROJECT-001 | T-05 | done | 2026-09-04T09:52 |
| T-07 | Fix list fetch: GET /api/projects/ (trailing slash) so FastAPI does not 307 to :8000 (CORS) | FR-PROJECT-001 | T-06 | done | 2026-09-04T10:32 |
| T-08 | Next rewrite: proxy GET /api/projects to upstream /api/projects/ so FastAPI 307 to :8000 never happens | FR-PROJECT-001 | T-07 | done | 2026-09-04T10:55 |