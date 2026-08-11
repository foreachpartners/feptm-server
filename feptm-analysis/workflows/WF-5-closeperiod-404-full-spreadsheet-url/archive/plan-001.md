# Plan: Fix close_period 404 — spreadsheet URL vs ID mismatch

**Workflow:** WF-5 (iteration 1)
**FRs:** FR-PAYMENT-001, FR-SPECIALIST-001
**Ceremony:** medium
**Session:** SID-1786476390-9ced6d62

## 1. Root Cause

`close_period` fails with 404 because a full spreadsheet URL (`https://docs.google.com/spreadsheets/d/18WOvPd...`) is passed to `spreadsheets().get(spreadsheetId=...)` instead of the bare ID (`18WOvPd...`).

### Value lifecycle

```
create_timesheet:     bare ID    (specialist_storage.py:44,54)
_apply_updates WRITE: full URL   (specialist_storage.py:224-225) — writes URL to Team sheet cell
_parse_row READ:      bare ID    (specialist_storage.py:168) — extracts ID via extract_id_from_hyperlink_formula
IMPORTRANGE:           full URL   (config_storage.py:63-73) — get_import_timesheet_formula rewraps bare ID
```

IMPORTRANGE is **NOT affected** — `get_import_timesheet_formula()` already handles both bare IDs and URLs, always producing a valid URL for the formula.

### The bug chain

1. `_apply_updates()` (`specialist_storage.py:224-225`) writes full URLs to the Team sheet's Timesheet column
2. `_parse_row()` (`specialist_storage.py:168`) reads them back, relies on `extract_id_from_hyperlink_formula()` which has a fallback `or timesheet_raw` — any extraction failure passes the raw URL through
3. `close_period()` (`project_service.py:267-268`) passes `sp.timesheet` unvalidated to `close_period_in_timesheet()`
4. `close_period_in_timesheet()` (`project_storage.py:462-463`) passes the value directly to the Google Sheets API

**Affected repos:** `feptm-server` only (`feptm-analysis` for workflow artifacts)

## 2. REST API Changes

None. `POST /api/v1/projects/{project_id}/periods/close` behavior unchanged — same request, same response. Fixes the 404 error for sheets that have full URLs in the Timesheet column.

## 3. Implementation Details

### 3.1 Fix 1 (root cause): Write bare IDs in `_apply_updates`

**File:** `src/feptm/storage/specialist_storage.py:224-225`

Remove the URL generation. Write the bare spreadsheet ID as-is:

```python
# Before:
if "spreadsheets/d/" not in ts_id:
    ts_id = f"https://docs.google.com/spreadsheets/d/{ts_id}"

# After:
pass  # remove the URL generation; write ts_id as-is
```

The `_parse_row()` function already handles bare IDs via `extract_id_from_hyperlink_formula()` fallback (last path-segment extraction), so reading bare IDs works correctly.

### 3.2 Fix 2 (defensive): Normalize timesheet_id at API call boundary

**File:** `src/feptm/storage/project_storage.py:461-463`

Extract bare ID from URL-form values before passing to the API, as a safety net for existing data:

```python
# Before:
spreadsheet = (
    self._sheets.sheets_service.spreadsheets()
    .get(spreadsheetId=timesheet_id)
    .execute()
)

# After:
resolved_id = utils.extract_id_from_hyperlink_formula(timesheet_id) or timesheet_id
spreadsheet = (
    self._sheets.sheets_service.spreadsheets()
    .get(spreadsheetId=resolved_id)
    .execute()
)
```

`utils` is already imported (`from feptm.core import utils` at line 6).

### 3.3 Fix 3 (belt-and-suspenders): Normalize in close_period orchestrator

**File:** `src/feptm/timesheets/project_service.py:264-268`

Normalize `sp.timesheet` before passing it down:

```python
# Before:
for sp in specialists:
    if not sp.timesheet:
        continue
    updated = self._projects.close_period_in_timesheet(
        sp.timesheet, period_name, start_date, end_date
    )

# After:
for sp in specialists:
    if not sp.timesheet:
        continue
    ts_id = utils.extract_id_from_hyperlink_formula(sp.timesheet) or sp.timesheet
    updated = self._projects.close_period_in_timesheet(
        ts_id, period_name, start_date, end_date
    )
```

Add import: `from feptm.core import utils` at line 6.

## 4. Storage Changes

No schema or data model changes. The same data flows through the same methods — just with proper ID extraction.

## 5. Security Considerations

No secrets are added, exposed, or modified. The `extract_id_from_hyperlink_formula()` function is read-only string parsing — no external calls or side effects.

## 6. Config Changes

None.

## 7. References

- `FR-PAYMENT-001.yaml` — Close payment periods and archive reports
- `FR-SPECIALIST-001.yaml` — Remove a specialist from future periods through Team
- `specialist_storage.py:204-248` — `_apply_updates()` writes full URLs
- `specialist_storage.py:137-179` — `_parse_row()` reads timesheet values
- `specialist_storage.py:160-168` — timesheet extraction fallback
- `project_storage.py:451-465` — `close_period_in_timesheet()` API call
- `project_service.py:258-269` — `close_period()` orchestrator loop
- `utils.py:136-187` — `extract_id_from_hyperlink_formula()` ID extraction
