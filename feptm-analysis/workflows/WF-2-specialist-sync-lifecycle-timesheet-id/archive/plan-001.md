# SDD Technical Plan: FR-SYNC-001

## Architecture Overview

Two bugs in `TimesheetProjectService` break the sync lifecycle:

**Bug 1 — `sync_project_specialists` (line 66):** `list_from_sheet` returns `(specialists, existing_count)` where `existing_count` counts pre-existing timesheet holders. This is assigned to `new_count` and used as the guard for `update_timesheet_ids` on line 77. When all specialists are new, `existing_count = 0` → `update_timesheet_ids` never called → timesheet IDs never written to Team sheet.

**Bug 2 — `sync_project_rates` (line 116):** Skips specialists without timesheets. If Bug 1 left IDs unwritten, rate sync silently does nothing.

**Fix overview:** Both methods in `TimesheetProjectService` (`project_service.py`). No API, model, protocol, or storage changes.

## Fix 1: `sync_project_specialists` — correct ID write-back guard

**File:** `feptm-server/src/feptm/timesheets/project_service.py:66-104`

Replace:
```python
specialists, new_count = self._specialists.list_from_sheet(project_id)
```
With:
```python
specialists, _ = self._specialists.list_from_sheet(project_id)
```

Then after line 75 (after the timesheet creation loop), replace:
```python
if new_count > 0:
    self._specialists.update_timesheet_ids(project_id, "Team", specialists)
```

With:
```python
needs_timesheet = [sp for sp in specialists if not sp.timesheet]
new_count = len(needs_timesheet)
for sp in needs_timesheet:
    self._specialists.create_timesheet(
        sp, context, self._timesheet_template_id
    )
if new_count > 0:
    self._specialists.update_timesheet_ids(project_id, "Team", specialists)
```

Wait — this is wrong. The creation loop on lines 71-75 iterates `specialists` checking `if not sp.timesheet`. The `create_timesheet` method mutates `sp.timesheet` in-place. So after the loop, all specialists have timesheets. We need to capture the count BEFORE the loop.

Correct approach — replace lines 66-78:

```python
specialists, existing_count = self._specialists.list_from_sheet(project_id)

if not specialists:
    return [], 0, 0

context = TimesheetContext(...)

new_count = 0
for sp in specialists:
    if not sp.timesheet:
        self._specialists.create_timesheet(
            sp, context, self._timesheet_template_id
        )
        new_count += 1

if new_count > 0:
    self._specialists.update_timesheet_ids(project_id, "Team", specialists)
```

Simply count the actual creations in the loop instead of relying on `list_from_sheet`'s return value. The log message on line 101 already uses `new_count` — it will now reflect the correct count.

## Fix 2: `sync_project_rates` — auto-create timesheets before rate sync

**File:** `feptm-server/src/feptm/timesheets/project_service.py:106-132`

Before the rate update loop, add a timesheet creation block for specialists without timesheets. This makes rate sync self-sufficient — it first ensures all specialists have timesheets and are added to Current Period sheets, then syncs rates.

Replace the entire `sync_project_rates` method:

```python
def sync_project_rates(
    self, project_id: str
) -> tuple[list[Specialist], int]:
    project = self._projects.get_project_metadata(project_id)

    if not project.drive_folder_id:
        raise Exception(
            f"Cannot sync rates: drive folder ID not found for project '{project.name}'."
        )

    context = TimesheetContext(
        folder_id=project.drive_folder_id, project_name=project.name
    )

    specialists, _ = self._specialists.list_from_sheet(project_id)
    if not specialists:
        return [], 0

    created_count = 0
    for sp in specialists:
        if not sp.timesheet:
            self._specialists.create_timesheet(
                sp, context, self._timesheet_template_id
            )
            created_count += 1

    if created_count > 0:
        self._specialists.update_timesheet_ids(project_id, "Team", specialists)

    for sp in specialists:
        if not sp.timesheet:
            continue
        import_formula = self._formulas.get_import_timesheet_formula(sp.timesheet)
        if project.report_spreadsheet_id:
            self._projects.add_specialist_to_report(
                project.report_spreadsheet_id, sp, import_formula
            )
            self._projects.sync_rates_to_current_period(
                project.report_spreadsheet_id, sp
            )
        if project.calculations_spreadsheet_id:
            self._projects.add_specialist_to_report(
                project.calculations_spreadsheet_id, sp, import_formula
            )
            self._projects.sync_rates_to_current_period(
                project.calculations_spreadsheet_id, sp
            )

    updated_count = sum(1 for sp in specialists if sp.timesheet)
    log.info("Synced rates for %d specialists", updated_count)
    return specialists, updated_count
```

Key changes:
- Added `drive_folder_id` guard (parity with `sync_project_specialists`)
- Added timesheet creation block before rate sync (lines matching `sync_project_specialists:62-78`)
- `add_specialist_to_report` called before `sync_rates_to_current_period` to ensure specialist exists in Current Period sheet
- `updated_count` counts all specialists with timesheets, not just those in the rate loop

## No changes to
- `protocols.py` — no new storage methods
- `project_storage.py` — no new storage methods
- `projects.py` — handler contract unchanged
- Models — unchanged

## Test Coverage

### Fix 1 tests (`test_project_service.py`)
- `test_sync_all_new_specialists_writes_ids` — all specialists new, verifies `update_timesheet_ids` is called
- `test_sync_mixed_specialists_writes_ids` — mix of existing and new, verifies call

### Fix 2 tests (`test_project_service.py`)
- `test_sync_rates_auto_creates_timesheets` — specialists without timesheets, verifies `create_timesheet` + `update_timesheet_ids` are called
- `test_sync_rates_skips_auto_create_when_timesheets_exist` — all have timesheets, verifies `create_timesheet` NOT called

### Existing tests
- `test_sync_project_rates_success` — update to expect `add_specialist_to_report` calls alongside `sync_rates_to_current_period`
- `test_sync_project_rates_empty_sheet` — unchanged
- `test_sync_project_rates_skips_no_timesheet` — needs updating: now timesheets get auto-created
- `test_sync_project_rates_missing_metadata` — unchanged

## @req Annotation

Handler `sync_project_rates` already has `# @req FR-SYNC-RATES-001`. Add `FR-SYNC-001`:
```python
# @req FR-SYNC-RATES-001, FR-SYNC-001
```

Handler `sync_project_specialists` needs `# @req FR-SYNC-001, FR-SPECIALIST-001`.
