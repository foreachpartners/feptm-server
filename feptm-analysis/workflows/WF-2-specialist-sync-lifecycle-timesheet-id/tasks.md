# Tasks: FR-SYNC-001, FR-SPECIALIST-001 (Run 5)

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Storage: Add `find_file_in_folder` method to GoogleSheetsService | FR-SYNC-001 | — | done | 2026-08-11T07:58 |
| T-02 | Storage: Modify `create_timesheet` for Drive dedup | FR-SYNC-001 | T-01 | done | 2026-08-11T07:59 |
| T-03 | Storage: Modify `add_specialist_to_report` to always refresh A1 formula | FR-SYNC-001, FR-SPECIALIST-001 | — | done | 2026-08-11T08:00 |
| T-04 | Tests: `create_timesheet` Drive dedup — reuse and create paths | FR-SYNC-001 | T-02 | done | 2026-08-11T08:01 |
| T-05 | Tests: `add_specialist_to_report` formula refresh — existing and new tab | FR-SYNC-001, FR-SPECIALIST-001 | T-03 | done | 2026-08-11T08:01 |
| T-06 | Tests: Update existing `test_create_timesheet_success` mock | FR-SYNC-001 | T-02 | done | 2026-08-11T08:01 |
| T-07 | Audit: Full repo audit — zero ERR, zero WARN | FR-SYNC-001, FR-SPECIALIST-001 | T-01..T-06 | done | 2026-08-11T08:02 |
