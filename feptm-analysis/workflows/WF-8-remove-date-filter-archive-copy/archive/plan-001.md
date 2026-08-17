# Plan: WF-8 — Remove date filter, copy Current Period for archive

## Requirement Traceability

| FR | Version | Change |
|----|---------|--------|
| FR-PAYMENT-001 | v3 | Remove `start_date`/`end_date` from close period. Entry selection uses empty Payment Period only. Archive copies Current Period tab instead of building from scratch. |
| FR-SPECIALIST-001 | v2 | Remove `_has_invalid_dates()` from sync and close_period. Date parsing errors no longer abort the pipeline. |

## Architecture Overview

**Affected repos:** feptm-server, feptm-analysis

**Data flow (close period — current):**
1. `PUT /api/periods` with `project_id`, `period_name`, `start_date`, `end_date`
2. `close_period()` validates dates, iterates specialists
3. `close_period_in_timesheet()` parses every date in timesheet, filters by range, writes period_name
4. `archive_current_period()` reads Current Period, calls `_sum_period_hours()` per specialist (which also parses dates), recalculates all costs, builds new sheet from scratch

**Data flow (close period — new):**
1. `PUT /api/periods` with `project_id`, `period_name`
2. `close_period()` iterates specialists
3. `close_period_in_timesheet()` finds empty Payment Period cells, writes period_name
4. `archive_current_period()` duplicates Current Period tab via `duplicateSheet`, writes period_name to Period column, replaces formulas with values

## REST API / OpenAPI Schema Changes

### `PUT /api/periods`

**Before:**
```json
{
  "project_id": "string",
  "period_name": "string",
  "start_date": "datetime",
  "end_date": "datetime"
}
```

**After:**
```json
{
  "project_id": "string",
  "period_name": "string"
}
```

`start_date` and `end_date` removed. Status codes unchanged (200, 422, 500).

## Storage Changes

### `src/feptm/models/payment_period.py`

Remove `start_date` and `end_date` fields from `ClosePeriodRequest`.

### `src/feptm/storage/protocols.py`

Update signatures:
- `close_period_in_timesheet(timesheet_id, period_name) -> int` — remove `start_date`, `end_date`
- `archive_current_period(spreadsheet_id, period_name) -> bool` — remove `specialists`, `start_date`, `end_date`

### `src/feptm/storage/project_storage.py`

**`close_period_in_timesheet()`** (line 456):
- Remove `start_date`/`end_date` parameters
- Remove date column lookup (`date_col`)
- Remove `_serial_to_date()` call and date range check
- Loop: for each row, if Payment Period cell is empty → write `period_name`
- Remove date validation error (no more `raise Exception("Invalid date format...")`)

**`archive_current_period()`** (line 558):
- Remove `specialists`, `start_date`, `end_date` parameters
- Remove `_sum_period_hours()` calls
- Remove row-by-row recalculation logic
- New implementation:
  1. Read Current Period sheet to get `sheetId`
  2. `duplicateSheet` via `batch_update` with `sourceSheetId` and `newSheetName=period_name`
  3. Read all values from the new tab with `UNFORMATTED_VALUE`
  4. Write all values back as `RAW` (replaces formulas with computed values)
  5. Find Period column, write `period_name` to all data rows (rows 2+)
  6. Return True

**Remove entirely:**
- `_sum_period_hours()` (line 829) — no longer needed
- `_serial_to_date()` (line 996) — no longer needed

### `src/feptm/timesheets/project_service.py`

**Remove `_has_invalid_dates()`** (line 44) entirely.

**`sync_project_specialists()`** (line 101):
- Remove `_has_invalid_dates(specialists)` call (line 126)

**`sync_project_rates()`** (line 167):
- Remove `_has_invalid_dates(specialists)` call (line 196)

**`close_period()`** (line 265):
- Remove `start_date`/`end_date` parameters
- Remove `_has_invalid_dates(specialists)` call (line 286)
- Remove `start_date`/`end_date` from `close_period_in_timesheet()` calls (lines 307, 324)
- Remove `start_date`/`end_date` from `archive_current_period()` calls (lines 337-338, 351-352)
- Remove `specialists` list from `archive_current_period()` calls — new signature only needs `spreadsheet_id` and `period_name`

### `src/feptm/api/v1/periods.py`

Remove `start_date`/`end_date` from `service.close_period()` call.

## Implementation Details

### `duplicateSheet` API usage

```python
self._sheets.batch_update(
    spreadsheet_id=spreadsheet_id,
    requests=[{
        "duplicateSheet": {
            "sourceSheetId": cp_sheet_id,
            "newSheetName": period_name,
        }
    }],
)
```

### Archive formula replacement

After duplicating, read all values with `UNFORMATTED_VALUE` and write back as `RAW`:

```python
range_name = f"{period_name}!A1:{last_col}{last_row}"
result = self._sheets.sheets_service.spreadsheets().values().get(
    spreadsheetId=spreadsheet_id,
    range=range_name,
    valueRenderOption="UNFORMATTED_VALUE",
).execute()
values = result.get("values", [])
self._sheets.update_range(
    spreadsheet_id=spreadsheet_id,
    range_name=range_name,
    values=values,
    value_input_option="RAW",
)
```

### Period column write

After formula replacement, find Period column index and write `period_name` to all data rows:

```python
period_col_letter = self._sheets.column_index_to_letter(period_idx)
range_name = f"{period_name}!{period_col_letter}2:{period_col_letter}{len(values)}"
period_values = [[period_name]] * (len(values) - 1)
self._sheets.update_range(
    spreadsheet_id=spreadsheet_id,
    range_name=range_name,
    values=period_values,
    value_input_option="RAW",
)
```

## Security Considerations

None. No changes to authentication, authorization, or secret handling.

## Config Changes

None. No new environment variables.

## Test Plan

| # | Test | File | Validates |
|---|------|------|-----------|
| 1 | `test_close_period_in_timesheet_no_date_filter` | `test_project_service.py` | All empty Payment Period cells get period_name, regardless of date |
| 2 | `test_close_period_in_timesheet_skips_filled` | `test_project_service.py` | Non-empty Payment Period cells are not overwritten |
| 3 | `test_archive_copies_current_period` | `test_project_service.py` | `duplicateSheet` called, formulas replaced with values, Period column written |
| 4 | `test_archive_skips_if_exists` | `test_project_service.py` | If tab already exists, return False |
| 5 | `test_close_period_no_date_params` | `test_project_service.py` | `close_period()` works without `start_date`/`end_date` |
| 6 | `test_close_period_request_no_dates` | `test_payment_period.py` | `ClosePeriodRequest` accepts only `project_id` and `period_name` |
| 7 | `test_close_payment_period_api_no_dates` | `test_periods.py` | API accepts request without `start_date`/`end_date` |
| 8 | `test_sync_no_abort_on_invalid_dates` | `test_project_service.py` | Sync proceeds even with unparseable dates |
| 9 | Remove `TestSerialToDate` class | `test_project_service.py` | `_serial_to_date` removed |
| 10 | Remove `test_archive_*` tests that mock `_sum_period_hours` | `test_project_service.py` | Old archive logic removed |
| 11 | Audit: full repo audit | — | Zero ERR, zero WARN in touched files |
