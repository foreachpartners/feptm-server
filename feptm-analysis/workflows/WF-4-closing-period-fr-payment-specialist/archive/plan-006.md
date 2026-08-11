# Plan: Fix $0.00 Total Cost and #DIV/0! in archived tabs

## Context

Archived period tabs show two problems:

1. **Total Cost $0.00** — `archive_current_period` writes Hours, Client Hourly Rate, Specialist Hourly Rate, Client Work Cost, Specialist Work Cost, and Revenue — but never writes `TOTAL_COST_USD`. The cell keeps its original template formula result ($0.00).

2. **#DIV/0! on summary row** — The Current Period has a Total/summary row (empty specialist name, formulas like `=СУММ(D2)`). When copied into the archive, these formulas reference wrong cells and fail if a divisor is zero.

## Fix A: Write Total Cost

Add `(ColumnName.TOTAL_COST_USD.value, str(cl_cost))` to the computed value writes in the archive row builder.

## Fix B: Skip total/summary rows

At the top of the loop in `archive_current_period`, call `_is_total_row` to skip summary rows:

```python
if _is_total_row(row, headers, 0, self._sheets):
    continue
```

The specialist column index is 0 (first column) since that's the name column in Current Period.

## File-Level Changes

### `feptm-server/src/feptm/storage/project_storage.py`

In `archive_current_period`, two edits:

**1. Skip summary rows** — at line 571, after `sp_name = row[0]...`:

```python
sp_name = row[0] if row else ""

if _is_total_row(row, headers, 0, self._sheets):
    continue
```

**2. Write Total Cost** — in the value assignment loop (around line 608):

```python
for col_name, val in [
    (ColumnName.HOURS_WORKED.value, str(hours)),
    (ColumnName.CLIENT_HOURLY_RATE_USD.value, str(cl_rate)),
    (ColumnName.SPECIALIST_HOURLY_RATE_USD.value, str(sp_rate)),
    (ColumnName.CLIENT_WORK_COST_USD.value, str(cl_cost)),
    (ColumnName.SPECIALIST_WORK_COST_USD.value, str(sp_cost)),
    (ColumnName.REVENUE_USD.value, str(revenue)),
    (ColumnName.TOTAL_COST_USD.value, str(cl_cost)),
]:
```

---

## Tests

Update `test_archive_current_period_writes_period_column` to verify:
- Total Cost column is populated
- Total/summary rows are excluded from archive

---

## REST API Changes

None.

## Config Changes

None.

## Security Considerations

None.
