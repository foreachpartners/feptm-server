# Plan: Standardize date reading to numeric serial format

## Context

Two different date parsing paths exist for reading dates from Google Sheets:

| Path | API mode | Caller | Parser | Formats |
|------|----------|--------|--------|---------|
| Timesheet Date column | `UNFORMATTED_VALUE` | `close_period_in_timesheet`, `_sum_period_hours` | `_serial_to_date` | 7+ formats |
| Team sheet Date column | `FORMATTED_VALUE` (default) | `_parse_row` via `_parse_date` | `parse_date_safely` | 1 format |

The Team sheet path reads dates as formatted strings (e.g. `"Aug 11, 2026"`) and parses with a single `%b %d, %Y` format. This fails silently for dates entered in other formats, falling back to `datetime.utcnow()`.

## Fix

Standardize the Team sheet path to use `UNFORMATTED_VALUE` and `_serial_to_date`, matching the timesheet path.

## File-Level Changes

### 1. `feptm-server/src/feptm/storage/specialist_storage.py`

**`_parse_row`** (line 153): replace `_parse_date` call with `_serial_to_date`:

```python
# BEFORE
date_val = _parse_date(row, hmap.get("date"), name)

# AFTER
date_raw = _opt(row, hmap.get("date"))
date_val = _serial_to_date(date_raw) if date_raw else None
```

This reads the raw cell value and passes it through `_serial_to_date` which handles both numeric serials and formatted strings.

**`_parse_date`** (line 228): remove — no longer needed after the above change.

### 2. `feptm-server/src/feptm/services/google_sheets_service.py`

**`get_sheet_data_with_headers`**: add `valueRenderOption="UNFORMATTED_VALUE"` to the `.get()` API call so the Team sheet reader gets raw serial numbers instead of formatted strings.

---

## REST API / Config / Security

None.
