# SDD Technical Plan: FR-SYNC-001, FR-SPECIALIST-001 (Run 5)

## Architecture Overview

**Affected repos**: `feptm-server`

**Bug**: When a specialist is removed from Team then re-added with the same name and an empty Timesheet field, the sync creates a duplicate `"Time Tracking for …"` file on Drive and the specialist's report tab continues to reference the old timesheet via a stale IMPORTRANGE formula. Hours from the new timesheet never appear in Current Period calculations.

### Data flow (remove → re-add cycle)

```
1. Specialist deleted from Team sheet
   → Old timesheet file remains on Drive (orphaned)
   → Specialist tab remains in report/calculations spreadsheet (A1 = old IMPORTRANGE)
   → Current Period row deleted (via remove_stale_specialists — fixed in BUG-02)

2. Specialist re-added to Team sheet, Timesheet column empty
   → sync_project_specialists()
      → create_timesheet() — no dedup check — creates NEW file (duplicate)
      → add_specialist_to_report() — tab exists → SKIPS formula update
      → Current Period row created fresh (correct)
   → Result: tab still points to old timesheet; new file orphaned
```

### Two root causes

| RC | What | Where |
|----|------|-------|
| RC1 | `create_timesheet()` creates a new Drive file unconditionally — no check for existing file with same title in project folder | `specialist_storage.py:35-47` |
| RC2 | `add_specialist_to_report()` skips formula update when the specialist tab already exists | `project_storage.py:203-222` |

### Fix overview

1. **Drive dedup**: Before creating a new timesheet, search the project folder for an existing file with the same title. If found, reuse its spreadsheet ID.
2. **Formula refresh**: Always write the IMPORTRANGE formula to cell A1 of the specialist tab, regardless of whether the tab already existed.

## REST API / OpenAPI Schema Changes

None. No endpoint signatures, request/response models, or status codes change.

## Storage Changes

### 1. `feptm-server/src/feptm/services/google_sheets_service.py`

**New method: `find_file_in_folder()`**

```python
def find_file_in_folder(self, folder_id: str, file_name: str) -> str | None:
    """Search for a spreadsheet by name in a Drive folder. Return file ID or None."""
    if not self.drive_service:
        raise Exception("Drive service not initialized")
    try:
        query = (
            f"'{folder_id}' in parents and name = '{file_name}'"
            f" and mimeType = 'application/vnd.google-apps.spreadsheet'"
            f" and trashed = false"
        )
        results = (
            self.drive_service.files()
            .list(q=query, fields="files(id, name)")
            .execute()
        )
        files = results.get("files", [])
        return files[0]["id"] if files else None
    except HttpError as error:
        raise Exception(f"Failed to search files in folder: {error}")
```

Uses Google Drive `files().list()` with a `q` parameter filtering by parent folder, filename, MIME type, and trashed status. Returns the first match's `id` or `None`.

### 2. `feptm-server/src/feptm/storage/specialist_storage.py`

**Modified: `create_timesheet()` — drive dedup**

Before calling `ensure_spreadsheet_from_template()`, search the project folder for an existing timesheet file. If found, reuse its ID.

```python
def create_timesheet(
    self, specialist: Specialist, context: TimesheetContext, template_id: str
) -> dict[str, str]:
    if not template_id:
        raise Exception("Timesheet template ID not configured")

    title = utils.generate_timesheet_title(specialist.name, context.project_name)

    existing_id = self._sheets.find_file_in_folder(context.folder_id, title)
    if existing_id:
        specialist.timesheet = existing_id
        log.info("Reusing existing timesheet for %s", specialist.name)
        return {
            "spreadsheet_id": existing_id,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{existing_id}",
        }

    result = self._sheets.ensure_spreadsheet_from_template(
        template_id=template_id, new_title=title, folder_id=context.folder_id
    )
    specialist.timesheet = result["spreadsheet_id"]
    log.info("Created timesheet for %s", specialist.name)
    return result
```

### 3. `feptm-server/src/feptm/storage/project_storage.py`

**Modified: `add_specialist_to_report()` — always refresh formula**

Before: created tab only when absent; skipped on existing.
After: write the formula to A1 unconditionally (create tab if absent, then write).

```python
def add_specialist_to_report(
    self,
    spreadsheet_id: str,
    specialist: Specialist,
    import_formula: str,
) -> None:
    tab_name = specialist.display_name or specialist.name
    existing = self._list_sheet_titles(spreadsheet_id)
    if tab_name not in existing:
        self._sheets.batch_update(
            spreadsheet_id=spreadsheet_id,
            requests=[{"addSheet": {"properties": {"title": tab_name}}}],
        )
        log.info("Created tab for %s in spreadsheet", specialist.name)
    self._sheets.update_range(
        spreadsheet_id=spreadsheet_id,
        range_name=RangeFormat.SINGLE_CELL.value.format(sheet_name=tab_name),
        values=[[import_formula]],
        value_input_option="USER_ENTERED",
    )
```

### 4. `feptm-server/src/feptm/storage/protocols.py`

No protocol changes — `find_file_in_folder` is a low-level GoogleSheetsService method, not a storage protocol method. `SpecialistStorageProtocol.create_timesheet` and `ProjectStorageProtocol.add_specialist_to_report` signatures remain unchanged.

## Implementation Details

### Handler Logic

No handler changes. The `sync_project_specialists` and `sync_project_rates` handlers (`api/v1/projects.py`) are unchanged — they continue to delegate to `TimesheetProjectService`.

### Error Handling

- `find_file_in_folder()`: Wraps Drive API errors in `Exception` with descriptive message (consistent with existing patterns in `google_sheets_service.py`).
- `create_timesheet()`: Handles the case where `find_file_in_folder` returns `None` by falling through to normal creation.
- `add_specialist_to_report()`: The `update_range()` call for A1 does not distinguish between new and existing tabs — on a freshly created tab, the subsequent write is idempotent with the previous code's behavior.

### Edge Cases

1. **Specialist re-added with different rates**: `update_current_period()` and `sync_rates_to_current_period()` continue to write correct rates to Current Period. The tab formula only changes if the timesheet ID changes.
2. **Multiple specialists with same name** (AR-DATA-001 disambiguation): `display_name` with `(row_index)` suffix ensures tabs are distinct. The Drive dedup uses `specialist.name` (raw name, not `display_name`) for the file title, matching `generate_timesheet_title()`.
3. **Project folder contains stale files with same title**: The dedup finds the first match. If the old timesheet was deleted/trashed, `trashed = false` in the query excludes it.
4. **Concurrent sync operations**: Google Drive `files().list()` results are eventually consistent. A brief race between two sync calls could produce a duplicate, but this is unlikely in the single-user workflow.
5. **Empty Timesheet column on existing specialist**: The `create_timesheet()` guard `if not sp.timesheet` in the service layer ensures we only enter the creation path for truly new specialists. The Drive dedup is an additional safety net.

## Security Considerations

None. The `find_file_in_folder()` method:
- Uses existing OAuth credentials (already scoped for `https://www.googleapis.com/auth/drive`).
- Does not expose file IDs or names outside the service layer.
- Does not log file IDs (only specialist names in context).

## Config Changes

None. No new environment variables, template IDs, or configuration keys.

## Test Coverage

### 1. `test_create_timesheet_reuses_existing_drive_file`
- Mock `find_file_in_folder` to return a file ID
- Verify `ensure_spreadsheet_from_template` is NOT called
- Verify `specialist.timesheet` is set to the found ID

### 2. `test_create_timesheet_creates_new_when_none_found`
- Mock `find_file_in_folder` to return `None`
- Verify `ensure_spreadsheet_from_template` IS called
- Verify `specialist.timesheet` is set to the new ID

### 3. `test_add_specialist_to_report_updates_formula_when_tab_exists`
- Pre-populate `_list_sheet_titles` to include tab_name
- Verify `batch_update` (addSheet) is NOT called
- Verify `update_range` IS called with the correct formula

### 4. `test_add_specialist_to_report_creates_tab_and_writes_formula_when_absent`
- Mock `_list_sheet_titles` returning empty list
- Verify `batch_update` IS called (addSheet)
- Verify `update_range` IS called with the correct formula

### Existing tests
- `test_create_timesheet_success` — needs update: add `find_file_in_folder` mock returning `None`
- `test_create_timesheet_missing_template` — unchanged (the guard fires before dedup)
- All `sync_project_*` tests — unchanged (they mock `create_timesheet` and `add_specialist_to_report` at the service layer)
