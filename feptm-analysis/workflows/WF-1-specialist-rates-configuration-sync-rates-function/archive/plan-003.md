# Plan: WF-1 v3 — Invalid Rate Handling

## Requirement Traceability

| FR | Version | Change |
|----|---------|--------|
| FR-SYNC-001 | v3 | Empty/invalid rates no longer default to 0; preserve previous rates + ERROR log + continue |
| FR-SYNC-RATES-001 | v5 | Same invalid rate handling; ERROR log format specified; recalculation covers every work entry with empty Payment Period |

## Architecture Overview

**Affected repos:** feptm-server

**Data flow (rate sync):**
1. `POST /api/projects/sync-rates` → `projects.py:sync_project_rates`
2. `TimesheetProjectService.sync_project_rates()` → `project_service.py:167`
3. `SpecialistStorage.list_from_sheet()` → parses rates from Team sheet → `specialist_storage.py:24`
4. `ProjectStorage.sync_rates_to_current_period()` → writes rates to Current Period → `project_storage.py:257`

**Problem:** `_parse_decimal()` in `specialist_storage.py:268` calls `utils.parse_decimal_safely()` which returns `Decimal(0)` for empty/invalid values. The specialist model stores `rate=0`, and `sync_rates_to_current_period` overwrites the previous rate with 0, destroying financial data.

**Fix:** Make rates `Decimal | None` in the Specialist model. `None` signals "invalid/unparseable". Validate in the service layer before writing. Skip invalid specialists with ERROR log, continue processing valid rows.

## REST API / OpenAPI Schema Changes

None. The API contract (`ProjectSyncRatesResponse`) does not change. The response still returns `(specialists, updated_count)`. Invalid-rate specialists are included in the returned list but not counted in `updated_count` and not written to sheets.

## Storage Changes

### `src/feptm/models/specialist.py`

Change `internal_rate` and `external_rate` from `Decimal = Decimal(0)` to `Decimal | None = None`.

`None` means the rate was empty or unparseable in the Team sheet. A valid rate of `0` (explicit "0" in the sheet) remains `Decimal(0)`.

### `src/feptm/storage/specialist_storage.py`

`_parse_decimal()` (line 268):
- Return `None` for empty values (empty string, whitespace, missing cell).
- Return `None` for unparseable values (non-numeric strings).
- Return `Decimal(0)` only when the cell explicitly contains "0".
- Log WARNING during parse: `"Invalid {field} for {name}: '{value}'"`.

### `src/feptm/storage/project_storage.py`

`_write_specialist_fields()` (line 1159):
- Guard: skip rate columns when specialist rate is `None` (defensive — service layer should prevent this path).
- Only write rate cells when the rate value is not `None`.

## Implementation Details

### `src/feptm/timesheets/project_service.py`

`sync_project_rates()` (line 167):

After listing specialists and before the sync loop, validate each specialist's rates:

```python
valid_specialists = []
for sp in specialists:
    if sp.internal_rate is None or sp.external_rate is None:
        invalid_field = "internal_rate" if sp.internal_rate is None else "external_rate"
        invalid_value = "<empty>" if ... else str(...)
        log.error(
            "Invalid rate for specialist '%s': %s='%s' is not a valid number. "
            "Previous rate retained.",
            sp.name, invalid_field, invalid_value,
        )
        continue
    valid_specialists.append(sp)
```

Use `valid_specialists` for the rate sync loop. The full `specialists` list is still returned in the response.

The ERROR log format matches FR-SYNC-RATES-001 v5 acceptance criteria:
> `Invalid rate for specialist '{specialist_name}': {rate_type}='{value}' is not a valid number. Previous rate retained.`

Both `internal_rate` and `external_rate` are checked independently. If either is `None`, the specialist is skipped entirely (both rates preserved).

### Downstream impact

- `sync_project_specialists()` (line 101): Uses `update_current_period` which writes all specialist fields including rates. For the specialist sync path, `None` rates should not be written. Add the same `None` guard in `_write_specialist_fields`.
- `close_period()` (line 235): Uses rates from `get_stale_specialists()` which parses from Current Period sheet (already numeric). No change needed.
- `archive_current_period()` (line 558): Uses `float(sp.external_rate)` and `float(sp.internal_rate)`. If rate is `None`, this would crash. Add guard: skip specialists with `None` rates in archive (they should not reach this path since they are not synced).

### `src/feptm/storage/project_storage.py` — `get_stale_specialists()`

Lines 784-789: Currently defaults to `Decimal(0)` when rate parse fails. Keep this behavior — stale specialist rates come from the Current Period sheet (already validated numeric data), so `None` is not expected here.

## Security Considerations

None. Rate values are numeric financial data, not secrets. No new attack surface.

## Config Changes

None. No new environment variables or configuration values.

## Test Plan

| # | Test | File | Validates |
|---|------|------|-----------|
| 1 | `test_sync_rates_invalid_rate_logs_error_and_skips` | `test_project_service.py` | ERROR log format, specialist skipped, other specialists processed |
| 2 | `test_sync_rates_both_rates_invalid` | `test_project_service.py` | Both rates None → single ERROR log, specialist skipped |
| 3 | `test_sync_rates_one_rate_invalid` | `test_project_service.py` | One rate None → ERROR log, specialist skipped entirely |
| 4 | `test_sync_rates_all_valid_no_error` | `test_project_service.py` | Valid rates → no ERROR, all processed |
| 5 | `test_parse_decimal_returns_none_for_empty` | `test_specialist_storage.py` or inline | Empty string → None |
| 6 | `test_parse_decimal_returns_none_for_invalid` | `test_specialist_storage.py` or inline | "abc" → None |
| 7 | `test_parse_decimal_returns_zero_for_explicit_zero` | `test_specialist_storage.py` or inline | "0" → Decimal(0) |
| 8 | `test_parse_decimal_returns_decimal_for_valid` | `test_specialist_storage.py` or inline | "100.50" → Decimal("100.50") |
| 9 | Audit: full repo audit | — | Zero ERR, zero WARN in touched files |
