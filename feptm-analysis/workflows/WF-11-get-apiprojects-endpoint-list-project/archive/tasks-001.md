# Tasks: GET /api/projects (FR-PROJECT-001)

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Add `list_drive_folders()` to `GoogleSheetsService` | FR-PROJECT-001 | — | done | 2026-09-02T12:01 |
| T-02 | Add `list_projects()` to `ProjectStorageProtocol` | FR-PROJECT-001 | — | done | 2026-09-02T12:01 |
| T-03 | Add `list_projects()` to `ProjectStorage` | FR-PROJECT-001 | T-02 | done | 2026-09-02T12:02 |
| T-04 | Add `list_projects()` to `TimesheetProjectService` | FR-PROJECT-001 | T-03 | done | 2026-09-02T12:03 |
| T-05 | Add `ProjectListItem`, `ProjectListResponse` models | FR-PROJECT-001 | — | done | 2026-09-02T12:04 |
| T-06 | Add `GET /api/projects` handler | FR-PROJECT-001 | T-04, T-05 | done | 2026-09-02T12:05 |
| T-07 | Add unit tests for list endpoint | FR-PROJECT-001 | T-06 | done | 2026-09-02T12:07 |
| T-08 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-PROJECT-001 | T-07 | done | 2026-09-02T12:08 |
