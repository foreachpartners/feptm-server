# Tasks: FR-SYNC-001

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Fix `sync_project_specialists` — count actual creations for `update_timesheet_ids` guard | FR-SYNC-001 | — | done | 2026-08-08T23:16 |
| T-02 | Fix `sync_project_rates` — auto-create timesheets, add to Current Period, then sync rates | FR-SYNC-001 | T-01 | done | 2026-08-08T23:17 |
| T-03 | Handler `@req` annotations — add FR-SYNC-001 to both handlers | FR-SYNC-001 | T-02 | done | 2026-08-08T23:17 |
| T-04 | Tests: update existing + new test for auto-creation behavior | FR-SYNC-001 | T-03 | done | 2026-08-08T23:18 |
| T-05 | Audit: typecheck + tests + zero ERR/WARN in touched files | FR-SYNC-001 | T-04 | done | 2026-08-08T23:18 |
