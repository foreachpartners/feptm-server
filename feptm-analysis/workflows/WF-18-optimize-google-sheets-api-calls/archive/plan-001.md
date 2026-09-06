# Technical Plan: Optimize Google Sheets API Calls

## Architecture Overview

**Affected repo:** feptm-server

**Data flow:**
```
API Handler (asyncio.to_thread)
  → TimesheetProjectService (facade)
    → ProjectStorage / SpecialistStorage (storage layer)
      → GoogleSheetsService (Google API wrapper)
```

**Current performance:** ~53s for 10 specialists, ~120+ API calls

**Target performance:** ~10-15s for 10 specialists, ~30-40 API calls

---

## Phase 1: Quick Fixes (Low Risk, ~5-8s saved)

### 1.1 Remove Duplicate Team Read

**File:** `src/feptm/timesheets/project_service.py:156,171`

**Problem:** `sync_project_rates` calls `list_from_sheet` twice in succession.

**Fix:** Delete line 171. Reuse result from line 156.

**Impact:** Eliminates 1 redundant `values.get` call per sync.

---

### 1.2 Skip A1 Write If Formula Matches

**File:** `src/feptm/storage/project_storage.py:256-275`

**Problem:** `add_specialist_to_report` always writes A1, even if tab exists and formula is identical.

**Fix:** 
1. After checking tab exists, read A1 with `FORMULA` render option
2. Compare with `import_formula`
3. Skip `update_range` if they match

**Implementation:**
```python
def add_specialist_to_report(self, spreadsheet_id, specialist, import_formula):
    tab_name = specialist.name
    existing = self._list_sheet_titles(spreadsheet_id)
    
    if tab_name not in existing:
        self._sheets.batch_update(
            spreadsheet_id=spreadsheet_id,
            requests=[{"addSheet": {"properties": {"title": tab_name}}}],
        )
        # New tab — write formula
        self._sheets.update_range(...)
    else:
        # Tab exists — check if A1 already has correct formula
        current = self._read_cell_formula(spreadsheet_id, tab_name, "A1")
        if current != import_formula:
            self._sheets.update_range(...)
```

**New helper:** `_read_cell_formula(spreadsheet_id, sheet_name, cell)` in `ProjectStorage`

**Impact:** Eliminates ~10 `update_range` calls per sync (for existing tabs).

---

### 1.3 Pre-Load All Formulas on First Cache Miss

**File:** `src/feptm/storage/config_storage.py:19-61`

**Problem:** `get_formula` calls `get_sheet_by_name` on every cache miss, then returns after first match without loading all formulas.

**Fix:** On first miss, read `Formulas!A:C` once, populate **all** entries into `_cache`, then lookup.

**Implementation:**
```python
def get_formula(self, formula_name):
    if formula_name in self._cache:
        return self._cache[formula_name]
    
    # Cache miss — load ALL formulas
    if not self._all_formulas_loaded:
        self._load_all_formulas()
        self._all_formulas_loaded = True
    
    if formula_name not in self._cache:
        raise Exception(f"Formula '{formula_name}' not found")
    
    return self._cache[formula_name]

def _load_all_formulas(self):
    sheet = self._sheets.get_sheet_by_name(...)
    result = self._sheets.sheets_service.spreadsheets().values().get(...).execute()
    values = result.get("values", [])
    for row in values[1:]:
        if len(row) >= 2:
            name = row[0].strip()
            formula = row[1].strip()
            if name and formula:
                self._cache[name] = formula
```

**Impact:** First call loads all formulas (~5-10). Subsequent calls are pure dict lookups (0 API calls).

---

### 1.4 Remove time.sleep(0.25)

**File:** `src/feptm/timesheets/project_service.py:144`

**Problem:** `time.sleep(0.25)` in per-specialist loop adds 2.5s dead time for 10 specialists.

**Fix:** Remove the sleep. The retry logic in `GoogleSheetsService._retry_api_call` already handles 429s with exponential backoff.

**Impact:** Saves 2.5s per sync.

---

## Phase 2: Metadata Cache (Medium Risk, ~10-15s saved)

### 2.1 Add Contextvar Metadata Cache

**File:** `src/feptm/services/google_sheets_service.py`

**Problem:** `get_sheet_by_name` calls `spreadsheets.get` every time. For 10 specialists, this is ~20 calls (report + calculations).

**Fix:** Add request-scoped metadata cache using `contextvars.ContextVar`.

**Implementation:**
```python
import contextvars

# Module-level contextvar
_metadata_cache: ContextVar[dict[str, dict]] = contextvars.ContextVar(
    '_metadata_cache', default={}
)

class GoogleSheetsService:
    def get_all_sheets(self, spreadsheet_id: str) -> list[dict]:
        """Return all sheets for a spreadsheet, using cache if available."""
        cache = _metadata_cache.get({})
        if spreadsheet_id in cache:
            return cache[spreadsheet_id]["sheets"]
        
        # Fetch from API
        _, sheets_service = self._get_services()
        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(title,sheetId))"
        ).execute()
        
        # Cache it
        cache[spreadsheet_id] = spreadsheet
        _metadata_cache.set(cache)
        
        return spreadsheet.get("sheets", [])
    
    def get_sheet_by_name(self, spreadsheet_id, sheet_name):
        """Use cached metadata instead of fetching every time."""
        sheets = self.get_all_sheets(spreadsheet_id)
        for sheet in sheets:
            if sheet.get("properties", {}).get("title") == sheet_name:
                return sheet
        return None
    
    def invalidate_metadata_cache(self, spreadsheet_id: str):
        """Remove spreadsheet from cache after mutations."""
        cache = _metadata_cache.get({})
        if spreadsheet_id in cache:
            del cache[spreadsheet_id]
            _metadata_cache.set(cache)
```

**Key points:**
- `contextvars` ensures cache is request-scoped (no leakage between requests)
- `fields="sheets(properties(title,sheetId))"` reduces payload size
- Cache is invalidated after mutations (see 2.4)

**Impact:** Reduces ~40 `spreadsheets.get` calls to ~5 (one per unique spreadsheet per request).

---

### 2.2 Update get_sheet_by_name to Use Cache

**File:** `src/feptm/services/google_sheets_service.py:216-263`

**Fix:** Replace direct `spreadsheets.get` with `get_all_sheets()`.

**Already done in 2.1.**

---

### 2.3 Update All Direct spreadsheets.get Calls

**Files:**
- `src/feptm/storage/project_storage.py:345` (`_list_sheet_titles`)
- `src/feptm/storage/project_storage.py:448` (`_copy_row_formatting`)
- `src/feptm/storage/project_storage.py:689` (`delete_sheet`)
- `src/feptm/storage/project_storage.py:861` (`protect_archived_sheet`)
- `src/feptm/storage/project_storage.py:520` (`close_period_in_timesheet`)

**Fix:** Replace `self._sheets.sheets_service.spreadsheets().get(...).execute()` with `self._sheets.get_all_sheets(spreadsheet_id)`.

**Example:**
```python
# Before
spreadsheet = self._sheets.sheets_service.spreadsheets().get(
    spreadsheetId=spreadsheet_id
).execute()
sheets_list = spreadsheet.get("sheets", [])

# After
sheets_list = self._sheets.get_all_sheets(spreadsheet_id)
```

**Impact:** All metadata reads use cache.

---

### 2.4 Add Cache Invalidation After Mutations

**Files:** `src/feptm/storage/project_storage.py`

**Problem:** After `addSheet`, `insertDimension`, `duplicateSheet`, `deleteSheet`, the cached metadata is stale.

**Fix:** Call `self._sheets.invalidate_metadata_cache(spreadsheet_id)` after each mutation.

**Locations:**
- `add_specialist_to_report:265` (after `addSheet`)
- `_insert_and_update_row:398` (after `insertDimension`)
- `archive_current_period:614` (after `duplicateSheet`)
- `delete_sheet:703` (after `deleteSheet`)

**Implementation:**
```python
def add_specialist_to_report(self, spreadsheet_id, specialist, import_formula):
    # ... addSheet ...
    self._sheets.invalidate_metadata_cache(spreadsheet_id)
    # ... write A1 ...
```

**Impact:** Ensures cache consistency.

---

### 2.5 Pass sheet_id to _copy_row_formatting

**File:** `src/feptm/storage/project_storage.py:442-506`

**Problem:** `_copy_row_formatting` re-resolves `sheet_id` from metadata (line 448-457), even though caller already has it.

**Fix:** Accept `sheet_id: int` as parameter.

**Implementation:**
```python
def _copy_row_formatting(
    self, spreadsheet_id, sheet_name, sheet_id, source_row, target_row
):
    # Remove lines 448-457 (sheet_id lookup)
    # Use sheet_id parameter directly
    ...
```

**Caller update:**
```python
# In _insert_and_update_row:420
self._copy_row_formatting(
    spreadsheet_id, sheet_name, sheet_id, template_row, target_row
)
```

**Impact:** Eliminates redundant metadata lookup.

---

## Phase 3: Skip Re-Reads (Low Risk, ~3-5s saved)

### 3.1 update_timesheet_ids — Eliminate Redundant Re-Reads

**File:** `src/feptm/storage/specialist_storage.py:182-249`

**Problem:** 
- `_prepare_updates` (line 185) calls `get_sheet_data_with_headers` to get headers
- `_apply_updates` (line 208-216) calls `get_sheet_by_name` + `get_sheet_data_with_headers` again (2 API calls)

**Fix:** 
1. `_prepare_updates` returns `(updates, headers)` instead of just `updates`
2. `_apply_updates` accepts `headers` parameter, computes `timesheet_col` once
3. With metadata cache (Phase 2), `get_sheet_by_name` is free, but we still eliminate one `get_sheet_data_with_headers` call

**Implementation:**
```python
def update_timesheet_ids(self, spreadsheet_id, sheet_name, specialists):
    updates, headers = self._prepare_updates(spreadsheet_id, sheet_name, specialists)
    if not updates:
        return True
    self._apply_updates(spreadsheet_id, sheet_name, updates, headers)
    return True

def _prepare_updates(self, spreadsheet_id, sheet_name, specialists):
    values, headers = self._sheets.get_sheet_data_with_headers(...)
    # ... compute updates ...
    return updates, headers

def _apply_updates(self, spreadsheet_id, sheet_name, updates, headers):
    # Use headers parameter instead of re-reading
    timesheet_col = self._sheets.find_column_index(headers, [ColumnName.TIMESHEET.value])
    # ... build requests ...
```

**Impact:** Eliminates 1 `get_sheet_data_with_headers` call per `update_timesheet_ids`.

---

## Phase 4: Batch Writes (High Risk, ~15-20s saved)

### 4.1 New Method: sync_rates_batch

**File:** `src/feptm/storage/project_storage.py`

**Problem:** `sync_rates_to_current_period` is called per-specialist, each making 1 read + 1 write.

**Fix:** New method `sync_rates_batch(spreadsheet_id, specialists)` that:
1. Reads Current Period once (1 call)
2. For each specialist: finds row, builds `updateCells` request
3. One `batch_update` with all requests (1 call)

**Implementation:**
```python
def sync_rates_batch(self, spreadsheet_id, specialists):
    sheet_name = SheetName.CURRENT_PERIOD.value
    sheet_data = self._read_current_period(spreadsheet_id, sheet_name)
    if not sheet_data:
        return
    
    values, headers, sheet = sheet_data
    sheet_id = sheet.get("properties", {}).get("sheetId")
    
    requests = []
    for specialist in specialists:
        target_row = _find_specialist_row(values, headers, specialist.name, self._sheets)
        if target_row is None:
            continue
        
        # Build updateCells requests for this specialist
        field_updates = [
            (ColumnName.SPECIALIST.value, specialist.name),
            (ColumnName.SPECIALIST_ROLE.value, specialist.role),
            (ColumnName.HOURLY_RATE_USD.value, specialist.external_rate),
            (ColumnName.SPECIALIST_HOURLY_RATE_USD.value, specialist.internal_rate),
            (ColumnName.CLIENT_HOURLY_RATE_USD.value, specialist.external_rate),
        ]
        
        row_index = target_row - 1
        for col_name, val in field_updates:
            col_idx = self._sheets.find_column_index(headers, [col_name])
            if col_idx is None or val is None:
                continue
            
            if isinstance(val, str):
                entry = {"stringValue": val}
            else:
                entry = {"numberValue": float(val)}
            
            requests.append({
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    },
                    "rows": [{"values": [{"userEnteredValue": entry}]}],
                    "fields": "userEnteredValue",
                }
            })
    
    if requests:
        self._sheets.batch_update(spreadsheet_id, requests)
```

**Impact:** Replaces ~20 API calls (10 reads + 10 writes) with 2 calls (1 read + 1 batch write).

---

### 4.2 Restructure sync_project_rates into Phases

**File:** `src/feptm/timesheets/project_service.py:153-246`

**Current flow:**
```
for each specialist:
    add_specialist_to_report (report)
    sync_rates_to_current_period (report)
    add_specialist_to_report (calculations)
    sync_rates_to_current_period (calculations)
```

**New flow:**
```
Phase A: Read
  - list_from_sheet (1 call)
  - get_project_metadata (1-2 calls)

Phase B: Create timesheets (per new specialist, unavoidable)
  - find_file_in_folder + ensure_spreadsheet_from_template

Phase C: Write timesheet IDs
  - update_timesheet_ids (1 batch call)

Phase D: Add tabs (batched)
  - Collect specialists needing new tabs
  - One batchUpdate with N addSheet requests for report
  - One batchUpdate with N addSheet requests for calculations

Phase E: Write A1 formulas (batched)
  - One batchUpdate per spreadsheet with all updateCells for A1

Phase F: Sync rates (batched)
  - sync_rates_batch for report (1 call)
  - sync_rates_batch for calculations (1 call)
```

**Implementation:**
```python
def sync_project_rates(self, project_id):
    # Phase A: Read
    specialists, _ = self._specialists.list_from_sheet(project_id)
    if not specialists:
        return [], 0
    
    project = self._projects.get_project_metadata(project_id)
    # ... validation ...
    
    # Phase B: Create timesheets
    created_count = 0
    for sp in valid_specialists:
        if not sp.timesheet:
            self._specialists.create_timesheet(sp, context, self._timesheet_template_id)
            created_count += 1
    
    # Phase C: Write timesheet IDs
    if created_count > 0:
        self._specialists.update_timesheet_ids(project_id, "Team", valid_specialists)
    
    # Phase D: Add tabs (batched)
    new_tabs_report = []
    new_tabs_calc = []
    for sp in valid_specialists:
        if not sp.timesheet:
            continue
        if project.report_spreadsheet_id:
            if not self._tab_exists(project.report_spreadsheet_id, sp.name):
                new_tabs_report.append(sp)
        if project.calculations_spreadsheet_id:
            if not self._tab_exists(project.calculations_spreadsheet_id, sp.name):
                new_tabs_calc.append(sp)
    
    if new_tabs_report:
        self._projects.batch_add_sheets(project.report_spreadsheet_id, new_tabs_report)
    if new_tabs_calc:
        self._projects.batch_add_sheets(project.calculations_spreadsheet_id, new_tabs_calc)
    
    # Phase E: Write A1 formulas (batched)
    formulas_report = []
    formulas_calc = []
    for sp in valid_specialists:
        if not sp.timesheet:
            continue
        import_formula = self._formulas.get_import_timesheet_formula(sp.timesheet)
        if project.report_spreadsheet_id:
            formulas_report.append((sp.name, import_formula))
        if project.calculations_spreadsheet_id:
            formulas_calc.append((sp.name, import_formula))
    
    if formulas_report:
        self._projects.batch_write_a1_formulas(project.report_spreadsheet_id, formulas_report)
    if formulas_calc:
        self._projects.batch_write_a1_formulas(project.calculations_spreadsheet_id, formulas_calc)
    
    # Phase F: Sync rates (batched)
    if project.report_spreadsheet_id:
        self._projects.sync_rates_batch(project.report_spreadsheet_id, valid_specialists)
    if project.calculations_spreadsheet_id:
        self._projects.sync_rates_batch(project.calculations_spreadsheet_id, valid_specialists)
    
    return specialists, len(valid_specialists)
```

**New methods in ProjectStorage:**
- `batch_add_sheets(spreadsheet_id, specialists)` — one `batchUpdate` with N `addSheet`
- `batch_write_a1_formulas(spreadsheet_id, formulas)` — one `batchUpdate` with N `updateCells`
- `_tab_exists(spreadsheet_id, tab_name)` — uses cached metadata

**Impact:** Replaces ~40 API calls with ~10 calls.

---

### 4.3 Same Pattern for sync_project_specialists

**File:** `src/feptm/timesheets/project_service.py:90-151`

**Current flow:**
```
for each specialist:
    add_specialist_to_report (report)
    update_current_period (report)
    add_specialist_to_report (calculations)
    update_current_period (calculations)
```

**New flow:** Similar to `sync_project_rates`, but `update_current_period` involves row insertion (sequential), so it remains per-specialist.

**Optimization:** Batch tab creation and A1 formula writes.

---

## Phase 5: Additional Optimizations (Medium Risk, ~3-5s saved)

### 5.1 Drive: Batch find_file_in_folder

**File:** `src/feptm/storage/specialist_storage.py:35-57`

**Problem:** `create_timesheet` calls `find_file_in_folder` per specialist.

**Fix:** One `list_drive_spreadsheets(folder_id)` at the start, match by name in-memory.

**Implementation:**
```python
def sync_specialists(self, spreadsheet_id, context, sheet_name="Team"):
    specialists, existing_count = self._storage.list_from_sheet(spreadsheet_id, sheet_name)
    
    # Pre-load all spreadsheets in folder
    existing_files = self._sheets.list_drive_spreadsheets(context.folder_id)
    existing_map = {f["name"]: f["id"] for f in existing_files}
    
    for sp in specialists:
        if not sp.timesheet:
            title = utils.generate_timesheet_title(sp.name, context.project_name)
            if title in existing_map:
                sp.timesheet = existing_map[title]
            else:
                # Create new timesheet
                ...
```

**Impact:** Replaces ~10 `files.list` calls with 1 call.

---

### 5.2 get_project_metadata — Combine Metadata + Values

**File:** `src/feptm/storage/project_storage.py:194-254`

**Problem:** Calls `get_sheet_by_name` (→ `spreadsheets.get`) then `values.get`.

**Fix:** Use `spreadsheets.get(includeData=True, ranges=[...])` to fetch metadata + values in one call.

**Implementation:**
```python
def get_project_metadata(self, project_id):
    _, sheets_service = self._sheets._get_services()
    
    result = sheets_service.spreadsheets().get(
        spreadsheetId=project_id,
        includeData=True,
        ranges=["Project info!A1:B20"],
        fields="sheets(properties(title,sheetId)),sheets(data(rowData(values(formattedValue))))"
    ).execute()
    
    # Extract sheet metadata
    sheets = result.get("sheets", [])
    sheet = next((s for s in sheets if s["properties"]["title"] == "Project info"), None)
    
    # Extract values
    values = []
    if sheet and "data" in sheet:
        for row_data in sheet["data"][0].get("rowData", []):
            row = [cell.get("formattedValue", "") for cell in row_data.get("values", [])]
            values.append(row)
    
    # ... parse values ...
```

**Impact:** Replaces 2 API calls with 1 call.

---

### 5.3 close_period Flow Optimization

**File:** `src/feptm/timesheets/project_service.py:248-368`

**Problem:** Multiple `_list_sheet_titles` and `_read_current_period` calls across `is_period_closed`, `archive_current_period`, `remove_stale_specialists`.

**Fix:** Metadata cache (Phase 2) eliminates most of these automatically. No additional changes needed.

---

## Security Considerations

- No secrets are logged or exposed in error messages
- Metadata cache is request-scoped (contextvars) — no leakage between requests
- All Google API calls use existing retry logic with exponential backoff

---

## Config Changes

No new config values required. Existing settings are sufficient:
- `GOOGLE_API_TIMEOUT` — already used for HTTP timeout
- `GOOGLE_CONFIG_SHEET_ID` — already used for formula retrieval

---

## Implementation Order

1. Phase 1 (quick fixes) — low risk, immediate wins
2. Phase 2 (metadata cache) — medium risk, significant wins
3. Phase 3 (skip re-reads) — low risk, moderate wins
4. Phase 4 (batch writes) — high risk, largest wins
5. Phase 5 (additional) — medium risk, moderate wins

---

## Testing Strategy

- Unit tests for each new method (`batch_add_sheets`, `sync_rates_batch`, etc.)
- Integration tests for `sync_project_rates` and `sync_project_specialists` with mocked Google API
- Verify API call count reduction (from ~120 to ~30-40 for 10 specialists)
- Verify no functional regression (same output, fewer calls)

---

## Success Criteria

- `sync_project_rates` for 10 specialists: <15s (from ~53s)
- API call count: <40 calls (from ~120)
- All existing tests pass
- Zero new lint/typecheck violations
