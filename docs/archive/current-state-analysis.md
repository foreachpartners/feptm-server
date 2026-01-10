# Current State Analysis: FEPTM Server

## Purpose

Gap analysis between current codebase and target architecture.

## Current Directory Structure

```
src/feptm/
├── __init__.py
├── main.py
├── py.typed
│
├── core/
│   ├── __init__.py
│   ├── config.py           # Settings
│   ├── log.py              # Logging
│   └── utils.py            # Utilities
│
├── api/
│   ├── __init__.py
│   ├── router.py           # Main router
│   └── v1/
│       ├── __init__.py
│       └── projects.py     # Project endpoints
│
├── models/
│   ├── __init__.py
│   ├── context.py          # TimesheetContext
│   ├── project.py          # Project, ProjectMetaResponse, etc.
│   └── specialist.py       # Specialist
│
├── services/
│   ├── __init__.py
│   └── google_sheets_service.py  # GoogleSheetsService (691 lines)
│
└── timesheets/
    ├── __init__.py
    ├── config_service.py    # ConfigService, Enums (201 lines)
    ├── project_service.py   # TimesheetProjectService (1379 lines)
    └── specialist_service.py # SpecialistService (585 lines)
```

## Gap Analysis by Layer

### Layer: core/

**Target:** Configuration, logging, utilities, exceptions.

**Current State:**

| File | Status | Issues |
|------|--------|--------|
| `config.py` | ✅ Compliant | Uses pydantic-settings |
| `log.py` | ✅ Compliant | Proper logger setup |
| `utils.py` | ⚠️ Partial | Contains business logic (date parsing, ID extraction) |
| `exceptions.py` | ❌ Missing | No custom exception hierarchy |

**Violations:**

1. `utils.py` contains business-specific functions:
   - `extract_id_from_hyperlink_formula()` - Google Sheets specific
   - `generate_timesheet_title()` - domain logic
   - `parse_date_safely()` - should be in domain or adapter

### Layer: domain/ (Target) vs models/ + timesheets/ (Current)

**Target:** Pure domain models, domain services with injected repositories.

**Current State:**

#### Models

| Current File | Target Location | Compliance | Issues |
|--------------|-----------------|------------|--------|
| `models/project.py` | `domain/models/project.py` | ❌ | Contains Google IDs |
| `models/specialist.py` | `domain/models/specialist.py` | ❌ | Contains Google IDs |
| `models/context.py` | Remove | ❌ | Infrastructure concern |

**Project Model Violations:**

```python
# Current: src/feptm/models/project.py
class Project(BaseModel):
    name: str
    drive_folder_id: Optional[str] = None           # ❌ Google ID
    project_info_spreadsheet_id: Optional[str]      # ❌ Google ID
    report_spreadsheet_id: Optional[str]            # ❌ Google ID
    calculations_spreadsheet_id: Optional[str]      # ❌ Google ID
    
    @computed_field
    def drive_folder_url(self) -> Optional[str]:    # ❌ Infrastructure concern
        ...
```

**Specialist Model Violations:**

```python
# Current: src/feptm/models/specialist.py
class Specialist(BaseModel):
    name: str
    role: str
    timesheet: Optional[str] = None                 # ❌ Google ID
    
    @computed_field
    def timesheet_url(self) -> Optional[str]:       # ❌ Infrastructure concern
        ...
```

#### Services

| Current File | Target Location | Compliance | Issues |
|--------------|-----------------|------------|--------|
| `timesheets/project_service.py` | Split into domain + adapters | ❌ | Mixed concerns |
| `timesheets/specialist_service.py` | Split into domain + adapters | ❌ | Mixed concerns |
| `timesheets/config_service.py` | `adapters/sheets/` | ⚠️ | Enum definitions should stay |

**TimesheetProjectService Violations (1379 lines):**

| Method | Lines | Issue |
|--------|-------|-------|
| `update_project_info_sheet` | 38-119 | Direct API calls, hardcoded column names |
| `create_project` | 150-264 | Mixes domain logic with Google Drive operations |
| `sync_project_specialists` | 266-324 | Orchestration + API calls in same method |
| `_extract_project_metadata` | 357-475 | Parsing Google Sheets data in service |
| `_link_specialist_timesheets` | 477-538 | Direct spreadsheet manipulation |
| `_update_general_expenses_current_period_tab` | 540-595 | 50+ lines of sheet manipulation |
| `_insert_and_update_specialist_row` | 777-872 | Complex row insertion logic |
| `_copy_row_formatting` | 1251-1327 | Raw API copyPaste call |

**Single Responsibility Violations:**
- Creates Google Drive folders
- Creates spreadsheets from templates
- Reads/writes project metadata
- Manages specialist timesheets
- Updates report sheets
- Handles formula insertion
- Row insertion and copying

**SpecialistService Violations (585 lines):**

| Method | Lines | Issue |
|--------|-------|-------|
| `get_specialists_from_sheet` | 74-104 | Mixes data extraction with validation |
| `create_timesheet` | 106-145 | Direct template copying |
| `update_specialists_sheet` | 147-180 | Direct sheet updates |
| `_parse_specialist_row` | 320-370 | Parsing logic coupled to sheet structure |

### Layer: adapters/ (Target) vs services/ (Current)

**Target:** 
- `adapters/sheets/` - In-memory spreadsheet abstraction
- `adapters/google/` - Google API wrapper

**Current State:**

| Current File | Target Location | Compliance | Issues |
|--------------|-----------------|------------|--------|
| `services/google_sheets_service.py` | `adapters/google/sheets_client.py` | ⚠️ Partial | No abstraction layer |

**GoogleSheetsService Analysis:**

**Positive:**
- Singleton pattern
- OAuth credential handling
- Basic CRUD operations

**Negative:**
- No in-memory state
- No change tracking
- No batch optimization
- Utility methods mixed with API calls
- 691 lines in single file

**Missing Abstractions:**
- `Workbook` - in-memory spreadsheet representation
- `Sheet` - in-memory sheet with cells
- `Cell` - value or formula container
- `Range` - cell range with operations
- `Formula` - formula with reference handling
- `UnitOfWork` - change tracking and batch commit

### Layer: interfaces/ (Target) vs api/ (Current)

**Target:** FastAPI endpoints with dependency injection.

**Current State:**

| Current File | Target Location | Compliance | Issues |
|--------------|-----------------|------------|--------|
| `api/router.py` | `interfaces/api/router.py` | ⚠️ | Missing DI setup |
| `api/v1/projects.py` | `interfaces/api/v1/projects.py` | ⚠️ | Direct service instantiation |

**Endpoint Issues:**

```python
# Current: src/feptm/api/v1/projects.py
@router.post("/create", response_model=ProjectMetaResponse)
async def create_project(request: ProjectCreateRequest) -> ProjectMetaResponse:
    # ❌ Service instantiated inside endpoint
    timesheet_service = TimesheetProjectService(google_sheets_service)
    result = timesheet_service.create_project(project)
```

**Should be:**

```python
@router.post("/create", response_model=CreateProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service)  # ✅ DI
) -> CreateProjectResponse:
    ...
```

## Architectural Violations Summary

### V-001: Domain Models Contain Infrastructure IDs

**Severity:** High

**Location:** `models/project.py`, `models/specialist.py`

**Description:** Domain models store Google Sheets/Drive IDs and compute URLs.

**Impact:** Cannot test domain logic without Google infrastructure.

### V-002: No Spreadsheet Abstraction Layer

**Severity:** High

**Location:** All `timesheets/` services

**Description:** Services directly manipulate Google Sheets API without in-memory representation.

**Impact:** 
- No batch optimization
- Cannot test without mocking complex API
- Tight coupling to Google API structure

### V-003: Services Mix Business Logic with API Calls

**Severity:** High

**Location:** `timesheets/project_service.py`, `timesheets/specialist_service.py`

**Description:** Single service classes handle domain operations, API calls, data parsing, and error handling.

**Impact:**
- Difficult to test
- Hard to modify
- Duplicate logic across services

### V-004: No Dependency Injection

**Severity:** Medium

**Location:** `api/v1/projects.py`

**Description:** Services instantiated inside endpoints with hardcoded dependencies.

**Impact:**
- Cannot swap implementations
- Testing requires patching globals

### V-005: Missing Exception Hierarchy

**Severity:** Medium

**Location:** Entire codebase

**Description:** No custom exceptions. Uses generic `Exception` with string messages.

**Impact:**
- Cannot catch specific errors
- Inconsistent error responses

### V-006: God Object Anti-Pattern

**Severity:** High

**Location:** `timesheets/project_service.py` (1379 lines)

**Description:** Single class handles 10+ distinct responsibilities.

**Impact:**
- Difficult to understand
- Changes affect entire class
- Testing requires extensive mocking

### V-007: String Literals for Column Names

**Severity:** Low

**Location:** Throughout services

**Description:** Column names hardcoded as strings despite `ColumnName` enum existing.

**Current:**
```python
headers, [ColumnName.SPECIALIST.value]  # ✅ Using enum
f"{sheet_name}!A1:B{len(data)}"          # ❌ Hardcoded
```

**Impact:** Inconsistent, prone to typos.

## Metrics

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Lines in largest service | 1379 | <300 | -1079 |
| Domain model Google IDs | 5 | 0 | -5 |
| Custom exception classes | 0 | 5+ | -5 |
| Test coverage | ~40%* | 80% | -40% |
| Services with DI | 0 | All | Full |

*Estimated based on test file analysis.

## Module Mapping: Current → Target

| Current Module | Target Module | Action |
|----------------|---------------|--------|
| `core/config.py` | `core/config.py` | Keep |
| `core/log.py` | `core/log.py` | Keep |
| `core/utils.py` | Split | Move domain utils to domain/, Google utils to adapters/ |
| `models/project.py` | `domain/models/project.py` | Remove Google IDs |
| `models/specialist.py` | `domain/models/specialist.py` | Remove Google IDs |
| `models/context.py` | Remove | Inline into services |
| `services/google_sheets_service.py` | `adapters/google/sheets_client.py` | Wrap with abstraction |
| `timesheets/config_service.py` | `adapters/sheets/` + `core/` | Split enums and service |
| `timesheets/project_service.py` | Split | Domain service + repository impl |
| `timesheets/specialist_service.py` | Split | Domain service + repository impl |
| `api/router.py` | `interfaces/api/router.py` | Add DI setup |
| `api/v1/projects.py` | `interfaces/api/v1/projects.py` | Use injected services |
| — | `adapters/sheets/workbook.py` | New |
| — | `adapters/sheets/cell.py` | New |
| — | `adapters/sheets/formula.py` | New |
| — | `adapters/sheets/unit_of_work.py` | New |
| — | `core/exceptions.py` | New |
| — | `domain/services/project_service.py` | New |
| — | `domain/services/specialist_service.py` | New |

## Refactoring Effort Estimate

| Component | Complexity | New Code | Modified Code |
|-----------|------------|----------|---------------|
| Spreadsheet abstraction | High | ~800 lines | — |
| Domain models | Low | ~200 lines | ~150 lines |
| Domain services | Medium | ~400 lines | — |
| Repository implementations | Medium | ~500 lines | — |
| Exception hierarchy | Low | ~100 lines | ~50 lines |
| API endpoints | Low | ~100 lines | ~150 lines |
| Tests | High | ~1500 lines | ~500 lines |
| **Total** | — | **~3600 lines** | **~850 lines** |

## Test Structure Analysis

**Current:**
```
tests/
├── api/v1/test_projects.py          # 1 file
├── models/test_project.py           # 1 file
├── services/test_google_sheets_service.py  # 1 file
└── timesheets/
    ├── test_project_service.py      # 1 file
    └── test_specialist_service.py   # 1 file (461 lines)
```

**Issues:**
- No clear unit/integration separation
- Tests in `test_specialist_service.py` mix unit and integration concerns
- Mocking strategy inconsistent

**Target:**
```
tests/
├── unit/
│   ├── domain/
│   │   ├── test_project_service.py
│   │   └── test_specialist_service.py
│   └── adapters/
│       └── sheets/
│           ├── test_workbook.py
│           ├── test_formula.py
│           └── test_unit_of_work.py
└── integration/
    └── api/
        └── test_projects_api.py
```

## Conclusion

Current codebase requires significant restructuring to achieve target architecture. Primary effort areas:

1. **Create spreadsheet abstraction layer** (highest impact)
2. **Separate domain from infrastructure** in models
3. **Split god object service** into focused components
4. **Add dependency injection** to endpoints
5. **Establish exception hierarchy**
6. **Reorganize and expand tests**

Total estimated new/modified code: ~4450 lines.
