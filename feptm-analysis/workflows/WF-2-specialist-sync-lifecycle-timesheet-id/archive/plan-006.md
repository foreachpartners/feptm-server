# Plan: Remove stale specialists from Current Period after closing

## Context

FR-SPECIALIST-001 criteria 5 and 6:

> 5. "After the open period is closed successfully, the next Current period is formed from the current Team."
> 6. "A specialist absent from Team is not included in the next or subsequent Current periods."

These criteria are **not satisfied**. The method `remove_stale_specialists` exists in `project_storage.py:643` and is declared in `ProjectStorageProtocol:87`, but it is **never called** in any production flow.

When `close_period` runs, it archives Current Period data into a new tab but leaves the live Current Period sheet untouched. Rows for specialists who were deleted from the Team sheet accumulate and remain visible in Current Period indefinitely.

### Why This Is Safe

The stale specialist's data is **preserved** in the archived tab (created before cleanup). Only the live Current Period gets pruned. The order is:

```
archive_current_period → protect_archived_sheet → remove_stale_specialists
```

## Architecture Overview

### Data Flow

```
close_period(project_id, period_name, start_date, end_date)
    │
    ├── list_from_sheet(project_id) → specialists (current Team)
    │
    ├── close_period_in_timesheet(sp.timesheet, ...)  — mark entries
    │
    ├── archive_current_period(spreadsheet_id, period_name, specialists, ...)
    │       ↓ creates snapshot tab, preserves ALL Current Period rows
    │
    ├── protect_archived_sheet(spreadsheet_id, period_name, ...)
    │       ↓ locks archived tab (except payment status column)
    │
    └── remove_stale_specialists(spreadsheet_id, active_names)   ← NEW
            ↓ removes rows for specialists NOT in Team from live Current Period
```

### Why No Additional Info Is Needed

`close_period` already reads the Team sheet at the start. The `specialists` list contains all current Team members. Constructing `active_names = {sp.name for sp in specialists}` and passing it to `remove_stale_specialists` is sufficient — no additional data sources are needed.

---

## File-Level Changes

### 1. `feptm-server/src/feptm/timesheets/project_service.py`

In `close_period`, after the archive + protect block (after line 264), add cleanup calls:

```python
# After:
#     if calculations_archived:
#         self._projects.protect_archived_sheet(
#             project.calculations_spreadsheet_id,
#             period_name,
#             payment_status_col_idx=5,
#         )

# Add:
active_names = {sp.name for sp in specialists}
if project.report_spreadsheet_id:
    removed = self._projects.remove_stale_specialists(
        project.report_spreadsheet_id, active_names
    )
    log.info("Removed %d stale specialists from report Current Period", removed)
if project.calculations_spreadsheet_id:
    removed = self._projects.remove_stale_specialists(
        project.calculations_spreadsheet_id, active_names
    )
    log.info("Removed %d stale specialists from calculations Current Period", removed)
```

### 2. `feptm-server/src/feptm/storage/project_storage.py`

No changes. `remove_stale_specialists` (lines 643-691) is already fully implemented.

### 3. `feptm-server/src/feptm/storage/protocols.py`

No changes. The method is already declared on line 87.

---

## Tests

Add test `test_close_period_removes_stale_specialists` in `test_project_service.py`:

- Set up `close_period` with specialists list containing "John" but Current Period having both "John" and "Jane" (deleted)
- Mock `archive_current_period` to return True
- Verify `remove_stale_specialists` is called with `active_names = {"John"}`
- Verify stale specialist "Jane" would be targeted for removal

---

## REST API Changes

None.

## Config Changes

None.

## Security Considerations

None.
