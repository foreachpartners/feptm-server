# SDD Technical Plan: FR-SYNC-RATES-001

## Architecture Overview

FR-SYNC-RATES-001 adds a standalone sync-rates endpoint to feptm-server. Currently, specialist rates (`internal_rate`, `external_rate`) are only read from the Team sheet and written to Current Period sheets during the initial `POST /api/projects/sync` operation. If a specialist's rates change in the Team sheet after that initial sync, there is no mechanism to propagate the updated rates to report/calculation spreadsheets.

This plan adds a `POST /api/projects/sync-rates` endpoint that:
1. Re-reads specialists from the Team sheet (picking up any rate changes)
2. Writes updated rates to the Current Period sheets in the project's report and calculation spreadsheets
3. Returns the updated specialist list

**Data flow:** Team sheet → SpecialistStorage.list_from_sheet() → ProjectStorage.update_current_period() → Current Period sheets

**Affected repos:** feptm-server (code changes), feptm-analysis (workflow artifacts only)

## REST API / OpenAPI Schema Changes

### New Endpoint: `POST /api/projects/sync-rates`

**Request:**
```json
{
  "project_id": "string"
}
```

**Response (200):**
```json
{
  "created": "2026-08-08T12:00:00Z",
  "project_id": "string",
  "specialists_updated": 3,
  "specialists": [
    {
      "name": "John Doe",
      "role": "Developer",
      "project": "E-Commerce Platform",
      "internal_rate": "20.00",
      "external_rate": "25.00",
      "date": "2023-02-15T12:00:00Z",
      "timesheet": "1abCdEfGhIjKlMnOpQrStUvWxYz"
    }
  ]
}
```

**Error responses:** 500 on config/runtime errors, reusing existing error patterns from `/projects/sync`.

### New Models

- `ProjectSyncRatesRequest` — `project_id: str` (mirrors `ProjectSyncRequest` pattern)
- `ProjectSyncRatesResponse` — `created`, `project_id`, `specialists_updated: int`, `specialists: list[Specialist]`

Add to `feptm-server/src/feptm/models/project.py` (alongside existing `ProjectSyncRequest`/`ProjectSyncResponse`).

## Storage Changes

No new storage methods required. The implementation reuses existing storage contracts:

- `SpecialistStorageProtocol.list_from_sheet()` — reads latest specialists with rates from Team sheet
- `ProjectStorageProtocol.update_current_period()` — writes specialist fields (name, role, internal_rate, external_rate) + formulas to Current Period sheet
- `ProjectStorageProtocol.get_project_metadata()` — reads project to get report/calc spreadsheet IDs

No changes to `protocols.py`, `specialist_storage.py`, or `project_storage.py`.

## Implementation Details

### 1. Add sync_rates method to TimesheetProjectService

File: `feptm-server/src/feptm/timesheets/project_service.py`

New method `sync_project_rates(self, project_id: str) -> tuple[list[Specialist], int]`:

```python
def sync_project_rates(self, project_id: str) -> tuple[list[Specialist], int]:
    project = self._projects.get_project_metadata(project_id)
    specialists, _ = self._specialists.list_from_sheet(project_id)
    if not specialists:
        return [], 0

    updated_count = 0
    for sp in specialists:
        if not sp.timesheet:
            continue
        if project.report_spreadsheet_id:
            self._projects.update_current_period(
                project.report_spreadsheet_id, sp, self._formulas
            )
        if project.calculations_spreadsheet_id:
            self._projects.update_current_period(
                project.calculations_spreadsheet_id, sp, self._formulas
            )
        updated_count += 1

    log.info("Synced rates for %d specialists", updated_count)
    return specialists, updated_count
```

The method follows AR-ARCH-003: thin facade (≤30 lines per method), delegates all storage operations. Reuses the same `update_current_period` pattern from `sync_project_specialists` (lines 80–97 of project_service.py).

### 2. Add API handler

File: `feptm-server/src/feptm/api/v1/projects.py`

```python
# @req FR-SYNC-RATES-001
@router.post("/sync-rates", response_model=ProjectSyncRatesResponse)
async def sync_project_rates(request: ProjectSyncRatesRequest) -> ProjectSyncRatesResponse:
    ...
```

Handler pattern follows existing `/sync` handler: obtains `TimesheetProjectService` via `get_timesheet_project_service()`, calls service method, formats response.

### 3. Add request/response models

File: `feptm-server/src/feptm/models/project.py`

- `ProjectSyncRatesRequest` — single field `project_id: str`
- `ProjectSyncRatesResponse` — `created`, `project_id`, `specialists_updated`, `specialists`

Export from `feptm-server/src/feptm/models/__init__.py`.

### 4. @req annotation placement

Per AR-LINEAGE-001, `# @req FR-SYNC-RATES-001` goes on the line directly above the handler function in `projects.py`. No @req annotations on service layer or storage methods.

## Security Considerations

- No new secrets or credentials introduced
- No new environment variable requirements
- Uses existing authentication flow (none currently in API; handled by nginx if added)
- No user input used in spreadsheet range construction (uses existing RangeFormat enum)

## Config Changes

No new config keys. Reuses existing:
- `GOOGLE_TIMESHEET_TEMPLATE_ID` (already validated in project_sync flow)
- No prefix changes to `FEPTM_FEPTM_SERVER__`

## Test Coverage

Tests follow existing patterns in:
- `feptm-server/tests/timesheets/test_project_service.py` — unit test `sync_project_rates` method
- `feptm-server/tests/api/v1/test_projects.py` — integration test for `POST /api/projects/sync-rates`
- `feptm-server/tests/conftest.py` — reuse existing fixtures (mock_specialist_storage, mock_project_storage, mock_config_storage, client)

Test cases:
1. **Happy path:** rates synced for specialists with timesheets
2. **Empty Team sheet:** returns empty list, zero updated
3. **Specialists without timesheets:** skipped (not synced)
4. **Missing project metadata:** raises exception
5. **API integration:** returns correct response model with updated specialists
