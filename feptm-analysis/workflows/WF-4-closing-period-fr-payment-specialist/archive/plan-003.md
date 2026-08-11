# Plan: Fix close_period 404 — Timesheet ID Read as URL

## Context

`PUT /api/periods` returns HTTP 500 with a 404 from the Google Sheets API. The error URL:

```
https://sheets.googleapis.com/v4/spreadsheets/https%3A%2F%2Fdocs.google.com%2Fspreadsheets%2Fd%2F1iRRA_Rc...
```

A full URL is being URL-encoded and passed as `spreadsheetId`.

## Root Cause

The write path and read path for the timesheet column in the Team sheet are **asymmetric**:

| Phase | Code | Behavior |
|-------|------|----------|
| **Write** | `_apply_updates` (specialist_storage.py:210-211) | Converts plain ID → full URL: `https://docs.google.com/spreadsheets/d/{id}` before writing to cell |
| **Read** | `_parse_row` (specialist_storage.py:160) | Returns raw cell value with no ID extraction |

After a sync creates a timesheet, the Team sheet cell contains the full URL. On the next operation that re-reads the Team sheet (close_period, sync_rates, etc.), `sp.timesheet` contains the full URL. Methods like `close_period_in_timesheet` and `_sum_timesheet_hours` pass this URL directly as `spreadsheetId` to the Sheets API, causing a 404.

## Fix

### Primary Fix: `feptm-server/src/feptm/storage/specialist_storage.py`

In `_parse_row`, after reading the `timesheet` cell value (line 160), normalize it to a plain spreadsheet ID:

```python
# Line 160-161 (current)
timesheet = _opt(row, hmap.get("timesheet"))

# Line 160-161 (fixed)
timesheet_raw = _opt(row, hmap.get("timesheet"))
timesheet = utils.extract_id_from_hyperlink_formula(timesheet_raw or "") or timesheet_raw
```

This leverages the existing `utils.extract_id_from_hyperlink_formula` which already handles:
- HYPERLINK formulas: `=HYPERLINK("url"; "text")`
- Direct spreadsheet URLs: `docs.google.com/spreadsheets/d/ID`
- Falls back to last path segment if it looks like a Google ID

Files affected by this change — all consumers of `sp.timesheet` that pass it to the Sheets API:
- `close_period_in_timesheet` (project_storage.py:460)
- `_sum_timesheet_hours` (project_storage.py:730)
- `remove_stale_specialists` (not applicable — uses tab formulas, not timesheet ID)
- `get_import_timesheet_formula` (config_storage.py — already has URL handling)

No other files need changes. The fix is one line in the parsing layer.

## File-Level Changes

### `feptm-server/src/feptm/storage/specialist_storage.py`

Lines 160-161:

```python
# BEFORE
timesheet = _opt(row, hmap.get("timesheet"))

# AFTER
timesheet_raw = _opt(row, hmap.get("timesheet"))
timesheet = utils.extract_id_from_hyperlink_formula(timesheet_raw or "") or timesheet_raw
```

---

## REST API Changes

None.

## Config Changes

None.

## Security Considerations

None.
