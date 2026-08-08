# Tasks: FR-SYNC-RATES-001

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Models: Add `ProjectSyncRatesRequest` + `ProjectSyncRatesResponse` to `models/project.py` | FR-SYNC-RATES-001 | — | done | 2026-08-08T21:41 |
| T-02 | Models: Export new models in `models/__init__.py` | FR-SYNC-RATES-001 | T-01 | done | 2026-08-08T21:41 |
| T-03 | Service: Add `sync_project_rates` method to `TimesheetProjectService` | FR-SYNC-RATES-001 | T-02 | done | 2026-08-08T21:41 |
| T-04 | Handler: Add `POST /api/projects/sync-rates` with `@req` annotation | FR-SYNC-RATES-001 | T-03 | done | 2026-08-08T21:42 |
| T-05 | Tests: Unit test for `sync_project_rates` in `test_project_service.py` | FR-SYNC-RATES-001 | T-03 | done | 2026-08-08T21:43 |
| T-06 | Tests: API integration test for `/projects/sync-rates` in `test_projects.py` | FR-SYNC-RATES-001 | T-04 | done | 2026-08-08T21:43 |
| T-07 | Audit: Full repo audit — zero ERR, zero WARN in touched files | FR-SYNC-RATES-001 | T-06 | done | 2026-08-08T21:43 |
