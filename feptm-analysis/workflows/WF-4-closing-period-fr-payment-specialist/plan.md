# Plan: AR-DATA-002 compliance — handle deleted specialists in period close

## Context

When a specialist is deleted from the Team sheet before a period is closed:

1. Name collision residual: if two Johns existed, deleting one leaves Current Period with "John (2)" row but `_resolve_display_names` produces `"John"` — lookup misses
2. Deleted specialist: "John (3)" Developer row exists in Current Period but has no matching specialist in Team → zero hours

AR-DATA-002 requires their work to be included in closed periods.

## Changes

**File:** `src/feptm/storage/project_storage.py` — `archive_current_period` method

### Fix A: Strip `(N)` suffix fallback in name lookup

When `sp_map.get(sp_name)` returns `None`, strip trailing `\s+(N)` suffix and retry:

```python
import re
base = re.sub(r"\s+\(\d+\)$", "", sp_name)
sp = sp_map.get(base)
```

### Fix B: Orphan specialist via specialist tab formula

When both exact and stripped lookups fail, the specialist was deleted. Extract timesheet ID from their individual report tab cell A1 formula:

```python
ts_id = self._extract_timesheet_id_from_tab(spreadsheet_id, sp_name)
```

New method `_extract_timesheet_id_from_tab(spreadsheet_id, tab_name)`:
1. Read cell A1 of the specialist's individual tab
2. Parse `=IMPORTRANGE("timesheetId", ...)` to extract timesheet ID
3. Return timesheet ID or None

### Fix C: Read rates from Current Period row (orphan)

Orphan specialists have no `Specialist` object with rates. Read rates directly from the Current Period row cells.

## Tasks

| # | Task | Req | Status |
|---|------|-----|--------|
| T-16 | Storage: Add `(N)` suffix stripping fallback to name lookup in archive_current_period | FR-PAYMENT-001, AR-DATA-002 | pending |
| T-17 | Storage: Add orphan specialist detection + timesheet ID extraction from tab formula | FR-PAYMENT-001, AR-DATA-002 | pending |
| T-18 | Tests: Add tests for suffix stripping and orphan handling | FR-PAYMENT-001, AR-DATA-002 | pending |
| T-19 | Audit: verify | FR-PAYMENT-001 | pending |
