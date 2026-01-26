# Debug Tools for FEPTM Server (LLM Reference)

## Purpose

CLI tools for inspecting Google Drive folders and Google Sheets spreadsheets. Use when debugging sync issues, verifying template structure, or examining generated timesheets.

## Prerequisites

- OAuth credentials configured (`credentials.json` in project root)
- First authentication completed (token saved)

## Tools

### 1. inspect_folder.py

Recursively lists Google Drive folder contents.

```bash
uv run python bin/inspect_folder.py <folder_id_or_url>
```

**Use when:**
- Verifying project folder structure
- Checking if timesheets were created
- Finding file IDs

**Example:**
```bash
# By ID
uv run python bin/inspect_folder.py 1kw8rS5F0ttZui9oT-CT1VGJutg4zFKZT

# By URL
uv run python bin/inspect_folder.py "https://drive.google.com/drive/folders/1kw8rS5F0ttZui9oT-CT1VGJutg4zFKZT"
```

**Output includes:**
- 📁 Folders with IDs
- 📊 Spreadsheets with IDs and URLs
- Recursive subfolder contents

---

### 2. inspect_spreadsheet.py

Examines spreadsheet structure and content.

```bash
uv run python bin/inspect_spreadsheet.py <spreadsheet_id> [sheet_name] [range]
```

**Use when:**
- Checking sheet column structure
- Verifying data format
- Finding formulas
- Debugging mapper issues

**Examples:**
```bash
# List all sheets
uv run python bin/inspect_spreadsheet.py 1LJRcO4TxwmWK76w4ZfLScaWi2ZJasj4TOPQJkUjwlwk

# View specific sheet
uv run python bin/inspect_spreadsheet.py 1LJRcO4TxwmWK76w4ZfLScaWi2ZJasj4TOPQJkUjwlwk "Team"

# View specific range
uv run python bin/inspect_spreadsheet.py 1LJRcO4TxwmWK76w4ZfLScaWi2ZJasj4TOPQJkUjwlwk "Team" "A1:G10"
```

**Output includes:**
- Sheet names and sizes
- Column headers with letters (A: Name | B: Role | ...)
- Data rows formatted as table
- Formulas in cells (if any)

---

### 3. inspect_templates.py

Shows all configured templates from `.env`.

```bash
uv run python bin/inspect_templates.py
```

**Use when:**
- Verifying template configuration
- Understanding expected sheet structure
- Checking column layout before writing code

**Output includes:**
- All 4 template IDs and URLs
- Sheet names in each template
- Column headers for each sheet
- Sample data rows
- Projects folder ID

---

### 4. inspect_project.py

Comprehensive project inspection.

```bash
uv run python bin/inspect_project.py <project_info_spreadsheet_id>
```

**Use when:**
- Debugging sync failures
- Verifying project structure completeness
- Checking if timesheets exist and are linked

**Output includes:**
- Project Info sheet content (Name, Created, links)
- Team sheet with all columns
- Project folder file listing
- Timesheets found (with IDs and URLs)
- Summary of what exists vs what's missing

---

## Common Debug Scenarios

### Scenario: Sync returns 200 but no timesheets created

1. Run `inspect_project.py` with project ID
2. Check Team sheet output - is Timesheet column (G) empty?
3. Check column structure matches expected format
4. Verify folder contents show only 3 spreadsheets (no timesheets)

### Scenario: Template structure mismatch

1. Run `inspect_templates.py`
2. Note column layout: `A: Name | B: Role | C: Project | D: Internal Rate | ...`
3. Compare with code expectations in `mappers.py` and `specialist_repository.py`
4. Adjust code column indices accordingly

### Scenario: Decimal parsing errors

1. Run `inspect_spreadsheet.py` on Team sheet
2. Check rate columns for format (comma vs dot, currency symbols)
3. Verify date format in Date column

### Scenario: Folder permissions

1. Run `inspect_folder.py` on projects folder
2. If error, check folder is shared with OAuth user
3. For service accounts, verify it's a Shared Drive

---

## Column Name Reference

Column names defined in `src/feptm/adapters/sheets/constants.py` (`ColumnName` enum):

| Team Sheet Column | ColumnName Enum |
|-------------------|-----------------|
| Name | `ColumnName.NAME` |
| Role | `ColumnName.ROLE` |
| Project | `ColumnName.PROJECT` |
| Internal Rate | `ColumnName.INTERNAL_RATE` |
| External Rate | `ColumnName.EXTERNAL_RATE` |
| Date | `ColumnName.DATE` |
| Timesheet | `ColumnName.TIMESHEET` |

## Helper Functions (`mappers.py`)

- `build_column_index(headers)` - Build column name -> index mapping from header row
- `get_cell_value(row, col_index, column_name)` - Get cell value by column name
- `get_column_letter(col_index, column_name)` - Get column letter (A, B, C...) by name

## Configuration Classes

- `TeamSheetConfig` - Team sheet data range (`START_CELL`, `END_CELL`)
- `ProjectInfoConfig` - Project info sheet range
- `CurrentPeriodConfig` - Current period sheet range

## Best Practices

- DO NOT hardcode column indices or letters
- Use `ColumnName` enum for column names
- Use `build_column_index()` to map headers to indices
- Use `get_cell_value()` to read cells by column name
- Use `get_column_letter()` to write cells by column name
