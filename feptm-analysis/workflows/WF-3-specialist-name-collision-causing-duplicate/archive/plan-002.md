# Plan: Remove Double Names Handling — Log Error & Abort Sync

## Architecture Overview

### Current State (WF-3, plan-001)

The Specialist model carries two identity fields beyond `name`:

- `row_index: int | None` — 1-based row in the Team sheet, populated during `list_from_sheet`
- `display_name: str` — `"{name} ({row_index})"` on collision, `name` on no collision

`_resolve_display_names()` in `project_service.py:18-24` uses `collections.Counter` to detect duplicate names and sets `display_name` with a row-index suffix. This disambiguated name is then used as:

- Tab name in report/calculation spreadsheets (`add_specialist_to_report` at `project_storage.py:209`)
- Lookup key in Current Period rows (`_specialist_in_sheet` at `project_storage.py:237`, `_find_specialist_row` at `project_storage.py:267`)
- Key in the specialist map during period archive (`archive_current_period` at `project_storage.py:562`)
- Value written into Current Period sheet cells (`_write_specialist_fields` at `project_storage.py:1073`)

The archive also carries residual handling: `(N)` suffix stripping fallback (`project_storage.py:578-581`) and `seen_bases` dedup (`project_storage.py:587-589`).

### Target State

On name collision detection during sync, the server writes an `ERROR`-level log listing **all** duplicate names with their row indices, then **aborts the entire operation**. No specialists are processed, no timesheets are created, no report tabs are added, no Current Period rows are updated. The operation returns an empty/safe result.

No disambiguation, no renaming, no `display_name` field.

`row_index` is preserved — it remains the authoritative way to target a specific Team sheet row for write-back (`update_timesheet_ids`).

### Data Flow

```
Team sheet rows → list_from_sheet → [Specialist(row_index=N)] → _has_duplicate_names?
                                                                    ↓ YES
                                          log.error("Duplicate names found: John (rows 2,5), Sam (rows 3,7). Aborting sync.")
                                                                    ↓
                                                                  abort (return empty/false)
                                                                    ↓ NO
                                              specialists → sync_project_specialists / sync_project_rates / close_period
                                                                    ↓
                                                     All storage ops use specialist.name directly
```

---

## File-Level Changes

### 1. `feptm-server/src/feptm/models/specialist.py`

Remove `display_name` field (line 20). `row_index` stays.

```python
# BEFORE
row_index: int | None = None
display_name: str = ""

# AFTER
row_index: int | None = None
```

### 2. `feptm-server/src/feptm/timesheets/project_service.py`

**Remove:**
- `from collections import Counter` import (line 3)
- `_resolve_display_names()` function (lines 18-24)

**Add new function:**

```python
def _has_duplicate_names(specialists: list[Specialist]) -> bool:
    name_rows: dict[str, list[int]] = {}
    for sp in specialists:
        if not sp.name:
            continue
        ri = sp.row_index or 0
        if sp.name not in name_rows:
            name_rows[sp.name] = []
        name_rows[sp.name].append(ri)
    
    dups = {n: rows for n, rows in name_rows.items() if len(rows) > 1}
    if dups:
        dup_detail = ", ".join(
            f"'{name}' (rows: {', '.join(str(r) for r in rows)})"
            for name, rows in dups.items()
        )
        log.error(
            "Duplicate specialist names found in Team sheet: %s. "
            "Aborting sync — rename the duplicates in the Team sheet to resolve.",
            dup_detail,
        )
        return True
    return False
```

**Replace call sites:**

| Line | Current | New |
|------|---------|-----|
| 84 | `_resolve_display_names(specialists)` | `if _has_duplicate_names(specialists): return [], 0, 0` |
| 145 | `_resolve_display_names(specialists)` | `if _has_duplicate_names(specialists): return [], 0` |
| 193 | `_resolve_display_names(specialists)` | `if _has_duplicate_names(specialists): return ClosePeriodResponse(...)` |

**`close_period` abort return value:**

```python
return ClosePeriodResponse(
    created=datetime.now(UTC),
    project_id=project_id,
    period_name=period_name,
    entries_updated=0,
    specialists_processed=0,
    report_archived=False,
    calculations_archived=False,
)
```

### 3. `feptm-server/src/feptm/storage/project_storage.py`

Replace every `specialist.display_name or specialist.name` with `specialist.name`:

| Line(s) | Current | New |
|---------|---------|-----|
| 209 | `specialist.display_name or specialist.name` | `specialist.name` |
| 237 | `specialist.display_name or specialist.name` | `specialist.name` |
| 238 | `specialist.display_name or specialist.name` | `specialist.name` |
| 267 | `specialist.display_name or specialist.name` | `specialist.name` |
| 1073 | `specialist.display_name or specialist.name` | `specialist.name` |

**`archive_current_period` method (lines 538-644):**

| Change | Detail |
|--------|--------|
| Line 561-565 | `sp_map` builds with `sp.name` instead of `sp.display_name or sp.name` |
| Line 571 | Remove `import re` |
| Lines 578-581 | Remove the `(N)` suffix stripping fallback block |
| Lines 587-589 | Remove `seen_bases` dedup + `base_name` extraction |
| Lines 592-595 | Remove `canonical` name rewrite |
| Line 607 | Remove `seen_bases.add(base_name)` |

New `archive_current_period` specialist map lookup section:

```python
sp_map = {sp.name: sp for sp in specialists if sp.timesheet}

archive = [list(headers)]
num_cols = len(headers)

for row in values[1:]:
    _pad_row(row, num_cols)
    sp_name = row[0] if row else ""

    sp = sp_map.get(sp_name)
    if sp is None:
        archive.append(list(row))
        continue

    timesheet_id = sp.timesheet or ""
    if not timesheet_id:
        archive.append(list(row))
        continue

    hours = self._sum_timesheet_hours(timesheet_id, start_date, end_date)
    if hours <= 0:
        archive.append(list(row))
        continue

    # ... rates, costs, revenue calculation unchanged ...
```

### 4. `feptm-analysis/ar-specs/200-data/AR-DATA-001.yaml`

Rewrite requirements and prohibitions to match log-and-abort behavior:

```yaml
requirements:
  - "When two or more specialists share the same name in the Team sheet, the server MUST log an ERROR-level message and abort the sync operation — no specialists are processed."
  - "The Specialist model MUST carry a row_index: int field populated from the source Team sheet row during list_from_sheet."
  - "All storage operations that write data to a specific Team sheet row (update_timesheet_ids) MUST target the row by row_index, not by name-based lookup."

prohibitions:
  - "Silently dropping or overwriting a specialist when a name collision is detected."
  - "Disambiguating specialist names with row-based suffixes in tab names, Current Period rows, or archived period sheets."
  - "Storage operations matching specialists by raw name string alone for write-back into the Team sheet."
```

Remove checks that reference `display_name` or disambiguation.

### 5. Tests

#### `feptm-server/tests/timesheets/test_project_service.py`

| Existing test | Action |
|---------------|--------|
| `test_sync_resolves_display_names_on_collision` (L365-399) | Replace with `test_sync_aborts_on_duplicate_names` |
| `test_sync_no_collision_preserves_name` (L401-432) | Update: verify sync proceeds normally with unique names, no `display_name` assertions |
| `test_sync_duplicate_names_passes_display_name_to_storage` (L434-466) | Replace with `test_sync_rates_aborts_on_duplicate_names` |

New test `test_sync_aborts_on_duplicate_names`:
- Two "John Smith" specialists → `sync_project_specialists` returns `([], 0, 0)`
- Verify `project_service._projects.add_specialist_to_report` is NOT called
- Verify `project_service._projects.update_current_period` is NOT called
- Verify `log.error` was called with duplicate name info

New test `test_sync_rates_aborts_on_duplicate_names`:
- Two "Sam" specialists → `sync_project_rates` returns `([], 0)`
- Verify no storage methods called
- Verify `log.error` was called

#### `feptm-server/tests/timesheets/test_specialist_service.py`

| Existing test | Action |
|---------------|--------|
| `test_prepare_updates_duplicate_names_correct_rows` (L197-215) | Keep — `row_index` write-back unaffected |

---

## REST API Changes

None. The API contract (endpoints, request/response shapes, status codes) remains unchanged. When a duplicate is detected, sync endpoints return empty results (`[], 0, 0` / `[], 0`) and `close_period` returns a response with zero entries. The error is logged server-side for operator investigation.

---

## Config Changes

None.

---

## Security Considerations

None. Error log contains specialist names and row indices, which are not secrets.
