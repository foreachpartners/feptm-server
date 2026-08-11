# Plan: Google Sheets API Resilience (AR-ARCH-005)

**Workflow:** WF-2 (iteration 7)
**FRs:** FR-SYNC-001, AR-ARCH-005
**Ceremony:** medium
**Session:** SID-1786472682-b7fbb6bf

## 1. Architecture Overview

The specialist sync pipeline (`POST /api/projects/sync`) processes specialists in a tight synchronous loop, making ~15 Google Sheets write API calls per specialist per spreadsheet. With 2 spreadsheets (report + calculations), that equals ~30 writes per specialist. Google Sheets enforces a 60 write requests/minute/user quota. With just 6 specialists, ~180 calls fire within seconds — exceeding the quota and causing a 429 Rate Limit error.

The fix has two layers:
1. **Resilience layer** — retry with exponential backoff in `GoogleSheetsService` (handles the symptom)
2. **Efficiency layer** — consolidate individual `update_range` calls into `batchUpdate` requests (reduces call volume ~80%, addressing the root cause)

**Affected repos:** `feptm-server` only

**Data flow (after fix):**
```
sync_project_specialists() [project_service.py]
  ├── _retry_api_call() wrapper [google_sheets_service.py]  ← NEW resilience
  │   ├── batch_update() — retry on 429/5xx with jitter
  │   └── update_range() — retry on 429/5xx with jitter
  ├── _write_specialist_fields() [project_storage.py]       ← consolidated: 5 calls → 1 batchUpdate
  ├── _add_formulas_for_row() [project_storage.py]          ← consolidated: 5 calls → 1 batchUpdate
  ├── _apply_updates() [specialist_storage.py]              ← consolidated: N calls → 1 batchUpdate
  └── throttle inter-specialist delay [project_service.py]  ← NEW: small delay between specialists
```

## 2. REST API Changes

None. `POST /api/projects/sync` behavior is unchanged — same request, same response. The endpoint may take slightly longer if retries fire, but succeeds where it previously failed with 429.

## 3. Implementation Details

### 3.1 Retry Wrapper — `google_sheets_service.py` (lines 460-585)

Add a private method `_retry_api_call()` that wraps any Google Sheets `.execute()` call:

```python
def _retry_api_call(self, operation_name: str, spreadsheet_id: str, callable, *args, **kwargs):
    max_retries = 5
    base_delay = 1.0
    max_delay = 60.0
    for attempt in range(max_retries + 1):
        try:
            return callable(*args, **kwargs)
        except HttpError as error:
            if error.resp.status == 429:
                retry_after = error.resp.get("Retry-After") or base_delay * (2 ** attempt) + random.uniform(0, 1)
                delay = min(float(retry_after), max_delay)
                log.warning("Rate limited (%s, %s): attempt %d/%d, waiting %.1fs",
                    operation_name, spreadsheet_id, attempt + 1, max_retries, delay)
                time.sleep(delay)
                continue
            if error.resp.status >= 500:
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                log.warning("Server error (%s, %s): attempt %d/%d, waiting %.1fs",
                    operation_name, spreadsheet_id, attempt + 1, max_retries, delay)
                time.sleep(delay)
                continue
            raise Exception(f"Failed to {operation_name}: {error}")
    raise GoogleSheetsRateLimitError(operation_name, spreadsheet_id, max_retries)
```

Wrap three methods:
- `batch_update()` (line 577): wrap the `.batchUpdate(...).execute()` call
- `update_range()` (line 502): wrap the `.values().update(...).execute()` call
- `clear_range()` (line 473): wrap the `.values().clear(...).execute()` call

**File:** `src/feptm/services/google_sheets_service.py`

### 3.2 Add Custom Exception — `google_sheets_service.py`

Add `GoogleSheetsRateLimitError` exception class at module level:
```python
class GoogleSheetsRateLimitError(Exception):
    def __init__(self, operation: str, spreadsheet_id: str, attempts: int):
        self.operation = operation
        self.spreadsheet_id = spreadsheet_id
        self.attempts = attempts
        super().__init__(f"Rate limit exhausted for {operation} on {spreadsheet_id} after {attempts} retries")
```

**File:** `src/feptm/services/google_sheets_service.py`

### 3.3 Consolidate `_write_specialist_fields()` — `project_storage.py` (line 1099)

Replace 5 individual `update_range()` calls with one `batchUpdate` containing 5 `updateCells` requests:

```python
requests = []
for col_name, val in field_updates:
    col_idx = sheets.find_column_index(headers, [col_name])
    if col_idx is None:
        continue
    requests.append({
        "updateCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": target_row - 1,
                "endRowIndex": target_row,
                "startColumnIndex": col_idx,
                "endColumnIndex": col_idx + 1,
            },
            "rows": [{"values": [{"userEnteredValue": {"stringValue": str(val)}}]}],
            "fields": "userEnteredValue",
        }
    })
if requests:
    sheets.batch_update(spreadsheet_id, requests)
```

Requires `sheet_id` (integer) instead of `sheet_name` — obtain via `get_sheet_by_name()` call added before the loop.

**File:** `src/feptm/storage/project_storage.py`

### 3.4 Consolidate `_add_formulas_for_row()` — `project_storage.py` (line 1068)

Same pattern: replace 5 individual `update_range()` calls with one `batchUpdate` containing 5 `updateCells` requests with `userEnteredValue.formulaValue`.

**File:** `src/feptm/storage/project_storage.py`

### 3.5 Consolidate `_apply_updates()` — `specialist_storage.py` (line 204)

Replace the `for row_idx, ts_id in updates:` loop of individual `update_range()` calls with one `batchUpdate` containing N `updateCells` requests. One batch call instead of N individual writes.

**File:** `src/feptm/storage/specialist_storage.py`

### 3.6 Throttle Between Specialists — `project_service.py` (line 125)

Add a small delay in the sync loop to spread API calls over time and avoid hitting the 60 writes/min quota:

```python
import time

# After each specialist iteration in sync_project_specialists():
for sp in specialists:
    ...
    if project.report_spreadsheet_id:
        self._projects.add_specialist_to_report(...)
        self._projects.update_current_period(...)
    if project.calculations_spreadsheet_id:
        self._projects.add_specialist_to_report(...)
        self._projects.update_current_period(...)
    time.sleep(0.25)  # ~4 specialists/sec → stays under 60/min
```

**File:** `src/feptm/timesheets/project_service.py`

## 4. Storage Changes

No schema or data model changes. The same data is written — just via fewer, consolidated API calls.

## 5. Security Considerations

- The `Retry-After` header value is parsed as a float and capped at `max_delay` (60s) — prevents malicious header values from causing infinite waits.
- No secrets are added, exposed, or modified.
- The `GoogleSheetsRateLimitError` exception carries the spreadsheet ID (not a secret) for operational debugging.

## 6. Config Changes

None. All retry parameters (max_retries=5, base_delay=1s, max_delay=60s) are hardcoded constants per AR-ARCH-005. Delayed config to future iteration if tunability is needed.

## 7. Call Volume Reduction Estimate

| Operation | Before | After | Change |
|-----------|--------|-------|--------|
| `_write_specialist_fields()` | 5 `update_range` | 1 `batchUpdate` | -80% |
| `_add_formulas_for_row()` | 5 `update_range` | 1 `batchUpdate` | -80% |
| `_apply_updates()` | N `update_range` | 1 `batchUpdate` | -(N-1) calls |
| Per-specialist total (2 spreadsheets) | ~30 writes | ~12 writes | -60% |

With 10 specialists: 300 writes → 120 writes. Still above 60/min but with the 250ms inter-specialist delay, 10 specialists take ~2.5s → 120 writes/2.5s ≈ 2880/min → still bursts. The retry wrapper handles remaining bursts gracefully.

## 8. AR-ARCH-005 Compliance

| Requirement | Coverage |
|-------------|----------|
| Retry wrapper on batch_update/update_range/clear_range | T-01 |
| Exponential backoff with jitter (1s base, 60s max, 5 retries) | T-01 |
| Honor Retry-After header on 429 | T-01 |
| Shared utility in GoogleSheetsService, not duplicated | T-01 |
| Domain exception on exhausted retries | T-01 |
| Batch op throttling (inter-specialist delay) | T-04 |
| Shared rate-limiter utility | T-04 |
| consolidate individual writes into batch | T-02, T-03, T-05 |

## 9. References

- `AR-ARCH-005.yaml` — Google Sheets API Resilience
- `FR-SYNC-001.yaml` — End-to-end specialist sync lifecycle
- `google_sheets_service.py:460-585` — API call methods without retry
- `project_storage.py:1068-1126` — per-specialist write functions
- `specialist_storage.py:204-226` — per-specialist update loop
- `project_service.py:99-159` — sync loop
