# Tasks: Remove Double Names Handling — Log Error & Abort Sync

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Remove `display_name` field from Specialist model | FR-SYNC-001 | — | done | 2026-08-11T12:00 |
| T-02 | Replace `_resolve_display_names` with `_has_duplicate_names` in project_service.py | FR-SYNC-001 | T-01 | done | 2026-08-11T12:05 |
| T-03 | Purge `display_name or name` → `name` in project_storage.py | FR-SYNC-001, FR-SYNC-RATES-001 | T-02 | done | 2026-08-11T12:08 |
| T-04 | Remove `(N)` suffix fallback and dedup from `archive_current_period` | FR-SYNC-RATES-001 | T-03 | done | 2026-08-11T12:10 |
| T-05 | Rewrite AR-DATA-001.yaml spec to log-and-abort behavior | FR-SYNC-001 | T-04 | done | 2026-08-11T12:12 |
| T-06 | Update tests — remove display_name tests, add abort-on-duplicate tests | FR-SYNC-001, FR-SYNC-RATES-001 | T-05 | done | 2026-08-11T12:18 |
| T-07 | Full audit — zero ERR/WARN in touched files | FR-SYNC-001, FR-SYNC-RATES-001 | T-06 | done | 2026-08-11T12:20 |
