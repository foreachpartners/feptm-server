# Tasks: Optimize Google Sheets API Calls

## Task Table

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Phase 1.1: Remove duplicate Team read in sync_project_rates | FR-SYNC-RATES-001 | — | done | 2026-09-07T00:31 |
| T-02 | Phase 1.2: Skip A1 write if formula matches in add_specialist_to_report | FR-SYNC-001 | — | done | 2026-09-07T00:33 |
| T-03 | Phase 1.3: Pre-load all formulas on first cache miss in ConfigStorage | FR-SYNC-001 | — | done | 2026-09-07T00:35 |
| T-04 | Phase 1.4: Remove time.sleep(0.25) from sync loops | FR-SYNC-001 | — | done | 2026-09-07T00:37 |
| T-05 | Phase 2: Add contextvar metadata cache to GoogleSheetsService | FR-SYNC-001, FR-SPECIALIST-001 | — | done | 2026-09-07T00:40 |
| T-06 | Phase 2: Update all spreadsheets.get callers to use cache | FR-SYNC-001, FR-SPECIALIST-001 | T-05 | done | 2026-09-07T00:45 |
| T-07 | Phase 2: Add cache invalidation after mutations | FR-SYNC-001, FR-SPECIALIST-001 | T-05 | done | 2026-09-07T00:48 |
| T-08 | Phase 3: Eliminate redundant re-reads in update_timesheet_ids | FR-SPECIALIST-001 | T-05 | done | 2026-09-07T00:51 |
| T-09 | Phase 4: Add sync_rates_batch method to ProjectStorage | FR-SYNC-RATES-001 | T-05, T-06 | done | 2026-09-07T00:54 |
| T-10 | Phase 4: Restructure sync_project_rates into phases | FR-SYNC-RATES-001 | T-09 | done | 2026-09-07T01:05 |
| T-11 | Phase 5: Batch find_file_in_folder in SpecialistStorage | FR-SPECIALIST-001 | T-05 | done | 2026-09-07T01:08 |
| T-12 | Phase 5: Combine metadata+values in get_project_metadata | FR-SYNC-001 | T-05 | done | 2026-09-07T01:11 |
| T-13 | Tests: Update all tests for new methods and signatures | FR-SYNC-001, FR-SYNC-RATES-001, FR-SPECIALIST-001 | T-01–T-12 | done | 2026-09-07T01:13 |
| T-14 | Audit: Full repo audit — zero ERR, zero WARN in touched files | FR-SYNC-001, FR-SYNC-RATES-001, FR-SPECIALIST-001 | T-13 | done | 2026-09-07T01:15 |

## Task Details

### T-01: Remove duplicate Team read
- **File:** `src/feptm/timesheets/project_service.py:156,171`
- **Action:** Delete line 171 (second `list_from_sheet` call)
- **Verify:** `make typecheck && make test`

### T-02: Skip A1 write if formula matches
- **File:** `src/feptm/storage/project_storage.py:256-275`
- **Action:** Add `_read_cell_formula` helper, check before writing A1
- **Verify:** `make typecheck && make test`

### T-03: Pre-load all formulas
- **File:** `src/feptm/storage/config_storage.py:19-61`
- **Action:** Add `_all_formulas_loaded` flag, `_load_all_formulas` method
- **Verify:** `make typecheck && make test`

### T-04: Remove time.sleep
- **File:** `src/feptm/timesheets/project_service.py:144`
- **Action:** Delete `time.sleep(0.25)` line
- **Verify:** `make typecheck && make test`

### T-05: Add metadata cache
- **File:** `src/feptm/services/google_sheets_service.py`
- **Action:** Add `_metadata_cache` contextvar, `get_all_sheets`, `invalidate_metadata_cache` methods
- **Verify:** `make typecheck && make test`

### T-06: Update spreadsheets.get callers
- **Files:** `src/feptm/storage/project_storage.py` (5 locations)
- **Action:** Replace direct `spreadsheets.get` with `get_all_sheets`
- **Verify:** `make typecheck && make test`

### T-07: Add cache invalidation
- **File:** `src/feptm/storage/project_storage.py`
- **Action:** Call `invalidate_metadata_cache` after addSheet, insertDimension, duplicateSheet, deleteSheet
- **Verify:** `make typecheck && make test`

### T-08: Eliminate re-reads in update_timesheet_ids
- **File:** `src/feptm/storage/specialist_storage.py:182-249`
- **Action:** `_prepare_updates` returns `(updates, headers)`, `_apply_updates` accepts headers
- **Verify:** `make typecheck && make test`

### T-09: Add sync_rates_batch
- **File:** `src/feptm/storage/project_storage.py`
- **Action:** New method reads once, builds all updateCells, one batch_update
- **Verify:** `make typecheck && make test`

### T-10: Restructure sync_project_rates
- **File:** `src/feptm/timesheets/project_service.py:153-246`
- **Action:** Phases A-F (read, create timesheets, write IDs, add tabs, write formulas, sync rates)
- **Verify:** `make typecheck && make test`

### T-11: Batch find_file_in_folder
- **File:** `src/feptm/storage/specialist_storage.py`
- **Action:** Pre-load all spreadsheets in folder, match by name in-memory
- **Verify:** `make typecheck && make test`

### T-12: Combine metadata+values
- **File:** `src/feptm/storage/project_storage.py:194-254`
- **Action:** Use `spreadsheets.get(includeData=True, ranges=[...])`
- **Verify:** `make typecheck && make test`

### T-13: Update tests
- **Files:** `tests/timesheets/test_project_service.py`, `tests/timesheets/test_specialist_service.py`, `tests/services/test_google_sheets_service.py`
- **Action:** Update mocks for new methods, add tests for batch operations
- **Verify:** `make test`

### T-14: Full repo audit
- **Action:** Run `sdd-cli.sh verify --wf-dir <wf_dir> --phase finalize`
- **Verify:** Exit 0, zero ERR, zero WARN
