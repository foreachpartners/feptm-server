# Plan: Append computed summary row to archived tab

## Context

Round 7 skipped the total/summary row via `_is_total_row` to avoid `#DIV/0!` from broken template formulas like `=F6/D6`. But the user needs a summary with real totals.

## Fix

Instead of only skipping the broken template row, append a computed summary row at the end of the archive.

### File-Level Changes

#### `feptm-server/src/feptm/storage/project_storage.py` — `archive_current_period`

In the `if hours > 0` branch, collect computed values. After the loop, append a summary row.

**In the hours>0 branch** (after `archive.append(new_row)`), track data:

```python
archive_data.append((hours, cl_cost, revenue))
```

**After the loop** (before the `batch_update`/`update_range` calls), append summary:

```python
if archive_data:
    total_h = sum(h[0] for h in archive_data)
    total_c = sum(h[1] for h in archive_data)
    total_r = sum(h[2] for h in archive_data)
    ratio = round(total_r / total_h, 2) if total_h > 0 else 0

    summary = [""] * num_cols
    summary[0] = "Total"
    for col_name, val in [
        (ColumnName.HOURS_WORKED.value, str(total_h)),
        (ColumnName.TOTAL_COST_USD.value, str(total_c)),
        (ColumnName.REVENUE_USD.value, str(total_r)),
    ]:
        col_idx = _find_column_contains(headers, col_name)
        if col_idx is not None:
            _pad_row(summary, col_idx + 1)
            summary[col_idx] = val
    summary[period_idx] = period_name
    archive.append(summary)
```

Summary columns: Hours Worked, Total Cost, Revenue, Period. Ratio (was `=F6/D6`) is also `total_r / total_h` — not needed in its own column unless the user wants it separate.

### Tests

Update `test_archive_current_period_writes_period_column`:
- Verify a "Total" row exists as the last row in archive
- Verify Hours, Total Cost, and Revenue sums match expected values
- Verify no template formula/`#DIV/0!` cells exist

## REST API / Config / Security

None.
