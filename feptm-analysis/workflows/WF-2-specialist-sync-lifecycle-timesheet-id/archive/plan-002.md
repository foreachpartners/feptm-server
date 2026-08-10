# Plan: Fix Current Period sync — new specialist rows show only names

## Architecture Overview

**Affected repos**: `feptm-server` (code fix + tests), `feptm-analysis` (workflow artifacts)

**Data flow** (sync adds a specialist to Current Period):

```
sync_project_specialists()                   # project_service.py:65
  → update_current_period()                  # project_storage.py:224
    → _read_current_period()                 # reads headers + existing rows
    → _specialist_in_sheet()                 # skip if already present
    → _find_insert_position()                # where to insert the new row
    → _insert_and_update_row()               # project_storage.py:323 ← BUG HERE
      → insertDimension                      # inserts new empty row
      → _copy_row_formatting()               # copies template row via PASTE_NORMAL
      → _write_specialist_fields()           # overwrites cells with new data
```

## Root Cause

In `_copy_row_formatting` (`project_storage.py:384-428`), the `copyPaste PASTE_NORMAL` (line 422) copies **values, formulas, and formatting** from the template row to the new row. Then `_write_specialist_fields` uses 5 separate `values().update()` calls to overwrite specific cells. These target overlapping cells through different API endpoints (`batchUpdate` vs `values.update`). The template row's pasted values overwrite the new specialist's data, leaving only the name column populated.

## REST API / OpenAPI Schema Changes

None. `POST /api/projects/sync` is unchanged.

## Storage Changes

**File**: `feptm-server/src/feptm/storage/project_storage.py`

**Method**: `_copy_row_formatting` (line 403-427)

**Change**: Replace single `copyPaste PASTE_NORMAL` with two `copyPaste` requests in the same `batchUpdate`:

1. `PASTE_FORMULA` — copies only formulas (relative references auto-adjust)
2. `PASTE_FORMAT` — copies only formatting (number formats, borders, colors)

Neither paste type touches cell **values**. Values are set exclusively by `_write_specialist_fields` called immediately after.

**Before**:
```python
requests=[{
    "copyPaste": {
        "source": {...},
        "destination": {...},
        "pasteType": "PASTE_NORMAL",
        "pasteOrientation": "NORMAL",
    }
}]
```

**After**:
```python
requests=[
    {
        "copyPaste": {
            "source": {...},
            "destination": {...},
            "pasteType": "PASTE_FORMULA",
            "pasteOrientation": "NORMAL",
        }
    },
    {
        "copyPaste": {
            "source": {...},
            "destination": {...},
            "pasteType": "PASTE_FORMAT",
            "pasteOrientation": "NORMAL",
        }
    },
]
```

## Implementation Details

- No config changes
- No handler changes
- No new imports
- Existing try/except in `_insert_and_update_row` covers failures
- `_add_formulas_for_row` fallback path (no template row) is unaffected
- Test: verify `_copy_row_formatting` sends two `copyPaste` requests with correct paste types

## Security Considerations

None. No secrets, auth, or permission changes.

## Config Changes

None.
