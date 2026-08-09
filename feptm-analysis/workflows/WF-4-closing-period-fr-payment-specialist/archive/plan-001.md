# Technical Plan: Close Payment Period (FR-PAYMENT-001)

## Architecture Overview

### Affected Repos
- **feptm-server** (service) — all code changes: models, API, service, storage, config enums
- **feptm-analysis** (analysis) — no code changes (FR spec already exists)

### Data Flow

```
PUT /api/periods  →  periods.py (handler)
  →  TimesheetProjectService.close_period()
    →  ProjectStorage.get_project_metadata()        # resolve spreadsheets
    →  SpecialistStorage.list_from_sheet()           # get specialists + timesheets
    →  For each specialist with timesheet:
        →  ProjectStorage.close_period_in_timesheet() # write period_name to col E
    →  If entries updated:
        →  ProjectStorage.archive_current_period()    # copy sheet with values
        →  ProjectStorage.protect_archived_sheet()    # add protection ranges
    →  Return ClosePeriodResponse
```

### Key Design Decisions

1. **Period close is a single atomic operation** — all timesheets updated first, then archives created. If timesheet updates produce no matches, archives are skipped entirely.
2. **Idempotent** — archived tabs are only created if they don't already exist. Timesheet entries only updated if Payment Period is empty.
3. **Formulas → values** — read "Current period" with `FORMATTED_VALUE` render mode (computes values), write to new tab with `RAW` input option (no formula interpretation).
4. **Protection** — add protected ranges covering the entire archived tab except the Payment Status column (column F) using Google Sheets API `AddProtectedRangeRequest`.

---

## New Files

### 1. `src/feptm/models/payment_period.py`

Pydantic models:

| Class | Fields |
|-------|--------|
| `ClosePeriodRequest` | `project_id: str` (min_length=1), `period_name: str` (min_length=1), `start_date: datetime`, `end_date: datetime` |
| `ClosePeriodResponse` | `created: datetime`, `project_id: str`, `period_name: str`, `entries_updated: int`, `specialists_processed: int`, `report_archived: bool`, `calculations_archived: bool` |

### 2. `src/feptm/api/v1/periods.py`

```
PUT /api/periods → close_payment_period(ClosePeriodRequest) → ClosePeriodResponse
```

- `# @req FR-PAYMENT-001` on handler
- Validates request via Pydantic
- Calls `TimesheetProjectService.close_period()`
- Wraps exceptions as `HTTPException(500)`

### 3. `tests/api/v1/test_periods.py`

Test cases:
- **PUT /api/periods success** — valid request returns 200 with entries_updated > 0
- **PUT /api/periods no entries** — date range matches nothing, returns entries_updated=0 and archived=false
- **PUT /api/periods empty period_name** — returns 422 validation error
- **PUT /api/periods missing fields** — returns 422 validation error
- **PUT /api/periods service error** — returns 500

### 4. `tests/models/test_payment_period.py`

- Validate `ClosePeriodRequest` accepts valid data
- Validate `ClosePeriodRequest` rejects empty `project_id`
- Validate `ClosePeriodRequest` rejects empty `period_name`
- Validate `ClosePeriodResponse` serialization

---

## Modified Files

### 5. `src/feptm/models/__init__.py`

Add exports:
```python
from feptm.models.payment_period import ClosePeriodRequest, ClosePeriodResponse
# Append to __all__
```

### 6. `src/feptm/api/router.py`

Register periods router:
```python
from feptm.api.v1 import periods
router.include_router(periods.router, prefix="/periods", tags=["periods"])
```

### 7. `src/feptm/timesheets/config_service.py`

Add `ColumnName` enums for timesheet columns:
```python
PAYMENT_PERIOD = "Payment Period"
PAYMENT_STATUS = "Payment Status"
TASK_NAME = "Task Name"
WORK_HOURS = "Work Hours"
```

Add `RangeFormat` for timesheet data:
```python
TIMESHEET_DATA = "{sheet_name}!A1:F100"
```

### 8. `src/feptm/storage/protocols.py`

Add to `ProjectStorageProtocol`:
```python
def close_period_in_timesheet(
    self, timesheet_id: str, period_name: str, start_date: datetime, end_date: datetime,
) -> int: ...

def archive_current_period(
    self, spreadsheet_id: str, period_name: str,
) -> bool: ...

def protect_archived_sheet(
    self, spreadsheet_id: str, sheet_name: str, payment_status_col_idx: int,
) -> None: ...
```

### 9. `src/feptm/storage/project_storage.py`

Implement three new methods:

**`close_period_in_timesheet(timesheet_id, period_name, start_date, end_date) -> int`**
1. Read timesheet data from sheet "timesheet" (or default first sheet), columns A-F, rows 1-100
2. Iterate rows; for each row where:
   - Column A (Date) is non-empty and between start_date..end_date (inclusive)
   - Column E (Payment Period) is empty
3. Write `period_name` to Column E for matching rows
4. Return count of updated entries

**`archive_current_period(spreadsheet_id, period_name) -> bool`**
1. Check if sheet named `period_name` already exists → return False
2. Read "Current period" sheet data with `valueRenderOption: FORMATTED_VALUE`
3. Create new sheet named `period_name`
4. Write data to new sheet with `valueInputOption: RAW`
5. Return True

**`protect_archived_sheet(spreadsheet_id, sheet_name, payment_status_col_idx) -> None`**
1. Get sheetId for `sheet_name`
2. Add ProtectedRange covering entire sheet (startRowIndex=0, startColumnIndex=0, no end bounds)
3. For the Payment Status column, add editors == [] (only document owner)
4. Set `warningOnly: False`

### 10. `src/feptm/timesheets/project_service.py`

Add `close_period(project_id, period_name, start_date, end_date) -> ClosePeriodResponse`:

```python
def close_period(self, project_id, period_name, start_date, end_date):
    project = self._projects.get_project_metadata(project_id)
    specialists, _ = self._specialists.list_from_sheet(project_id)
    
    total_entries = 0
    specialists_processed = 0
    report_archived = False
    calculations_archived = False
    
    for sp in specialists:
        if not sp.timesheet:
            continue
        updated = self._projects.close_period_in_timesheet(
            sp.timesheet, period_name, start_date, end_date
        )
        specialists_processed += 1
        total_entries += updated
    
    if total_entries > 0:
        if project.report_spreadsheet_id:
            report_archived = self._projects.archive_current_period(
                project.report_spreadsheet_id, period_name
            )
            if report_archived:
                self._projects.protect_archived_sheet(
                    project.report_spreadsheet_id, period_name, payment_status_col_idx=5
                )
        if project.calculations_spreadsheet_id:
            calculations_archived = self._projects.archive_current_period(
                project.calculations_spreadsheet_id, period_name
            )
            if calculations_archived:
                self._projects.protect_archived_sheet(
                    project.calculations_spreadsheet_id, period_name, payment_status_col_idx=5
                )
    
    return ClosePeriodResponse(
        created=datetime.now(UTC),
        project_id=project_id,
        period_name=period_name,
        entries_updated=total_entries,
        specialists_processed=specialists_processed,
        report_archived=report_archived,
        calculations_archived=calculations_archived,
    )
```

### 11. `src/feptm/dependencies.py`

No changes needed — `close_period` is a method on existing `TimesheetProjectService`, obtained via `get_timesheet_project_service()`.

### 12. `tests/timesheets/test_project_service.py`

Add test cases for `close_period`:
- Close period with matching entries — returns entries > 0
- Close period with no matching entries — returns entries == 0, archives skipped
- Close period handles missing timesheets gracefully
- Close period when report/calculations spreadsheet IDs are None

---

## Acceptance Criteria Mapping

| # | Criterion | Implementation |
|---|-----------|---------------|
| 1 | Accept project_id, period_name, start_date, end_date | `ClosePeriodRequest` Pydantic model |
| 2 | Include only entries with empty Payment Period and Date in range | `close_period_in_timesheet()` date + empty column check |
| 3 | Write period_name to Payment Period column | `close_period_in_timesheet()` writes to col E |
| 4 | No matching entries → no archives/modifications | Service skips archive if `total_entries == 0` |
| 5 | Create copies of Current period named period_name | `archive_current_period()` — values-only copy |
| 6 | Archived tabs contain recalculated values, not formulas | Read with FORMATTED_VALUE, write with RAW |
| 7 | Changes to source hours/rates after closure don't change archived values | Values are hard-coded, no formula links |
| 8 | Protected ranges except payment status cells | `protect_archived_sheet()` — full sheet protection minus col F |
| 9 | Current period unchanged; idempotent on re-run | Empty Payment Period check prevents re-update; duplicate sheet check prevents re-create |

## Security Considerations

- No new secrets or credentials introduced
- Protected ranges set `editors: []` — only document owner can edit
- All operations use existing Google Sheets OAuth 2.0 credentials

## Config Changes

No new environment variables. Existing `FEPTM_FEPTM_SERVER__` prefixed settings are sufficient — timesheet template structure already has Payment Period (E) and Payment Status (F) columns.
