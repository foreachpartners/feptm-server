# WF-7: Fix Payment Distribution column J summary formula

## Affected FRs

- **FR-PAYMENT-001** (Close payment periods and archive reports)
- **FR-SPECIALIST-001** (Remove a specialist from future periods through Team)

## Bug Summary

Payment Distribution column J contains a text summary formula:

```
=СЦЕПИТЬ($A2, " | Project: ProjectName | Period: ", $C2, " | Hours: ", $D2, " | Rate (USD): ", $G2, " | Total (USD): ", $H2)
```

Three problems:

1. **Literal "ProjectName"**: never replaced with the real project name
2. **Live formula references in archives**: references A2, C2, D2, G2, H2 of Current Period — stays stale in archived tabs where the formula is copied verbatim as part of `new_row = list(row)`
3. **Period is empty**: column C (Period) is only populated during archive creation, not in Current Period

## Architecture Overview

### Affected Repo

- `feptm-server` — all changes

### Data Flow

```
sync_project_specialists / sync_project_rates
├── sp.project = project.name                               # NEW: inject project name
├── update_current_period()
│   └── _write_specialist_fields()
│       └── if Payment Distribution: write column J formula  # NEW: with real project name

close_period()
├── stale_specialists → sp.project = project.name           # NEW: inject project name
├── archive_current_period()
│   └── if Payment Distribution: write column J text value   # NEW: computed from archived values
```

## REST API / OpenAPI Changes

None.

## Storage Changes

### `feptm-server/src/feptm/storage/project_storage.py`

#### 1. `_write_specialist_fields()` — column J formula

After the existing `field_updates` batch write (line ~1125), detect Payment Distribution by checking if headers contain `CLIENT_HOURLY_RATE_USD`. If detected and `specialist.project` is set, write a column J formula:

```python
if specialist.project:
    pd_col = _find_column_contains(headers, ColumnName.CLIENT_HOURLY_RATE_USD.value)
    if pd_col is not None:
        formula = (
            f'=CONCATENATE($A{target_row},'
            f'" | Project: {specialist.project} | Period: ",'
            f'$C{target_row}, " | Hours: ", $D{target_row},'
            f'" | Rate (USD): ", $G{target_row},'
            f'" | Total (USD): ", $H{target_row})'
        )
        # batch update to column J (index 9)
```

This covers both `sync_project_specialists` and `sync_project_rates` which both call `_write_specialist_fields`.

#### 2. `archive_current_period()` — column J text value

After line 629 (where period is set on `new_row`), detect Payment Distribution and write a computed text value to column J:

```python
if _find_column_contains(headers, ColumnName.CLIENT_HOURLY_RATE_USD.value) is not None:
    if col_j_idx is not None:
        _pad_row(new_row, col_j_idx + 1)
        text = (
            f"{sp_name} | Project: {sp.project or ''}"
            f" | Period: {period_name} | Hours: {hours}"
            f" | Rate (USD): {sp_rate} | Total (USD): {sp_cost}"
        )
        new_row[col_j_idx] = text
```

Text value (not formula) ensures immutability in protected archives.

## Service Layer Changes

### `feptm-server/src/feptm/timesheets/project_service.py`

Inject `sp.project = project.name` in three flows:

**`sync_project_specialists()`** — after line 115 (specialists fetched from Team):
```python
for sp in specialists:
    sp.project = project.name
```

**`sync_project_rates()`** — after line 182 (specialists fetched from Team):
```python
for sp in specialists:
    sp.project = project.name
```

**`close_period()`** — after stale specialists discovered:
```python
for sp in stale_specialists:
    sp.project = project.name
```

## Security Considerations

None.

## Config Changes

None.
