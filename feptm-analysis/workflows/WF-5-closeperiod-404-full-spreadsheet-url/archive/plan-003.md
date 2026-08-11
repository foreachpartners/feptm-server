# Plan: Enforce strict DD.MM.YYYY date format in close_period

**Workflow:** WF-5 (iteration 3)
**FRs:** FR-PAYMENT-001
**Ceremony:** medium
**Session:** SID-1786482157-fd6d4903

## 1. Root Cause

`_serial_to_date` accepts 7 date formats: numeric serials, `%d.%m.%Y`, `%Y-%m-%d`, `%m/%d/%Y`, `%d/%m/%Y`, `%b %d, %Y`, and Russian locale dates. Ambiguous formats (e.g., `03.04.2026` — March or April?) cause silent misclassification of work entries. Invalid dates are silently skipped rather than failing loudly.

## 2. Fix

### 2.1 Strip `_serial_to_date` to `%d.%m.%Y` only

**File:** `src/feptm/storage/project_storage.py:913-928`

Remove all fallback formats, numeric serial support, and Russian date parsing:

```python
def _serial_to_date(value: Any) -> datetime | None:
    if isinstance(value, str) and value.strip():
        try:
            return datetime.strptime(value.strip(), "%d.%m.%Y").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass
    return None
```

### 2.2 Abort `close_period_in_timesheet` on invalid date

**File:** `src/feptm/storage/project_storage.py:513-515`

Replace silent `continue` with error log + raise:

```python
# Before:
parsed = _serial_to_date(date_val)
if parsed is None:
    continue

# After:
parsed = _serial_to_date(date_val)
if parsed is None:
    log.error(
        "Invalid date format in timesheet %s row %d: %s (expected DD.MM.YYYY)",
        timesheet_id, i + 1, date_val,
    )
    raise Exception(
        f"Invalid date format in timesheet {timesheet_id} row {i+1}: {date_val!r} (expected DD.MM.YYYY)"
    )
```

The exception propagates through `close_period` orchestrator → API handler's `except Exception` → 500 Internal Server Error. Malformed date = abort.

### 2.3 Error on invalid date in `_sum_period_hours`

**File:** `src/feptm/storage/project_storage.py:796-798`

Log error and raise (identical behavior to `close_period_in_timesheet` — no silent skips anywhere):

```python
# Before:
parsed = _serial_to_date(row[date_col])
if parsed is None:
    continue

# After:
parsed = _serial_to_date(row[date_col])
if parsed is None:
    log.error(
        "Invalid date format in timesheet %s row %d: %s (expected DD.MM.YYYY)",
        timesheet_id, i + 1, row[date_col],
    )
    raise Exception(
        f"Invalid date format in timesheet {timesheet_id} row {i+1}: {row[date_col]!r} (expected DD.MM.YYYY)"
    )
```

### 2.4 Remove dead code

**File:** `src/feptm/storage/project_storage.py`

Remove unused helpers (only referenced by `_serial_to_date`, no other callers):

- `_GSHEETS_EPOCH` (line 868)
- `_RUSSIAN_MONTHS` dict (lines 870-912)
- `_parse_russian_date` function (lines 931-955)
- `import re` from `_parse_russian_date` if no other usage

## 3. REST API Changes

`POST /api/v1/projects/{project_id}/periods/close` — on invalid date in any specialist's timesheet, returns 500 with detail message. Previously returned 200 OK silently skipping entries.

## 4. Storage Changes

No schema or data model changes.

## 5. Security Considerations

None.

## 6. Config Changes

None.

## 7. References

- `FR-PAYMENT-001.yaml` — Close payment periods and archive reports
- `project_storage.py:913-928` — `_serial_to_date` (current, 7-format)
- `project_storage.py:507-520` — `close_period_in_timesheet` date filter loop
- `project_storage.py:791-809` — `_sum_period_hours` date filter loop
- `project_storage.py:868` — `_GSHEETS_EPOCH` (remove)
- `project_storage.py:870-912` — `_RUSSIAN_MONTHS` (remove)
- `project_storage.py:931-955` — `_parse_russian_date` (remove)
