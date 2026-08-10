# Plan: Use spreadsheet URLs instead of raw IDs in IMPORTRANGE and Team sheet

## Architecture Overview

**Affected repos**: `feptm-server`

Two places currently write raw spreadsheet IDs. Both should write full URLs.

## Storage Changes

### 1. IMPORTRANGE formula — substitute URL instead of ID

**File**: `feptm-server/src/feptm/storage/config_storage.py:63-69`

**Before**:
```python
return re.sub(
    r"(SpecialistSpreadsheetID|\{timesheet_id\})",
    specialist_timesheet_id,
    formula,
)
```

**After**:
```python
url = f"https://docs.google.com/spreadsheets/d/{specialist_timesheet_id}"
return re.sub(
    r"(SpecialistSpreadsheetID|\{timesheet_id\})",
    url,
    formula,
)
```

### 2. Team sheet Timesheet column — write URL instead of ID

**File**: `feptm-server/src/feptm/storage/specialist_storage.py:199-204`

**Before**:
```python
values=[[ts_id]],
```

**After**:
```python
url = f"https://docs.google.com/spreadsheets/d/{ts_id}"
values=[[url]],
```

## Implementation Details

- No config changes
- No handler changes
- No new imports
- URL pattern matches `UrlPattern.SPREADSHEET` in `config_service.py`
- Tests: update assertions to expect URLs instead of raw IDs

## Security Considerations

None.

## Config Changes

None.
