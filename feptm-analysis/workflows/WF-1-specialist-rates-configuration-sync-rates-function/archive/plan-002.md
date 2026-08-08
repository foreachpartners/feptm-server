# SDD Fix Plan: update_current_period append-only bug

**Revision:** v3 (FR-SYNC-RATES-001 revision_history)
**Root cause:** `update_current_period` in `project_storage.py:237-239` returns early if a specialist already exists in the Current Period sheet. This method was designed for inserting new specialists during `POST /api/projects/sync`, not for updating existing rows. When `sync_project_rates` calls it, existing specialists are silently skipped.

## Fix

Add a dedicated `sync_rates_to_current_period` method that finds an existing specialist row and overwrites rate columns, without inserting rows or setting formulas.

### File: `src/feptm/storage/project_storage.py`

**1. New private helper `_find_specialist_row`** (after `_specialist_in_sheet`, line 434):

Returns the 1-based sheet row number where the specialist is found, or `None`. Same scan logic as `_specialist_in_sheet` but returns the row instead of a bool.

```python
def _find_specialist_row(
    values, headers, name, sheets,
) -> int | None:
    idx = sheets.find_column_index(headers, [ColumnName.SPECIALIST.value])
    if idx is None:
        return None
    for i, row in enumerate(values[1:], start=2):
        if len(row) > idx and row[idx] == name:
            return i
    return None
```

**2. New public method `sync_rates_to_current_period`** (after `update_current_period`, line 253):

```python
def sync_rates_to_current_period(
    self, spreadsheet_id: str, specialist: Specialist,
) -> None:
    sheet_name = SheetName.CURRENT_PERIOD.value
    sheet_data = self._read_current_period(spreadsheet_id, sheet_name)
    if not sheet_data:
        return
    values, headers, _ = sheet_data
    target_row = _find_specialist_row(values, headers, specialist.name, self._sheets)
    if target_row is None:
        return
    _write_specialist_fields(
        self._sheets, spreadsheet_id, sheet_name, target_row, specialist, headers,
    )
```

No `formula_provider` parameter -- not needed since we're only overwriting values, not inserting rows or setting formulas.

### File: `src/feptm/storage/protocols.py`

Add to `ProjectStorageProtocol`:

```python
def sync_rates_to_current_period(
    self,
    spreadsheet_id: str,
    specialist: Specialist,
) -> None: ...
```

### File: `src/feptm/timesheets/project_service.py`

In `sync_project_rates`, replace `self._projects.update_current_period(...)` calls with `self._projects.sync_rates_to_current_period(...)`, dropping the `self._formulas` argument.

### File: `tests/timesheets/test_project_service.py`

Update mock method names from `update_current_period` to `sync_rates_to_current_period` in:
- `test_sync_project_rates_success`
- `test_sync_project_rates_skips_no_timesheet`

### File: `tests/api/v1/test_projects.py`

No changes — handler contract unchanged.
