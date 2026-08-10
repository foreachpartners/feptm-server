# Tasks: Fix IMPORTRANGE placeholder mismatch

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Storage: change `get_import_timesheet_formula` replace target from `{timesheet_id}` to `SpecialistSpreadsheetID` | FR-SYNC-001 | — | done | 2026-08-10T13:15 |
| T-02 | Tests: verify `get_import_timesheet_formula` substitutes SpecialistSpreadsheetID with actual timesheet ID | FR-SYNC-001 | T-01 | done | 2026-08-10T13:20 |
| T-03 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-SYNC-001 | T-02 | done | 2026-08-10T13:25 |
