# Plan: Exclude empty-timesheet specialists from archived tab

**Workflow:** WF-5 (iteration 2)
**FRs:** FR-PAYMENT-001
**Ceremony:** medium
**Session:** SID-1786479579-e2968998

## 1. Root Cause

`archive_current_period` includes specialists with empty timesheets in the archived tab — they get a row with just the period name and raw Current Period values, but zero computed hours/costs/revenue. These rows are meaningless: the specialist has no timesheet data, so the archive entry adds no useful information.

## 2. Fix

Skip specialists without a timesheet entirely. They do not appear in the archived tab.

### 2.1 Remove archive entries for specialists without timesheets

**File:** `src/feptm/storage/project_storage.py`

Two paths currently archive empty-timesheet specialists:

**Path A — specialist not in `sp_map`** (lines 585-590):
```python
# Before:
sp = sp_map.get(sp_name)
if sp is None:
    row_copy = list(row)
    _pad_row(row_copy, period_idx + 1)
    row_copy[period_idx] = period_name
    archive.append(row_copy)
    continue

# After:
sp = sp_map.get(sp_name)
if sp is None:
    continue     # skip — no timesheet, nothing to compute
```

**Path B — specialist in `sp_map` but timesheet_id empty** (lines 592-598):
```python
# Before:
timesheet_id = sp.timesheet or ""
if not timesheet_id:
    row_copy = list(row)
    _pad_row(row_copy, period_idx + 1)
    row_copy[period_idx] = period_name
    archive.append(row_copy)
    continue

# After:
timesheet_id = sp.timesheet or ""
if not timesheet_id:
    continue     # skip — no timesheet, nothing to compute
```

The `sp_map` construction at lines 564-568 already filters to `if sp.timesheet`, so Path B is unreachable with current code (if timesheet is empty, the specialist is never in `sp_map`). Path B is kept as defensive coding.

## 3. REST API Changes

None. `POST /api/v1/projects/{project_id}/periods/close` behavior unchanged — same response shape. The archived tab simply has fewer rows (empty-timesheet specialists excluded).

## 4. Storage Changes

No schema or data model changes. Same methods, same parameters.

## 5. Security Considerations

None.

## 6. Config Changes

None.

## 7. References

- `FR-PAYMENT-001.yaml` — Close payment periods and archive reports
- `project_storage.py:541-638` — `archive_current_period()` method
- `project_storage.py:564-568` — `sp_map` construction
- `project_storage.py:585-590` — Path A: specialist not in sp_map
- `project_storage.py:592-598` — Path B: timesheet_id empty
- `project_service.py:265-267` — close_period skips empty-timesheet specialists
