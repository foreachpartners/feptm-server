# Tasks: Use spreadsheet URLs instead of raw IDs

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Storage: substitute spreadsheet URL in IMPORTRANGE formula (config_storage.py) | FR-SYNC-001 | — | done | 2026-08-10T13:40 |
| T-02 | Storage: write spreadsheet URL to Team sheet Timesheet column (specialist_storage.py) | FR-SYNC-001 | — | done | 2026-08-10T13:40 |
| T-03 | Tests: update expectations to match URL format | FR-SYNC-001 | T-01, T-02 | done | 2026-08-10T13:40 |
| T-04 | Audit: full repo audit — zero ERR, zero WARN | FR-SYNC-001 | T-03 | done | 2026-08-10T13:45 |
