# Google Sheets Abstraction Layer: Research Document

## Purpose

Evaluate approaches for in-memory spreadsheet representation with batch synchronization to Google Sheets API.

## Current Implementation Analysis

Current codebase uses `google-api-python-client` directly:

```python
# src/feptm/services/google_sheets_service.py
from googleapiclient.discovery import build
self.sheets_service = build("sheets", "v4", credentials=creds)
```

**Problems identified:**

- Direct API calls per operation (no batching)
- No in-memory state management
- Formula handling via `value_input_option="USER_ENTERED"`
- Cell copying via `copyPaste` batchUpdate request
- Tight coupling between business logic and API calls

## Evaluation Criteria

| ID | Criterion | Weight | Description |
|----|-----------|--------|-------------|
| C1 | Batch operations | High | Accumulate changes, sync in single API call |
| C2 | In-memory representation | High | Work with local data before sync |
| C3 | Formula preservation | Critical | Read/write formulas as formulas, not evaluated values |
| C4 | Cell stretching | Critical | Relative references adjust on copy (A1→A2 when copying down) |
| C5 | Type safety | Medium | mypy strict compatibility |
| C6 | Testability | Medium | Mock API without real calls |

## Candidate Solutions

### 1. gspread

**Repository:** <https://github.com/burnash/gspread>

**Overview:** Most popular Python library for Google Sheets (8k+ GitHub stars).

**Formula Handling:**

```python
# Reading formulas (not evaluated values)
worksheet.get('A1', value_render_option='FORMULA')

# Writing formulas
worksheet.update('A1', '=SUM(B1:B10)', value_input_option='USER_ENTERED')
```

**Batch Operations:**

```python
# Batch update
worksheet.batch_update([
    {'range': 'A1', 'values': [['=SUM(B1:B10)']]},
    {'range': 'A2', 'values': [['=SUM(B2:B11)']]},
], value_input_option='USER_ENTERED')
```

**Cell Copying (Stretching):**

- NO native support for copyPaste with relative reference adjustment
- MUST use raw batchUpdate API for copyPaste operation:

```python
spreadsheet.batch_update({
    'requests': [{
        'copyPaste': {
            'source': {...},
            'destination': {...},
            'pasteType': 'PASTE_NORMAL'
        }
    }]
})
```

**Evaluation:**

| Criterion | Score | Notes |
|-----------|-------|-------|
| C1 Batch ops | ✅ | `batch_update`, `batch_get` supported |
| C2 In-memory | ⚠️ | Worksheet object caches data, but no explicit dirty tracking |
| C3 Formula preservation | ✅ | `value_render_option='FORMULA'` |
| C4 Cell stretching | ⚠️ | Requires raw API call |
| C5 Type safety | ⚠️ | Type stubs exist but incomplete |
| C6 Testability | ✅ | Can mock `gspread.Client` |

### 2. gspread-dataframe

**Repository:** <https://github.com/robin900/gspread-dataframe>

**Overview:** Extension to gspread adding pandas DataFrame integration.

**Usage:**

```python
from gspread_dataframe import get_as_dataframe, set_with_dataframe

df = get_as_dataframe(worksheet)
# ... modify df ...
set_with_dataframe(worksheet, df)
```

**Formula Handling:**

- DataFrames contain evaluated values by default
- Formula preservation requires custom handling:

```python
# Get raw values including formulas
df = get_as_dataframe(worksheet, evaluate_formulas=False)  # NOT SUPPORTED
```

**Limitation:** `evaluate_formulas` parameter does NOT exist. DataFrames always contain evaluated values.

**Evaluation:**

| Criterion | Score | Notes |
|-----------|-------|-------|
| C1 Batch ops | ✅ | Inherited from gspread |
| C2 In-memory | ✅ | DataFrame is in-memory |
| C3 Formula preservation | ❌ | DataFrames lose formulas |
| C4 Cell stretching | ❌ | No support |
| C5 Type safety | ⚠️ | pandas typing issues |
| C6 Testability | ✅ | DataFrame easily mocked |

**Verdict:** NOT SUITABLE due to formula loss.

### 3. pygsheets

**Repository:** <https://github.com/nithinmurali/pygsheets>

**Overview:** Alternative to gspread with more ORM-like API (2k+ GitHub stars).

**Formula Handling:**

```python
# Reading
cell = worksheet.cell('A1')
cell.formula  # Returns formula string or None
cell.value    # Returns evaluated value

# Writing
cell.formula = '=SUM(B1:B10)'
cell.update()  # Or worksheet.update_value('A1', '=SUM(B1:B10)')
```

**Batch Operations:**

```python
# DataRange for batch operations
data_range = worksheet.range('A1:C10')
data_range.values = [[...]]
data_range.update()
```

**Cell Copying:**

```python
# Copy with relative reference adjustment
worksheet.copy_range(
    'A1:B1',  # source
    'A2:B2',  # destination
    paste_type='PASTE_NORMAL'
)
```

**Evaluation:**

| Criterion | Score | Notes |
|-----------|-------|-------|
| C1 Batch ops | ✅ | DataRange, batch methods |
| C2 In-memory | ✅ | Cell/DataRange objects |
| C3 Formula preservation | ✅ | `cell.formula` property |
| C4 Cell stretching | ✅ | `copy_range` with paste_type |
| C5 Type safety | ⚠️ | Limited type hints |
| C6 Testability | ✅ | Can mock client |

### 4. pandas + openpyxl (Local-first approach)

**Concept:** Use pandas with openpyxl for local spreadsheet operations, sync to Google Sheets.

**Formula Handling in openpyxl:**

```python
from openpyxl import Workbook
wb = Workbook()
ws = wb.active
ws['A1'] = '=SUM(B1:B10)'  # Preserved as formula
```

**Problem:** Syncing openpyxl workbook to Google Sheets requires:

1. Export to xlsx
2. Upload via Drive API
3. Convert to Google Sheets format

**Verdict:** NOT SUITABLE. Format conversion loses Google Sheets-specific features (IMPORTRANGE, real-time collaboration).

### 5. Custom Abstraction Layer

**Concept:** Build abstraction over current `google-api-python-client` implementation.

**Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│                    Domain Layer                          │
│  Project, Specialist, PaymentPeriod (no Google IDs)     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               Spreadsheet Abstraction                    │
│  Workbook, Sheet, Cell, Range, Formula                  │
│  Unit of Work (dirty tracking, batch sync)              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Google API Adapter                     │
│  Implements sync via sheets.spreadsheets.batchUpdate    │
└─────────────────────────────────────────────────────────┘
```

**Core Classes:**

```python
@dataclass
class Cell:
    row: int
    col: int
    value: str | float | None = None
    formula: str | None = None
    
    @property
    def is_formula(self) -> bool:
        return self.formula is not None

@dataclass  
class Sheet:
    name: str
    cells: dict[tuple[int, int], Cell]
    _dirty_cells: set[tuple[int, int]]
    
    def set_value(self, row: int, col: int, value: Any) -> None:
        self.cells[(row, col)] = Cell(row, col, value=value)
        self._dirty_cells.add((row, col))
    
    def set_formula(self, row: int, col: int, formula: str) -> None:
        self.cells[(row, col)] = Cell(row, col, formula=formula)
        self._dirty_cells.add((row, col))

class Workbook:
    sheets: dict[str, Sheet]
    _pending_operations: list[dict]  # copyPaste, insertDimension, etc.
    
    def copy_range(self, source: Range, dest: Range) -> None:
        self._pending_operations.append({
            'copyPaste': {
                'source': source.to_grid_range(),
                'destination': dest.to_grid_range(),
                'pasteType': 'PASTE_NORMAL'
            }
        })

class UnitOfWork:
    def __init__(self, google_service: GoogleSheetsService):
        self._service = google_service
        self._workbooks: dict[str, Workbook] = {}
    
    def get_workbook(self, spreadsheet_id: str) -> Workbook:
        if spreadsheet_id not in self._workbooks:
            self._workbooks[spreadsheet_id] = self._load_workbook(spreadsheet_id)
        return self._workbooks[spreadsheet_id]
    
    def commit(self) -> None:
        for spreadsheet_id, workbook in self._workbooks.items():
            requests = self._build_requests(workbook)
            if requests:
                self._service.batch_update(spreadsheet_id, requests)
        self._workbooks.clear()
```

**Evaluation:**

| Criterion | Score | Notes |
|-----------|-------|-------|
| C1 Batch ops | ✅ | Unit of Work collects changes |
| C2 In-memory | ✅ | Full workbook in memory |
| C3 Formula preservation | ✅ | Explicit formula handling |
| C4 Cell stretching | ✅ | copyPaste in pending operations |
| C5 Type safety | ✅ | Full control over types |
| C6 Testability | ✅ | In-memory state, mock adapter |

**Effort:** High (2-3 weeks development)

## Comparison Matrix

| Solution | Batch | In-Memory | Formulas | Stretching | Types | Testing | Effort |
|----------|-------|-----------|----------|------------|-------|---------|--------|
| gspread | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | Low |
| gspread-dataframe | ✅ | ✅ | ❌ | ❌ | ⚠️ | ✅ | Low |
| pygsheets | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | Low |
| pandas+openpyxl | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A |
| Custom abstraction | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | High |

## Decision: pygsheets

### Rationale

- **Native formula support:** `cell.formula` property for read/write
- **Built-in cell stretching:** `worksheet.copy_range()` with `paste_type='PASTE_NORMAL'`
- **Batch operations:** `DataRange`, `worksheet.update_values()`, batch methods
- **In-memory representation:** `Cell`, `Worksheet` objects cached locally
- **Reduced development effort:** Low vs High for custom abstraction
- **Mature library:** 2k+ GitHub stars, active maintenance

### Trade-offs Accepted

- **Limited type hints:** Will add custom type stubs or `# type: ignore` where needed
- **pygsheets API exposure:** Domain layer will NOT import pygsheets directly; thin adapter layer isolates

### Implementation Approach

1. Replace `google-api-python-client` with `pygsheets`
2. Create `adapters/sheets/` layer wrapping pygsheets:
   - `PygSheetsClient` implementing `SheetsClient` protocol
   - Repository implementations using pygsheets objects
3. Domain models remain infrastructure-agnostic
4. Unit of Work pattern as thin wrapper over pygsheets for batch control

## API Design Considerations

### Formula Representation

```python
class Formula:
    """Represents a spreadsheet formula with relative/absolute references."""
    
    raw: str  # e.g., "=SUM($A$1:A10)"
    
    def offset(self, rows: int = 0, cols: int = 0) -> "Formula":
        """Return formula with relative references adjusted."""
        ...
    
    @classmethod
    def from_template(cls, template: str, **kwargs: str) -> "Formula":
        """Create formula from template with substitutions."""
        # e.g., Formula.from_template("=IMPORTRANGE(\"{id}\", \"timesheet!A:E\")", id="abc123")
```

### Range Operations

```python
class Range:
    sheet_name: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int
    
    def copy_to(self, dest: "Range", paste_type: PasteType = PasteType.NORMAL) -> None:
        """Copy range with formula adjustment."""
        ...
    
    def fill_down(self, rows: int) -> None:
        """Fill formulas down, adjusting relative references."""
        ...
```

### Batch Sync

```python
class SyncStrategy(Enum):
    IMMEDIATE = "immediate"  # Sync after each operation
    BATCH = "batch"          # Collect operations, sync on commit
    
class SpreadsheetContext:
    def __init__(self, strategy: SyncStrategy = SyncStrategy.BATCH):
        ...
    
    def __enter__(self) -> "SpreadsheetContext":
        return self
    
    def __exit__(self, *args) -> None:
        if self.strategy == SyncStrategy.BATCH:
            self.commit()
```

## Out of Scope

- Real-time collaboration handling (Google handles)
- Conflict resolution (last-write-wins acceptable)
- Offline mode
- Excel format support
