# SDD Technical Plan: FR-SYNC-001, FR-SYNC-RATES-001, AR-DATA-001

## Architecture Overview

**Root cause:** The `Specialist` model has no unique identifier. All downstream storage operations (tab creation, Current Period row insertion, rate sync, timesheet ID write-back) match specialists exclusively by `name` string. When two specialists share the same name in the Team sheet, the second specialist is silently dropped from reports, Current Period sheets, and never gets their timesheet ID written back to the Team sheet.

**Fix strategy:** Carry row identity from the Team sheet through the `Specialist` model. Add a `display_name` field that disambiguates on name collision. Use `row_index` for precise write-back to the Team sheet. Use `display_name` for Google Sheets tab names and Current Period row matching.

### Data Flow (fixed)

```
Team sheet row N: "John Smith", role, rates, timesheet_id
Team sheet row N+1: "John Smith", role, rates, null
              |
              v list_from_sheet
[Specialist(name="John Smith", row_index=N, display_name="John Smith (N)"),
 Specialist(name="John Smith", row_index=N+1, display_name="John Smith (N+1)")]
              |
              v _resolve_display_names (service layer)
Detects collision: both have name "John Smith" → display_name receives "(row_index)" suffix
              |
              v sync loop
  - update_timesheet_ids: targets row N via row_index, not name lookup
  - add_specialist_to_report: creates tab "John Smith (N)" and "John Smith (N+1)"
  - update_current_period: writes "John Smith (N)" and "John Smith (N+1)" rows
  - sync_rates_to_current_period: finds rows by display_name
```

## Files Changed

### 1. `src/feptm/models/specialist.py`

Add two fields:

```python
row_index: int | None = None
display_name: str = ""  # Set after collision detection; defaults to name
```

`display_name` equals `name` for unique names, `"{name} ({row_index})"` on collision. Initially empty; set by `_resolve_display_names` in the service layer after listing.

### 2. `src/feptm/storage/specialist_storage.py`

**`_parse_row`** (line 128): Build the `Specialist` with `row_index` from the enumeration. The loop in `_parse_rows` enumerates `values[1:]` starting from data row 2. Track the actual sheet row: `row_number = i + 2` where `i` is the 0-based index into `values[1:]`.

```python
# In _parse_rows: enumerate(values[1:], start=0) → row_number = start + 2
sp = self._parse_row(row, headers_map, row_number=start_index + 2)
```

Pass `row_number` through to `_parse_row`, which sets `row_index=row_number` on the Specialist.

**`_prepare_updates`** (line 162): Replace `find_specialist_row_index(values, name_col, sp.name)` with direct row indexing using `sp.row_index`. Since `row_index` is the 1-based sheet row number:

```python
if sp.row_index is not None:
    updates.append((sp.row_index, sp.timesheet))
```

The `find_specialist_row_index` call on line 182 becomes:

```python
# Before: find by name
row_idx = self._sheets.find_specialist_row_index(values, name_col, sp.name)

# After: use row_index directly
row_idx = sp.row_index
```

### 3. `src/feptm/storage/project_storage.py`

**`add_specialist_to_report`** (line 203): Replace `tab_name = specialist.name` with `tab_name = specialist.display_name`. If `display_name` is empty (legacy, not set), fall back to `specialist.name`.

```python
tab_name = specialist.display_name or specialist.name
```

**`update_current_period`** (line 224): Use `specialist.display_name or specialist.name` for:
- `_specialist_in_sheet` check (line 237)
- `_write_specialist_fields` call (line 380 via `_insert_and_update_row`)

The `_write_specialist_fields` function at line 576 already writes `specialist.name` at `ColumnName.SPECIALIST`. Change to `specialist.display_name or specialist.name`.

**`sync_rates_to_current_period`** (line 256): Use `specialist.display_name or specialist.name` for `_find_specialist_row` lookup (line 267).

**`_specialist_in_sheet`** (line 444): Signature unchanged (takes `name: str`). Callers pass `specialist.display_name or specialist.name`.

**`_find_specialist_row`** (line 456): Same — callers pass the disambiguated name.

**`_write_specialist_fields`** (line 576): The specialist name written to the sheet must use the disambiguated name:

```python
field_updates = [
    (ColumnName.SPECIALIST.value, specialist.display_name or specialist.name),
    ...
]
```

### 4. `src/feptm/timesheets/project_service.py`

Add helper function `_resolve_display_names`:

```python
def _resolve_display_names(specialists: list[Specialist]) -> None:
    from collections import Counter
    name_counts = Counter(sp.name for sp in specialists if sp.name)
    for sp in specialists:
        if name_counts[sp.name] > 1 and sp.row_index is not None:
            sp.display_name = f"{sp.name} ({sp.row_index})"
        else:
            sp.display_name = sp.name
```

Call this in both `sync_project_specialists` (line 66, after `list_from_sheet`) and `sync_project_rates` (line 111 and 126, after both `list_from_sheet` calls).

### 5. `src/feptm/services/google_sheets_service.py`

`find_specialist_row_index` (line 621) remains for backward compatibility but is no longer used by `_prepare_updates`. Annotate the remaining call site or the method itself with `# AR-DATA-001:allow`.

### 6. `src/feptm/api/v1/projects.py`

Add `FR-SYNC-001` to the `@req` annotation on `sync_project_specialists` (already present). No contract changes — both endpoints retain same signatures and response models.

## No Changes

- **`protocols.py`** — No signature changes. All storage methods receive `Specialist` objects that now carry `row_index` and `display_name`.
- **`models/project.py`, `models/context.py`** — Unchanged.
- **`storage/config_storage.py`** — Unchanged.
- **`timesheets/config_service.py`** — Unchanged.
- **`timesheets/specialist_service.py`** — Unchanged.
- **`core/config.py`, `core/utils.py`** — Unchanged.
- **REST API schemas** — Unchanged. `row_index` and `display_name` are internal fields, not exposed in request/response schemas (they are not part of the JSON body).

## Test Coverage

### Unit tests (`tests/timesheets/test_project_service.py`)

- `test_sync_resolves_display_names_on_collision` — Two specialists with same name, verify display_name differs
- `test_sync_no_collision_preserves_name` — Unique names, verify display_name equals name
- `test_sync_duplicate_names_writes_ids_to_correct_rows` — Verifies `update_timesheet_ids` targets correct rows
- `test_sync_duplicate_names_creates_disambiguated_tabs` — Verifies tab creation uses display_name

### Unit tests (`tests/storage/test_specialist_storage.py`)

- `test_parse_rows_sets_row_index` — Verify row_index populated
- `test_prepare_updates_uses_row_index` — Verify row targeting uses row_index, not find_specialist_row_index

### Existing tests impacted

- Tests mocking `find_specialist_row_index` may need updating if `_prepare_updates` no longer calls it.
- Any test passing `Specialist` objects without `row_index` should still work (backward compatible — `row_index` defaults to `None`).
- Existing sync tests should continue passing (non-collision case unchanged).

## Security

No config changes. No new environment variables. No secrets introduced.

## @req Annotations

Handlers already annotated. No new annotations required:

- `sync_project_specialists`: `# @req FR-SYNC-001, FR-SPECIALIST-001`
- `sync_project_rates`: `# @req FR-SYNC-RATES-001, FR-SYNC-001`

## Config Changes

None. No `FEPTM_FEPTM_SERVER__` prefix changes.
