# Plan: WF-8 fix2 — Archive before timesheet update

## Problem

Current Period uses IMPORTRANGE formulas that pull from timesheets, filtering on empty Payment Period. When `close_period_in_timesheet()` fills in Payment Period first, the IMPORTRANGE formulas immediately recalculate to 0 hours. Then `archive_current_period()` copies this now-zeroed Current Period, resulting in 0 hours in the archived sheet.

## Solution

**Reorder operations in `close_period()`:**

1. **Archive Current Period FIRST** — `duplicateSheet` + read `UNFORMATTED_VALUE` + write back as `RAW` freezes the values before timesheet updates
2. **Update timesheet Payment Periods** — count entries
3. **If total_entries == 0, delete the archived tabs** — respects FR-PAYMENT-001 requirement that "If no work entries with empty Payment Period → don't create archived tabs"

## Files to Change

### 1. `src/feptm/storage/protocols.py`

Add `delete_sheet()` method to `ProjectStorageProtocol`:

```python
def delete_sheet(self, spreadsheet_id: str, sheet_name: str) -> bool:
    """Delete a sheet tab from a spreadsheet. Returns True if deleted, False if not found."""
    ...
```

### 2. `src/feptm/storage/project_storage.py`

Implement `delete_sheet()`:

```python
def delete_sheet(self, spreadsheet_id: str, sheet_name: str) -> bool:
    if not self._sheets.sheets_service:
        raise Exception("Google Sheets service not initialized")
    
    spreadsheet = (
        self._sheets.sheets_service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id)
        .execute()
    )
    sheet_id = None
    for sheet in spreadsheet.get("sheets", []):
        if sheet.get("properties", {}).get("title") == sheet_name:
            sheet_id = sheet.get("properties", {}).get("sheetId")
            break
    
    if sheet_id is None:
        return False
    
    self._sheets.batch_update(
        spreadsheet_id=spreadsheet_id,
        requests=[{"deleteSheet": {"sheetId": sheet_id}}],
    )
    log.info("Deleted sheet %s from spreadsheet %s", sheet_name, spreadsheet_id)
    return True
```

### 3. `src/feptm/timesheets/project_service.py`

**Reorder `close_period()` operations:**

```python
def close_period(
    self,
    project_id: str,
    period_name: str,
) -> ClosePeriodResponse:
    project = self._projects.get_project_metadata(project_id)
    specialists, _ = self._specialists.list_from_sheet(project_id)

    if _has_duplicate_names(specialists):
        return ClosePeriodResponse(...)

    # Step 1: Archive Current Period FIRST (before timesheet updates)
    report_archived = False
    calculations_archived = False
    
    if project.report_spreadsheet_id:
        report_archived = self._projects.archive_current_period(
            project.report_spreadsheet_id,
            period_name,
        )
    if project.calculations_spreadsheet_id:
        calculations_archived = self._projects.archive_current_period(
            project.calculations_spreadsheet_id,
            period_name,
        )

    # Step 2: Update timesheet Payment Periods
    total_entries = 0
    specialists_processed = 0

    for sp in specialists:
        if not sp.timesheet:
            continue
        ts_id = utils.extract_id_from_hyperlink_formula(sp.timesheet) or sp.timesheet
        updated = self._projects.close_period_in_timesheet(
            ts_id, period_name
        )
        specialists_processed += 1
        total_entries += updated

    # Handle stale specialists
    active_names = {sp.name for sp in specialists}
    if project.calculations_spreadsheet_id:
        stale_specialists = self._projects.get_stale_specialists(
            project.calculations_spreadsheet_id, active_names
        )
        for sp in stale_specialists:
            sp.project = project.name
            if not sp.timesheet:
                continue
            ts_id = utils.extract_id_from_hyperlink_formula(sp.timesheet) or sp.timesheet
            updated = self._projects.close_period_in_timesheet(
                ts_id, period_name
            )
            specialists_processed += 1
            total_entries += updated

    # Step 3: If no entries were updated, delete the archived tabs
    if total_entries == 0:
        if report_archived and project.report_spreadsheet_id:
            self._projects.delete_sheet(project.report_spreadsheet_id, period_name)
            report_archived = False
        if calculations_archived and project.calculations_spreadsheet_id:
            self._projects.delete_sheet(project.calculations_spreadsheet_id, period_name)
            calculations_archived = False
    else:
        # Protect the archived sheets
        if report_archived and project.report_spreadsheet_id:
            self._projects.protect_archived_sheet(
                project.report_spreadsheet_id,
                period_name,
                payment_status_col_idx=5,
            )
        if calculations_archived and project.calculations_spreadsheet_id:
            self._projects.protect_archived_sheet(
                project.calculations_spreadsheet_id,
                period_name,
                payment_status_col_idx=5,
            )

    # Step 4: Remove stale specialists from Current Period
    if project.report_spreadsheet_id:
        removed = self._projects.remove_stale_specialists(
            project.report_spreadsheet_id, active_names
        )
        log.info("Removed %d stale specialists from report Current Period", removed)
    if project.calculations_spreadsheet_id:
        removed = self._projects.remove_stale_specialists(
            project.calculations_spreadsheet_id, active_names
        )
        log.info("Removed %d stale specialists from calculations Current Period", removed)

    log.info(
        "Closed period %s: %d entries updated, %d specialists processed",
        period_name,
        total_entries,
        specialists_processed,
    )
    return ClosePeriodResponse(
        created=datetime.now(UTC),
        project_id=project_id,
        period_name=period_name,
        entries_updated=total_entries,
        specialists_processed=specialists_processed,
        report_archived=report_archived,
        calculations_archived=calculations_archived,
    )
```

### 4. `tests/timesheets/test_project_service.py`

Update close_period tests to verify:
- Archive is called BEFORE timesheet updates
- If no entries updated, archived tabs are deleted
- If entries updated, archived tabs are protected

## Verification

```bash
cd feptm-server && make typecheck && make test
```

All tests should pass.
