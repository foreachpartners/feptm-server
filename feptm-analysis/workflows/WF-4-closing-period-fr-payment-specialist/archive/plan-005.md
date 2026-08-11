# Plan: Fix _sum_timesheet_hours to filter by Payment Period

## Context

When two close operations cover the same date (e.g., "August Week 3" and "August Week 4" both have entries on 01.03.2026), `_sum_timesheet_hours` sums **all** hours in the date range, including entries already marked with a different period. This inflates the hour count in the archived tab.

## Root Cause

`_sum_timesheet_hours` (`project_storage.py:725`) filters by date column only:

```python
for i in range(1, len(values)):
    ...
    if parsed < start_date or parsed > end_date:
        continue
    total += float(row[hours_col] or 0)
```

It does not check the Payment Period column. After `close_period_in_timesheet` writes `period_name` to matching rows, `_sum_timesheet_hours` should only sum rows where Payment Period matches `period_name`.

## Fix

Rename `_sum_timesheet_hours` → `_sum_period_hours` and add `period_name` parameter. Find the Payment Period column and filter rows by it.

### File-Level Changes

#### 1. `feptm-server/src/feptm/storage/project_storage.py`

**Rename method** (line 725):

```python
# BEFORE
def _sum_timesheet_hours(self, timesheet_id, start_date, end_date) -> float:

# AFTER
def _sum_period_hours(self, timesheet_id, start_date, end_date, period_name) -> float:
```

**Add Payment Period column lookup** (after line 761, alongside `date_col` and `hours_col`):

```python
period_col = self._sheets.find_column_index(
    headers, [ColumnName.PAYMENT_PERIOD.value]
)
if period_col is None:
    period_col = _find_column_contains(headers, ColumnName.PAYMENT_PERIOD.value)
```

**Add period filter in the loop** (lines 766-779):

```python
for i in range(1, len(values)):
    row = values[i]
    if len(row) <= max(date_col, hours_col, period_col or 0):
        continue
    parsed = _serial_to_date(row[date_col])
    if parsed is None:
        continue
    if parsed < start_date or parsed > end_date:
        continue
    if period_col is not None:
        period_val = row[period_col] if len(row) > period_col else ""
        if str(period_val).strip() != period_name:
            continue
    try:
        total += float(row[hours_col] or 0)
    except (ValueError, TypeError):
        continue
```

**Update call site** in `archive_current_period` (line 584):

```python
# BEFORE
hours = self._sum_timesheet_hours(timesheet_id, start_date, end_date)

# AFTER
hours = self._sum_period_hours(timesheet_id, start_date, end_date, period_name)
```

---

## Tests

Update existing tests that mock `_sum_timesheet_hours` to use new name `_sum_period_hours`, and verify the `period_name` parameter is passed.

---

## REST API Changes

None.

## Config Changes

None.

## Security Considerations

None.
