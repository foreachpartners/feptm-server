# Plan: Write numbers, not strings, to Current Period and Archive

**Workflow:** WF-5 (iteration 4)
**FRs:** FR-PAYMENT-001, FR-SPECIALIST-001
**Ceremony:** medium
**Session:** SID-1786484030-faeeb398

## 1. Root Cause

Two places write numeric values as text cells in Google Sheets, causing SUM to ignore them:

| Location | What it writes | Result |
|----------|---------------|--------|
| `_write_specialist_fields` | `stringValue: str(rate)` | rates are text in Current Period |
| `archive_current_period` | `str(12.0)`, `str(840.0)` with RAW | all computed values are text in Archive |

## 2. Fix

### 2.1 `_write_specialist_fields` — use `numberValue` for rate columns

**File:** `src/feptm/storage/project_storage.py`

Numeric fields (rates) written as numbers; name/role stay as strings:

```python
for col_name, val in field_updates:
    col_idx = ...
    if col_idx is None:
        continue
    if isinstance(val, (int, float, Decimal)):
        cell = {"userEnteredValue": {"numberValue": float(val)}}
    else:
        cell = {"userEnteredValue": {"stringValue": str(val)}}
    requests.append({
        "updateCells": {
            ...
            "rows": [{"values": [cell]}],
            "fields": "userEnteredValue",
        }
    })
```

### 2.2 `archive_current_period` — drop `str()` on computed values

**File:** `src/feptm/storage/project_storage.py`

**Per-specialist rows** (lines ~610-616):
```python
# Before:
new_row[col_idx] = str(hours)
new_row[col_idx] = str(cl_cost)

# After:
new_row[col_idx] = hours
new_row[col_idx] = cl_cost
```

**Summary row** (lines ~634-645):
```python
# Before:
str(total_h), str(total_cl), str(total_sp), str(total_r)

# After:
total_h, total_cl, total_sp, total_r
```

`value_input_option="RAW"` stays — with raw numbers Google Sheets stores as number type.

## 3. REST API / Config / Security

None.

## 4. References

- `project_storage.py:1073-1116` — `_write_specialist_fields`
- `project_storage.py:547-670` — `archive_current_period`
