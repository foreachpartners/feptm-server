# Technical Plan: GET /api/projects (FR-PROJECT-001)

## Architecture Overview

**Affected repo:** feptm-server (Python/FastAPI)

**Data flow:**
```
Client → GET /api/projects → API handler → TimesheetProjectService
    → ProjectStorage → GoogleSheetsService.list_drive_folders()
    → Google Drive API (list folders in parent)
    → Sort by name (case-insensitive)
    → Return ProjectListResponse
```

**No database.** Google Drive is the source of truth. The parent folder `GOOGLE_PROJECTS_FOLDER_ID` contains only project folders — no validation needed at list time.

## REST API Changes

### New endpoint

| Method | Path | Handler | Req | Description |
|--------|------|---------|-----|-------------|
| `GET` | `/api/projects` | `list_projects()` | `@req FR-PROJECT-001` | List all projects |

**Response (200):**
```json
{
  "projects": [
    {"name": "Alpha Corp", "drive_folder_id": "1abc..."},
    {"name": "Beta Inc", "drive_folder_id": "2def..."}
  ]
}
```

**Empty list (200):**
```json
{"projects": []}
```

**Error (500):** Missing config or Drive API failure.

**No pagination.** Matches existing endpoint patterns.

**No auth.** FR-PROJECT-001 specifies "no sign-in and no roles."

## Storage Changes

### GoogleSheetsService — new method

**File:** `src/feptm/services/google_sheets_service.py`

Add `list_drive_folders(parent_folder_id: str) -> list[dict[str, str]]`:
- Query: `mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false`
- Fields: `nextPageToken, files(id,name)`
- Handle pagination via `nextPageToken` loop
- Return `[{"id": "...", "name": "..."}, ...]`

### ProjectStorageProtocol — new signature

**File:** `src/feptm/storage/protocols.py`

Add to `ProjectStorageProtocol`:
```python
def list_projects(self, parent_folder_id: str) -> list[dict[str, str]]:
    """List project folders from Google Drive."""
    ...
```

### ProjectStorage — new method

**File:** `src/feptm/storage/project_storage.py`

Add `list_projects(parent_folder_id: str) -> list[dict[str, str]]`:
- Delegate to `self._sheets.list_drive_folders(parent_folder_id)`

## Service Layer

### TimesheetProjectService — new method

**File:** `src/feptm/timesheets/project_service.py`

Add `list_projects(parent_folder_id: str) -> list[dict[str, str]]`:
- Delegate to `self._projects.list_projects(parent_folder_id)`
- Sort by `name` case-insensitive: `sorted(result, key=lambda x: x["name"].lower())`

## API Handler

### New route

**File:** `src/feptm/api/v1/projects.py`

Add `GET /` handler:
```python
# @req FR-PROJECT-001
@router.get("/", response_model=ProjectListResponse)
async def list_projects() -> ProjectListResponse:
```

**Logic:**
1. Check `settings.GOOGLE_PROJECTS_FOLDER_ID` — if missing, raise `HTTPException(500)`
2. Call `service.list_projects(parent_folder_id)`
3. Map to `ProjectListResponse(projects=[...])`
4. On exception: `HTTPException(500, detail=f"Failed to load the project list: {e}")`

## Model Changes

### New response models

**File:** `src/feptm/models/project.py`

```python
class ProjectListItem(BaseModel):
    name: str
    drive_folder_id: str

class ProjectListResponse(BaseModel):
    projects: list[ProjectListItem]
```

**Export:** Add to `src/feptm/models/__init__.py` and `__all__`.

## Config Changes

No new config fields. Uses existing `GOOGLE_PROJECTS_FOLDER_ID`.

## Security Considerations

- No secrets in logs or error messages
- Drive API errors should not leak internal details to client
- Parent folder ID is server config, not user input (no injection risk)

## Implementation Order

1. `GoogleSheetsService.list_drive_folders()` — Drive API integration
2. `ProjectStorageProtocol.list_projects()` — protocol signature
3. `ProjectStorage.list_projects()` — storage impl
4. `TimesheetProjectService.list_projects()` — service facade with sorting
5. `ProjectListItem`, `ProjectListResponse` — models
6. `GET /api/projects` handler — API layer
7. Tests — unit tests for all layers

## Acceptance Criteria Mapping (FR-PROJECT-001)

| Criterion | Implementation |
|-----------|----------------|
| "single server list request" | Single `drive.files().list()` call with pagination |
| "sorted alphabetically by project name, case-insensitive" | `sorted(..., key=lambda x: x["name"].lower())` in service |
| "empty list response is not a failure" | Return 200 `{"projects": []}` |
| "failed list request shows error" | 500 with detail message |
