# Technical Plan: GET /api/projects/{drive_folder_id}/

## Architecture Overview

Add a read-only GET endpoint that returns a project card by `drive_folder_id`. The endpoint queries Google Drive for folder metadata and spreadsheet listings, then assembles a structured response with table URLs and timesheet entries.

**Affected repo:** feptm-server

**Data flow:**
```
Client → GET /api/projects/{drive_folder_id}/
       → ProjectCardHandler (api/v1/projects.py)
       → TimesheetProjectService.get_project_card() (facade)
       → ProjectStorage.get_project_card() (storage)
       → GoogleSheetsService.get_file() + list_drive_spreadsheets() (Drive API)
       → ProjectCardResponse
```

No side effects. No writes. No Team sheet reads.

---

## REST API Contract

### Endpoint

```
GET /api/projects/{drive_folder_id}/
```

- Path param: `drive_folder_id` (str) — Drive folder ID
- No query params, no body
- No auth (consistent with GET /api/projects/)
- Trailing slash MUST be present (FastAPI 307 redirect avoidance)

### Registration order

Register after all existing routes in `router` to avoid path conflicts:
- `GET /` (list)
- `POST /create`
- `POST /sync`
- `POST /sync-rates`
- `GET /{drive_folder_id}/` ← new

### 200 Response Body

```json
{
  "name": "Acme",
  "drive_folder_id": "1folderId",
  "project_id": "1projectInfoSpreadsheetId",
  "tables": {
    "project_info": {
      "label": "Project info / Team",
      "spreadsheet_id": "1projectInfoSpreadsheetId",
      "url": "https://docs.google.com/spreadsheets/d/1projectInfoSpreadsheetId"
    },
    "general_expenses": {
      "label": "General Expenses",
      "spreadsheet_id": "1reportSpreadsheetId",
      "url": "https://docs.google.com/spreadsheets/d/1reportSpreadsheetId"
    },
    "payment_distribution": {
      "label": "Payment Distribution",
      "spreadsheet_id": "1calcSpreadsheetId",
      "url": "https://docs.google.com/spreadsheets/d/1calcSpreadsheetId"
    }
  },
  "timesheets": [
    {
      "name": "Time Tracking for Ada. Project Acme",
      "spreadsheet_id": "1tsAda",
      "url": "https://docs.google.com/spreadsheets/d/1tsAda"
    }
  ]
}
```

### Error Responses

| Code | Condition | detail |
|------|-----------|--------|
| 404 | Folder not found / no access | `Project folder not found.` |
| 404 | Missing one of 3 project spreadsheets | `Project spreadsheet not found: {expected file name}.` |
| 500 | Drive/Sheets unavailable, no config | `Failed to load project card: {e}` |

No 409. No 200 with `url: null`.

---

## Response Models

**File:** `src/feptm/models/project.py`

### New models

```python
class ProjectCardTable(BaseModel):
    label: str
    spreadsheet_id: str
    url: str

class ProjectCardTimesheet(BaseModel):
    name: str
    spreadsheet_id: str
    url: str

class ProjectCardResponse(BaseModel):
    name: str
    drive_folder_id: str
    project_id: str
    tables: dict[str, ProjectCardTable]
    timesheets: list[ProjectCardTimesheet]
```

Export from `src/feptm/models/__init__.py`.

### Field rules

| Field | Source |
|-------|--------|
| `name` | Drive folder name (from `get_file`) |
| `drive_folder_id` | Echo path param |
| `project_id` | Spreadsheet ID of `{name} - Project info` |
| `tables.*.label` | Fixed strings (not Drive file names) |
| `tables.*.url` | `UrlPattern.SPREADSHEET.format(spreadsheet_id=...)` |
| `timesheets[].name` | Drive file name (text of link) |
| `timesheets[].url` | `UrlPattern.SPREADSHEET.format(spreadsheet_id=...)` |

---

## Storage Layer Changes

### GoogleSheetsService — new method

**File:** `src/feptm/services/google_sheets_service.py`

```python
def list_drive_spreadsheets(self, folder_id: str) -> list[dict[str, str]]:
```

- Query: `'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false`
- Fields: `nextPageToken, files(id,name)`
- Paginated (same pattern as `list_drive_folders`)
- Returns `list[dict[str, str]]` with keys `id`, `name`
- Raises `Exception` on HttpError (consistent with existing methods)

### ProjectStorage — new method

**File:** `src/feptm/storage/project_storage.py`

```python
def get_project_card(self, folder_id: str) -> dict:
```

Logic:
1. `self._sheets.get_file(folder_id)` — verify folder exists, get name
   - On exception → raise `ProjectFolderNotFoundError(folder_id)`
   - Validate `mimeType` contains `folder` → else raise `ProjectFolderNotFoundError(folder_id)`
2. `self._sheets.list_drive_spreadsheets(folder_id)` — list all spreadsheets
3. Build expected file names using `_spreadsheet_title(name, key)` for keys `info`, `report`, `calculations`
4. Match each expected name against spreadsheet list (exact match on `name`)
5. If any of 3 not found → raise `ProjectSpreadsheetNotFoundError(expected_name)`
6. `project_id` = spreadsheet ID of `{name} - Project info`
7. Remaining spreadsheets = timesheets (sorted by name, case-insensitive: `key=lambda x: x["name"].lower()`)
8. Return dict with all fields for response assembly

### New exception classes

**File:** `src/feptm/core/exceptions.py`

```python
class ProjectFolderNotFoundError(Exception):
    def __init__(self, folder_id: str):
        self.folder_id = folder_id
        super().__init__(f"Project folder not found: {folder_id}")

class ProjectSpreadsheetNotFoundError(Exception):
    def __init__(self, expected_name: str):
        self.expected_name = expected_name
        super().__init__(f"Project spreadsheet not found: {expected_name}")
```

### ProjectStorageProtocol — add signature

**File:** `src/feptm/storage/protocols.py`

```python
def get_project_card(self, folder_id: str) -> dict:
    """Get project card data by Drive folder ID."""
    ...
```

---

## Service Facade

**File:** `src/feptm/timesheets/project_service.py`

```python
def get_project_card(self, folder_id: str) -> dict:
    return self._projects.get_project_card(folder_id)
```

Thin delegation. No business logic.

---

## API Handler

**File:** `src/feptm/api/v1/projects.py`

```python
# @req FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001
@router.get("/{drive_folder_id}/", response_model=ProjectCardResponse)
async def get_project_card(drive_folder_id: str) -> ProjectCardResponse:
```

Logic:
1. `service: TimesheetProjectService = get_timesheet_project_service()`
2. `card_data = service.get_project_card(drive_folder_id)`
3. Build `ProjectCardResponse` from `card_data` dict
4. Catch `ProjectFolderNotFoundError` → HTTP 404, detail="Project folder not found."
5. Catch `ProjectSpreadsheetNotFoundError` → HTTP 404, detail=f"Project spreadsheet not found: {e.expected_name}."
6. Catch generic `Exception` → HTTP 500, detail=f"Failed to load project card: {e}"

### Tables dict assembly

```python
tables = {
    "project_info": ProjectCardTable(
        label="Project info / Team",
        spreadsheet_id=card_data["info_spreadsheet_id"],
        url=UrlPattern.SPREADSHEET.format(spreadsheet_id=card_data["info_spreadsheet_id"]),
    ),
    "general_expenses": ProjectCardTable(
        label="General Expenses",
        spreadsheet_id=card_data["report_spreadsheet_id"],
        url=UrlPattern.SPREADSHEET.format(spreadsheet_id=card_data["report_spreadsheet_id"]),
    ),
    "payment_distribution": ProjectCardTable(
        label="Payment Distribution",
        spreadsheet_id=card_data["calculations_spreadsheet_id"],
        url=UrlPattern.SPREADSHEET.format(spreadsheet_id=card_data["calculations_spreadsheet_id"]),
    ),
}
```

### Timesheets list assembly

```python
timesheets = [
    ProjectCardTimesheet(
        name=ts["name"],
        spreadsheet_id=ts["id"],
        url=UrlPattern.SPREADSHEET.format(spreadsheet_id=ts["id"]),
    )
    for ts in card_data["timesheets"]
]
```

---

## Implementation Order

1. **Models** — `ProjectCardTable`, `ProjectCardTimesheet`, `ProjectCardResponse` in `models/project.py`; export from `models/__init__.py`
2. **Exceptions** — `ProjectFolderNotFoundError`, `ProjectSpreadsheetNotFoundError` in `core/exceptions.py`
3. **GoogleSheetsService** — `list_drive_spreadsheets()` method
4. **ProjectStorageProtocol** — add `get_project_card()` signature
5. **ProjectStorage** — implement `get_project_card()`
6. **TimesheetProjectService** — add `get_project_card()` facade method
7. **API handler** — `GET /{drive_folder_id}/` in `api/v1/projects.py`
8. **Tests** — 7 tests per spec (see below)
9. **Verification** — `make lint && make typecheck && make test`

---

## Tests

**File:** `tests/api/v1/test_projects.py`

All tests use `@patch("feptm.api.v1.projects.get_timesheet_project_service")` pattern.

### Test cases

| # | Name | Setup | Assert |
|---|------|-------|--------|
| 1 | `test_get_project_card_success_no_timesheets` | Mock returns 3 files, 0 timesheets | 200, timesheets=[], project_id=info id, 3 table URLs |
| 2 | `test_get_project_card_timesheets_sorted_case_insensitive` | 2 timesheets: "B...", "a..." | Order: a..., B... |
| 3 | `test_get_project_card_timesheet_not_in_team` | Timesheet for specialist not in Team | Still in timesheets list |
| 4 | `test_get_project_card_folder_not_found` | Service raises `ProjectFolderNotFoundError` | 404, detail="Project folder not found." |
| 5 | `test_get_project_card_missing_spreadsheet` | Service raises `ProjectSpreadsheetNotFoundError` | 404, detail contains expected file name |
| 6 | `test_get_project_card_no_side_effects` | Mock service; verify create/sync/close not called | `mock_service.create_project.assert_not_called()` etc. |
| 7 | `test_get_project_card_project_id_matches_sync` | Mock returns known info_spreadsheet_id | `response.json()["project_id"]` == that ID |

---

## Security Considerations

- No auth (consistent with existing GET /api/projects/)
- No secrets in logs or error messages (AR-SECRETS-001)
- Read-only: no writes, no side effects
- Input validation: `drive_folder_id` is a path param (str), no injection risk

---

## Config Changes

None. No new env vars. Uses existing `GOOGLE_PROJECTS_FOLDER_ID` implicitly (folder ID comes from path param, not config).

---

## Traceability

| Requirement | Handler | Storage | Test |
|-------------|---------|---------|------|
| FR-PROJECT-001 | `get_project_card` | `ProjectStorage.get_project_card` | test 1, 4, 5 |
| FR-CREATE-001 | `get_project_card` | `ProjectStorage.get_project_card` | test 1 |
| FR-SHEET-001 | `get_project_card` | `ProjectStorage.get_project_card` | test 1, 2, 3, 6, 7 |

---

## Audit (last task)

Full repo audit — zero ERR, zero WARN in touched files:
- `src/feptm/models/project.py`
- `src/feptm/models/__init__.py`
- `src/feptm/core/exceptions.py`
- `src/feptm/services/google_sheets_service.py`
- `src/feptm/storage/protocols.py`
- `src/feptm/storage/project_storage.py`
- `src/feptm/timesheets/project_service.py`
- `src/feptm/api/v1/projects.py`
- `tests/api/v1/test_projects.py`
