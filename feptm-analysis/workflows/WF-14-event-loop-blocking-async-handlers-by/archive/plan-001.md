# Technical Plan: Fix Event-Loop Blocking in Async Handlers

## Workflow: WF-14-event-loop-blocking-async-handlers-by

**FRs:** FR-SYNC-001, FR-SYNC-RATES-001, FR-PAYMENT-001, FR-PROJECT-001  
**ARs:** AR-ARCH-006 (Non-Blocking Request Handling), AR-ARCH-007 (Service Lifecycle and Resource Management)  
**Repos:** feptm-server, feptm-analysis  
**Baseline policy:** fix_all (11 ERR, 1 WARN)

---

## 1. Architecture Overview

### Problem

FastAPI runs on a single-threaded asyncio event loop per worker. All API handlers are `async def` but call synchronous Google API methods (googleapiclient `.execute()`, `time.sleep()`). This blocks the event loop, starving all concurrent requests.

**Symptoms:**
- UI hangs on "Updating team..." / "Updating rates..." / "Closing..."
- Next.js proxy drops connection (ECONNRESET) during long sync
- GET project card fails with "Failed to load the project card" while sync runs
- Single uvicorn worker cannot serve concurrent requests

### Solution

1. **Offload blocking calls** — wrap synchronous service methods in `asyncio.to_thread()` at the handler boundary
2. **Singleton GoogleSheetsService** — cache instance per worker process, not per request
3. **HTTP timeout** — bound Google API calls with configurable timeout
4. **Multiple workers** — run uvicorn with configurable worker count (except in debug mode)

### Data Flow (After)

```
[Client] → [nginx] → [Next.js proxy] → [uvicorn worker 1..N]
                                              ↓
                                        async handler
                                              ↓
                                        asyncio.to_thread()
                                              ↓
                                        worker thread
                                              ↓
                                        TimesheetProjectService
                                              ↓
                                        GoogleSheetsService (singleton)
                                              ↓
                                        Google Sheets API (with timeout)
```

---

## 2. REST API / OpenAPI Schema Changes

**No endpoint changes.** All existing endpoints retain their paths, methods, request/response schemas.

| Endpoint | Method | Change |
|----------|--------|--------|
| `/api/projects/` | GET | Non-blocking (asyncio.to_thread) |
| `/api/projects/create` | POST | Non-blocking |
| `/api/projects/sync` | POST | Non-blocking |
| `/api/projects/sync-rates` | POST | Non-blocking |
| `/api/projects/{drive_folder_id}/` | GET | Non-blocking |
| `/api/periods` | PUT | Non-blocking |

**Error responses:** All handlers already return structured JSON on failure (HTTPException 500). No schema change — just ensure exceptions are caught and returned, not dropped.

---

## 3. Storage Changes

**No storage layer changes.** Storage classes (ProjectStorage, SpecialistStorage, ConfigStorage) remain synchronous. The blocking calls are offloaded at the handler boundary via `asyncio.to_thread()`.

---

## 4. Implementation Details

### 4.1 Config: Add WORKERS and GOOGLE_API_TIMEOUT

**File:** `feptm-server/src/feptm/core/config.py`

Add two settings:

```python
# API settings
WORKERS: int = 4

# Google API settings
GOOGLE_API_TIMEOUT: int = 30
```

**Config prefix:** `FEPTM_FEPTM_SERVER__`  
**Env vars:** `FEPTM_FEPTM_SERVER__WORKERS`, `FEPTM_FEPTM_SERVER__GOOGLE_API_TIMEOUT`

---

### 4.2 Singleton GoogleSheetsService

**File:** `feptm-server/src/feptm/dependencies.py`

Replace per-request construction with module-level cache:

```python
_google_sheets_service: GoogleSheetsService | None = None

def get_google_sheets_service() -> GoogleSheetsService:
    global _google_sheets_service
    if _google_sheets_service is None:
        _google_sheets_service = GoogleSheetsService()
    return _google_sheets_service
```

**Rationale:** One OAuth flow + API build per worker process, not per request. Reduces latency and OAuth rate-limit risk.

---

### 4.3 HTTP Timeout on Google API Build

**File:** `feptm-server/src/feptm/services/google_sheets_service.py`

Modify `initialize()` to use httplib2.Http with timeout:

```python
import httplib2

def initialize(self) -> bool:
    try:
        creds = self._get_credentials()
        if not creds:
            log.error("Failed to obtain OAuth credentials")
            return False

        http = httplib2.Http(timeout=settings.GOOGLE_API_TIMEOUT)
        self.drive_service = build("drive", "v3", credentials=creds, http=http)
        self.sheets_service = build("sheets", "v4", credentials=creds, http=http)

        log.info("Google Drive and Sheets services initialized successfully")
        return True
    except Exception as e:
        log.error(f"Error initializing Google services: {e!s}")
        self.drive_service = None
        self.sheets_service = None
        return False
```

**Effect:** All `.execute()` calls inherit the 30s timeout. Network hangs no longer block indefinitely.

---

### 4.4 Uvicorn Workers Configuration

**File:** `feptm-server/bin/run_api.py`

Add workers parameter:

```python
uvicorn.run(
    "feptm.main:app",
    host=settings.HOST,
    port=settings.PORT,
    reload=settings.DEBUG,
    workers=1 if settings.DEBUG else settings.WORKERS,
)
```

**Rationale:** `reload=True` is incompatible with `workers > 1`. In debug mode, force single worker. In production, use configured count.

---

### 4.5 Wrap Blocking Calls in asyncio.to_thread

**File:** `feptm-server/src/feptm/api/v1/projects.py`

Add import:
```python
import asyncio
```

Wrap all service calls:

| Line | Before | After |
|------|--------|-------|
| 49 | `service.list_projects(...)` | `await asyncio.to_thread(service.list_projects, ...)` |
| 87 | `service.create_project(...)` | `await asyncio.to_thread(service.create_project, ...)` |
| 144 | `service.sync_project_specialists(...)` | `await asyncio.to_thread(service.sync_project_specialists, ...)` |
| 169 | `service.sync_project_rates(...)` | `await asyncio.to_thread(service.sync_project_rates, ...)` |
| 191 | `service.get_project_card(...)` | `await asyncio.to_thread(service.get_project_card, ...)` |

**Example transformation:**

```python
# Before
service: TimesheetProjectService = get_timesheet_project_service()
folders = service.list_projects(settings.GOOGLE_PROJECTS_FOLDER_ID)

# After
service: TimesheetProjectService = get_timesheet_project_service()
folders = await asyncio.to_thread(
    service.list_projects, settings.GOOGLE_PROJECTS_FOLDER_ID
)
```

---

**File:** `feptm-server/src/feptm/api/v1/periods.py`

Add import:
```python
import asyncio
```

Wrap service call:

```python
# Before
service: TimesheetProjectService = get_timesheet_project_service()
return service.close_period(project_id=..., period_name=...)

# After
service: TimesheetProjectService = get_timesheet_project_service()
return await asyncio.to_thread(
    service.close_period,
    project_id=request.project_id,
    period_name=request.period_name,
)
```

---

### 4.6 Error Handling

All handlers already have try/except blocks that catch `Exception` and raise `HTTPException(status_code=500, detail=...)`. No changes needed — the existing pattern produces structured JSON errors.

**Verification:** After wrapping with `asyncio.to_thread()`, exceptions raised in the worker thread propagate to the handler's try/except, so the client receives a JSON error instead of a dropped connection.

---

## 5. Security Considerations

- **No new secrets introduced.** Google OAuth credentials remain in `credentials.json` / token file.
- **No logging of secrets.** Existing `AR-SECRETS-001` compliance maintained.
- **Timeout prevents DoS.** `GOOGLE_API_TIMEOUT` bounds request latency, preventing indefinite hangs.

---

## 6. Config Changes Summary

| Setting | Type | Default | Env Var |
|---------|------|---------|---------|
| `WORKERS` | int | 4 | `FEPTM_FEPTM_SERVER__WORKERS` |
| `GOOGLE_API_TIMEOUT` | int | 30 | `FEPTM_FEPTM_SERVER__GOOGLE_API_TIMEOUT` |

---

## 7. Testing Strategy

- **Manual:** Start server with `WORKERS=2`, trigger sync/rates/close in parallel with GET card — verify no blocking.
- **Lint/Typecheck:** `make lint && make typecheck` must pass.
- **Audit:** `sdd-cli.sh verify --wf-dir ... --phase implement` must show zero new violations.

---

## 8. Rollout

1. Deploy with `WORKERS=1` (safe fallback) — verify asyncio.to_thread works.
2. Increase to `WORKERS=4` — verify concurrent requests succeed.
3. Monitor Google API quota usage — singleton reduces OAuth calls.

---

## 9. Affected Files

| File | Change Type |
|------|-------------|
| `feptm-server/src/feptm/core/config.py` | Add settings |
| `feptm-server/src/feptm/dependencies.py` | Singleton cache |
| `feptm-server/src/feptm/services/google_sheets_service.py` | HTTP timeout |
| `feptm-server/bin/run_api.py` | Workers config |
| `feptm-server/src/feptm/api/v1/projects.py` | asyncio.to_thread |
| `feptm-server/src/feptm/api/v1/periods.py` | asyncio.to_thread |
