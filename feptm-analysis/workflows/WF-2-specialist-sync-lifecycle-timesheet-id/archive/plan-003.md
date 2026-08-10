# Plan: Fix IMPORTRANGE placeholder mismatch — SpecialistSpreadsheetID not replaced with timesheet ID

## Architecture Overview

**Affected repos**: `feptm-server` (code fix + tests)

**Data flow**:

```
Config Google Sheet (Formulas)       ConfigStorage.get_import_timesheet_formula()
┌──────────────────────────────┐     ┌────────────────────────────────────────────┐
│ Formulas sheet               │read │ get_formula("Import specialist timesheet")  │
│ Import specialist timesheet: │────>│   -> '=IMPORTRANGE("SpecialistSpreadsheet  │
│   =IMPORTRANGE(              │     │            ID"; "Sheet1!A:Z")'              │
│   "SpecialistSpreadsheetID"; │     │                                            │
│   ...)                       │     │ formula.replace("{timesheet_id}",           │
└──────────────────────────────┘     │              sp.timesheet)  ← NO-OP!       │
                                     └────────────────────────────────────────────┘
```

The config sheet stores the formula with `SpecialistSpreadsheetID` as placeholder.
The code replaces `{timesheet_id}`. These don't match → `.replace()` is a no-op → the
literal string `SpecialistSpreadsheetID` is written to the spreadsheet tab as the
IMPORTRANGE spreadsheet ID → Google Sheets shows `#REF!` error.

## Root Cause

In `config_storage.py:63` (`get_import_timesheet_formula`):
```python
return formula.replace("{timesheet_id}", specialist_timesheet_id)
```

The config sheet formula uses the placeholder `SpecialistSpreadsheetID`, not `{timesheet_id}`.
The replace call finds no match and returns the formula unchanged.

## REST API / OpenAPI Schema Changes

None.

## Storage Changes

**File**: `feptm-server/src/feptm/storage/config_storage.py`

**Method**: `get_import_timesheet_formula` (line 61-63)

**Change**: Replace `SpecialistSpreadsheetID` instead of `{timesheet_id}`:

**Before**:
```python
def get_import_timesheet_formula(self, specialist_timesheet_id: str) -> str:
    formula = self.get_formula("Import specialist timesheet")
    return formula.replace("{timesheet_id}", specialist_timesheet_id)
```

**After**:
```python
def get_import_timesheet_formula(self, specialist_timesheet_id: str) -> str:
    formula = self.get_formula("Import specialist timesheet")
    return formula.replace("SpecialistSpreadsheetID", specialist_timesheet_id)
```

This is a 1-line change.

## Implementation Details

- No config changes
- No handler changes
- No new imports
- Existing caching logic in `get_formula()` is unaffected
- Tests: verify that `get_import_timesheet_formula` correctly substitutes the spreadsheet ID

**Note**: AR-ARCH-004 mandates `{timesheet_id}`-style named placeholders. The production config sheet still uses `SpecialistSpreadsheetID`. This fix matches the actual config content. The config sheet can be migrated later to use `{timesheet_id}` as a separate task.

## Security Considerations

None.

## Config Changes

None.
