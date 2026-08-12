# WF-6: Fix close_period for deleted specialists

## Affected FRs

- **FR-SPECIALIST-001** (Remove a specialist from future periods through Team)
  - Criterion: "All eligible work of the removed specialist is included when the open period is closed."
  - Criterion: "The removed specialist remains included in archived reports for periods in which the specialist participated."
- **FR-PAYMENT-001** (Close payment periods and archive reports)
  - Criterion: "In each specialist's personal timesheet, the system writes period_name to the Payment Period column of every included entry."

## Bug Summary

When a specialist is deleted from the Team sheet before `close_period()` runs:

1. **Timesheet entries not marked**: `close_period()` reads specialists from Team only. The deleted specialist is absent from the list, so `close_period_in_timesheet()` is never called for their timesheet. Their Payment Period column remains empty.
2. **Excluded from archive**: `archive_current_period()` receives only active Team specialists. The deleted specialist is skipped (`sp_map.get(name)` returns `None`), so they do not appear in the archived period tab.
3. **Formatted values in archived sheets**: `_read_current_period()` uses default `valueRenderOption=FORMATTED_VALUE`, which returns locale-formatted strings (e.g. `$4,00`). These strings may persist in the archive for columns not overwritten by computed values.

## Architecture Overview

### Affected Repos

- `feptm-server` — all changes

### Data Flow (after fix)

```
close_period()
├── list_from_sheet(Team) → active specialists
├── close_period_in_timesheet() for active specialists
├── get_stale_specialists(report, active_names) → stale Specialist objects
│   ├── _read_current_period() → Current Period rows
│   ├── Filter: names not in active_names
│   ├── Parse rates from Current Period row
│   └── _extract_timesheet_id_from_tab() → timesheet ID from IMPORTRANGE
├── close_period_in_timesheet() for stale specialists
├── archive_current_period(all_specialists = active + stale)
├── protect_archived_sheet()
└── remove_stale_specialists()
```

### Existing Methods Reused

- `_extract_timesheet_id_from_tab()` (`project_storage.py:714`) — reads `IMPORTRANGE` formula from a specialist's named tab, extracts timesheet URL
- `_parse_rate_from_row()` (`project_storage.py:896`) — parses numeric rates from sheet rows, stripping currency symbols
- `remove_stale_specialists()` (`project_storage.py:664`) — deletes stale rows from Current Period (unchanged, called after archiving)

## REST API / OpenAPI Changes

None. The `PUT /api/periods` endpoint (`close_payment_period`) unchanged. Response model `ClosePeriodResponse` unchanged.

## Storage Changes

### `feptm-server/src/feptm/storage/project_storage.py`

#### 1. Fix `_read_current_period()` — `valueRenderOption`

**File**: `project_storage.py:302-322`

Add `valueRenderOption="UNFORMATTED_VALUE"` to the `spreadsheets().values().get()` call. This ensures raw numbers are returned (e.g. `4.0`) instead of locale-formatted strings (`$4,00`).

All callers verified safe:
- `update_current_period()` — only uses row indices and name matching, not value parsing
- `archive_current_period()` — overwrites monetary columns with computed Python floats anyway, but this prevents formatted strings from entering via `new_row = list(row)` for non-overwritten fields
- `remove_stale_specialists()` — only reads Specialist name column

#### 2. New method: `get_stale_specialists()`

**Location**: `project_storage.py`, new public method on `ProjectStorage`

**Signature**:
```python
def get_stale_specialists(
    self, spreadsheet_id: str, active_names: set[str]
) -> list[Specialist]
```

**Logic**:
1. Call `_read_current_period(spreadsheet_id, SheetName.CURRENT_PERIOD.value)`
2. For each data row where `name` column is non-empty and NOT in `active_names`:
   - Parse `external_rate` from `Client Hourly Rate (USD)` column via `_parse_rate_from_row()`
   - Parse `internal_rate` from `Specialist Hourly Rate (USD)` column via `_parse_rate_from_row()`
   - Read `role` from `Specialist Role` column
   - Call `_extract_timesheet_id_from_tab(spreadsheet_id, tab_name=name)` to get timesheet ID
3. Return `list[Specialist]` reconstructed from parsed data

**Error handling**:
- `_parse_rate_from_row()` returns `None` on parse failure → default to `Decimal(0)`
- `_extract_timesheet_id_from_tab()` returns `None` on failure → `timesheet=None`, specialist skipped in timesheet update loop
- Empty name or total row → skip

### `feptm-server/src/feptm/storage/protocols.py`

Add `get_stale_specialists()` to `ProjectStorageProtocol`:

```python
def get_stale_specialists(
    self, spreadsheet_id: str, active_names: set[str]
) -> list[Specialist]:
    """Find specialists in Current Period not in active_names, with rates and timesheet IDs."""
    ...
```

## Service Layer Changes

### `feptm-server/src/feptm/timesheets/project_service.py`

#### Modify `close_period()` (lines 228-331)

**Current flow** (simplified):
```
specialists = list_from_sheet(Team)
for sp in specialists: close_period_in_timesheet()
archive_current_period(specialists)
remove_stale_specialists()
```

**New flow**:
```
specialists = list_from_sheet(Team)

# Phase 1: Active specialists
for sp in specialists: close_period_in_timesheet()

# Phase 2: Discover stale specialists from Current Period
active_names = {sp.name for sp in specialists}
stale = get_stale_specialists(report_spreadsheet_id, active_names)

# Phase 3: Stale specialists' timesheets
for sp in stale: close_period_in_timesheet()

# Phase 4: Archive with ALL specialists
all_specialists = specialists + stale
archive_current_period(all_specialists)

# Phase 5: Cleanup
protect_archived_sheet()
remove_stale_specialists()
```

**Key details**:
- `get_stale_specialists()` called only once (from report spreadsheet), not duplicated for calculations
- Same `stale_specialists` list used for both report and calculations archives
- `total_entries` accumulates from both active and stale specialist phases
- `specialists_processed` counts both active and stale
- `remove_stale_specialists()` called for BOTH report and calculations spreadsheets (unchanged behavior)

## Security Considerations

None. No new secrets, credentials, or auth changes.

## Config Changes

None.
