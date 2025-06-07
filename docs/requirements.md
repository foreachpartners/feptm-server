## Technical Specification for Backend Development of Time Tracking Service

## Keywords

FastAPI >=0.110.0, Python >=3.12, Google Sheets API v4, OAuth 2.0, Google Drive API v3, uvicorn >=0.29.0, Ubuntu 24.04 LTS, nginx >=1.24, systemd, OpenAPI 3.0, REST API, VPS, Time & Materials accounting, Single Source of Truth (Google Sheets), pydantic >=2.0.0, uv (package manager), Configuration Management, Formula Cache, Dynamic Formulas, Enum Constants, Type Safety

### 1. Development Goal
Development of a backend service for automating time tracking of the development team using Time & Materials model with Google Sheets API.

### 2. Functional Requirements

#### 2.1 Core Functions

- **Project Management:**
  - Create new projects.
  - Connect and disconnect specialists.
  - Change specialist rates and roles.

- **Timesheet Generation:**
  - Create and copy Google Sheets timesheets from templates.
  - Configure access for specialists (write access).
  - Automatic timesheet updates when specialist data changes.

- **Payment Period Management:**
  - Create and close payment periods with custom names and dates.
  - Automatic "Payment Period" field filling in timesheets.

- **Report Generation:**
  - Generate project cost summary reports based on timesheet data.
  - Automatic creation and updating of report tabs with calculations for specialist totals and overall costs.

---

### 3. Technical Requirements

#### 3.1 Technology Stack

- **Programming Language:** Python >=3.12
- **Web Framework:** FastAPI >=0.110.0
- **Package Manager:** uv (modern replacement for pip/poetry)
- **Data Validation:** Pydantic >=2.0.0
- **Google APIs:** Google Sheets API v4, Google Drive API v3
- **Authorization System:** OAuth 2.0 for Google API access
- **ASGI Server:** uvicorn >=0.29.0
- **Operating System:** Ubuntu 24.04 LTS
- **Web Server:** nginx (reverse proxy)
- **Process Manager:** systemd

#### 3.2 Project Architecture

**Project Structure:**
```
src/feptm/
├── main.py                     # Main application module
├── core/
│   ├── config.py              # Application configuration
│   └── log.py                 # Logging
├── api/
│   ├── router.py              # Main router
│   └── v1/
│       └── projects.py        # Projects API endpoints
├── models/
│   ├── project.py             # Project model
│   └── specialist.py          # Specialist model
├── services/
│   └── google_sheets_service.py  # Google Sheets API service
└── timesheets/
    ├── project_service.py     # Project management service
    ├── specialist_service.py  # Specialist management service
    └── config_service.py      # Configuration and formulas service
```

#### 3.2.1 Configuration Management System

**Configuration Google Sheets:**

The system uses a separate Google Sheets document for storing configuration data, including:

- **"Formulas" Sheet** - contains named formulas for calculations:
  - `Calculate working hours` - formula for calculating working hours
  - `Import specialist timesheet` - formula for importing timesheet data
  - `Gross total cost` - formula for calculating gross cost
  - `Net total cost` - formula for calculating net cost
  - `Revenue` - formula for calculating revenue

**Configuration Sheet Structure:**
| Column A | Column B |
|----------|----------|
| Formula name | Formula value |
| Calculate working hours | `=SUMIF(INDIRECT("'"&$A2&"'!$E$2:$E", true), TRIM($C2), INDIRECT("'"&$A2&"'!$D$2:$D", true))` |
| Import specialist timesheet | `=IMPORTRANGE("SpecialistSpreadsheetID", "timesheet!A:E")` |
| Gross total cost | `=$D2*$E2` |
| Net total cost | `=$D2*$G2` |
| Revenue | `=$F2-$H2` |

> **Note:** The provided formulas are examples and may change and be supplemented. For the current list of formulas, refer to the configuration document specified in the `GOOGLE_CONFIG_SHEET_ID` environment variable.

**ConfigService Functionality:**
- Dynamic formula loading from configuration sheet
- Formula caching for performance optimization
- Automatic parameter substitution in formulas (e.g., timesheet specialist ID)
- Error handling for missing configuration

#### 3.3 Functionality Requirements

**Implemented REST API endpoints:**

- `POST /api/v1/projects/create`
  - Create new project with automatic Google Sheets and access setup
  - Creates folder in Google Drive, project documentation, reports and calculations

- `POST /api/v1/projects/sync`
  - Synchronize project specialists
  - Analyze project table and create timesheets for new specialists

**Required REST API endpoints:**

- `/api/v1/periods`
  - PUT: Close payment period and generate totals

**Management through Google Sheets:**

- **Adding specialists:** Done directly through editing "Team" sheet in project information (see `GOOGLE_PROJECT_INFO_TEMPLATE_ID`)
- **Timesheet generation:** Automatically happens in `/api/v1/projects/sync` endpoint when new specialists are detected
- **Report generation:** Automatically happens in `/api/v1/projects/sync` endpoint with linked document creation

#### 3.4 Data Models

> **Note:** The provided data models are examples of main entities and may change and be supplemented. For the current list of models and their structure, refer to the `src/feptm/models/` folder.

**Specialist (example):**
```python
- name: str                    # Full name
- role: str                    # Role (Developer, QA, Designer, Project Manager, DevOps)
- project: Optional[str]       # Project name
- internal_rate: Decimal       # Internal hourly rate
- external_rate: Decimal       # Client hourly rate
- date: Optional[datetime]     # Connection date
- timesheet: Optional[str]     # Google Sheets timesheet ID
```

**Project (example):**
```python
- name: str                           # Project name
- drive_folder_id: Optional[str]      # Google Drive folder ID
- project_info_spreadsheet_id: Optional[str]    # Project information ID
- report_spreadsheet_id: Optional[str]          # Report ID
- calculations_spreadsheet_id: Optional[str]    # Calculations ID
- created: datetime                   # Creation date
- modified: datetime                  # Modification date
```

**Payment Period (requires implementation, example):**
```python
- id: UUID                     # Unique identifier
- project_id: UUID            # Project ID
- period_name: str            # Period name
- start_date: datetime        # Start date
- end_date: datetime          # End date
```

#### 3.5 Architectural Features

- **Single Source of Truth:** All information stored exclusively in Google Sheets (no separate database)
- **Google Sheets as DB:** Google Sheets used as single data source
- **API Gateway:** Backend processes frontend requests and works directly with Google Sheets API
- **Template Approach:** All documents created based on pre-prepared templates
- **OAuth Integration:** Full integration with Google OAuth 2.0 for secure access
- **Formula Management System:** Centralized formula storage in configuration sheet with caching

#### 3.6 Configuration

**Environment Variables (example):**
```bash
# Google API
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=~/.google_sheets_token.json
GOOGLE_TIMESHEET_TEMPLATE_ID=your_template_id
GOOGLE_PROJECT_INFO_TEMPLATE_ID=your_template_id
GOOGLE_PROJECT_REPORT_TEMPLATE_ID=your_template_id
GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID=your_template_id
GOOGLE_PROJECTS_FOLDER_ID=your_folder_id

# Configuration Management
GOOGLE_CONFIG_SHEET_ID=your_config_sheet_id

# Application
PROJECT_NAME="Time & Materials Accounting API"
VERSION=0.1.0
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

> **Note:** The provided environment variables are examples and may change and be supplemented. For the current list of variables, refer to the `.env` and `env.example` files in the project root.

**Configuration Sheet Setup:**

1. **Create configuration document:**
   - Create new Google Sheets document
   - Add sheet named "Formulas"
   - Configure "Share by link" access for reading

2. **"Formulas" Sheet Structure:**
   - Column A: Formula name (Formula name)
   - Column B: Formula value (Formula value)
   - First row contains headers
   - Starting from second row - formula data

3. **Required formulas (examples):**
   - `Calculate working hours`
   - `Import specialist timesheet`
   - `Gross total cost`
   - `Net total cost`
   - `Revenue`

**Configuration document:** Access to the current configuration document is through the `GOOGLE_CONFIG_SHEET_ID` environment variable

4. **Create env.example file:**
   ```bash
   # Google API Configuration
   GOOGLE_CREDENTIALS_FILE=credentials.json
   GOOGLE_TOKEN_FILE=~/.google_sheets_token.json
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   
   # Google Sheets Templates
   GOOGLE_TIMESHEET_TEMPLATE_ID=your_timesheet_template_id
   GOOGLE_PROJECT_INFO_TEMPLATE_ID=your_project_info_template_id
   GOOGLE_PROJECT_REPORT_TEMPLATE_ID=your_report_template_id
   GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID=your_calculations_template_id
   
   # Google Drive Settings
   GOOGLE_PROJECTS_FOLDER_ID=your_projects_folder_id
   
   # Configuration Management
   GOOGLE_CONFIG_SHEET_ID=your_config_sheet_id
   
   # Application Settings
   PROJECT_NAME="Time & Materials Accounting API"
   PROJECT_DESCRIPTION="Backend service for time and materials accounting with Google Sheets"
   VERSION=0.1.0
   HOST=0.0.0.0
   PORT=8000
   DEBUG=true
   API_KEY=your_optional_api_key
   ```

#### 3.6.1 Formula Management System

**Dynamic Formulas:**

- **Centralized Management:** All formulas stored in one configuration sheet
- **Type-safe Access:** Using Enum for safe formula access
- **Automatic Substitution:** Dynamic parameter replacement in formulas (e.g., timesheet IDs)
- **Caching:** Formulas cached after first access for performance
- **Error Handling:** System correctly handles missing formulas or configuration

**Formula Usage in Code:**
```python
from feptm.timesheets.config_service import config_service, FormulaName

# Get formula for gross total cost calculation
gross_total_cost_formula = config_service.get_formula(FormulaName.GROSS_TOTAL_COST)

# Get import formula with timesheet ID substitution
import_formula = config_service.get_import_specialist_timesheet_formula(timesheet_id)
```

**Enum Constants:**
- `FormulaName` - available formula names
- `SheetName` - sheet names in documents
- `ColumnName` - column names in tables
- `DateFormat` - date formats
- `RangeFormat` - range formats for API calls

#### 3.7 Deployment Requirements

- **Python Environment:** Python >=3.12 using uv for dependency management
- **ASGI Server:** FastAPI deployed through uvicorn, launched using systemd
- **Reverse Proxy:** HTTPS access using nginx as reverse proxy
- **Configuration:** Separate configuration file (.env) for environment variables (see pyproject.toml and env.example)
- **Logging:** Structured logging for debugging and monitoring
- **API Documentation:** Automatic OpenAPI 3.0 documentation generation via FastAPI

#### 3.8 Project Dependencies

> **Note:** The provided dependencies are examples and may change and be supplemented. For the current list of dependencies, refer to the `pyproject.toml` file in the project root.

**Main Dependencies (example):**
```toml
fastapi>=0.110.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.2.0
uvicorn>=0.29.0
google-api-python-client>=2.0.0
google-auth>=2.0.0
google-auth-oauthlib>=0.4.0
email-validator>=2.2.0
```

**Development Tools (example):**
```toml
black>=25.1.0
flake8>=7.2.0
flake8-pyproject>=1.2.3
httpx>=0.28.1
isort>=6.0.1
mypy>=1.15.0
pytest>=8.3.5
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
```

**Dependency Management:**
- **Package Manager:** uv (modern replacement for pip/poetry)
- **Configuration:** All dependencies described in `pyproject.toml`
- **Dependency Groups:** Main dependencies and dev dependency-groups
- **Development Commands:** Available through `Makefile` (lint, format, test, etc.)

**Main Development Commands:**
```bash
make lint          # Code style checking (flake8)
make format        # Code formatting (black)
make isort         # Import sorting
make typecheck     # Type checking (mypy)
make test          # Run tests (pytest)
make test-coverage # Run tests with coverage
make all          # Run all tools
```

### 4. Endpoint Results

Based on testing `/create` and `/sync` endpoints, the following results can be observed:

#### 4.1 `/api/v1/projects/create` Endpoint

**Result:** Creates complex project document structure in Google Drive:

1. **Project Folder** - organizes all project documents in Google Drive
2. **Project Information** - main document (see `GOOGLE_PROJECT_INFO_TEMPLATE_ID`) with:
   - "Project info" sheet with project metadata:
     - Project ID, Name, Created/Modified dates
     - Links to Project Folder, Payment Distribution, General Expenses
   - "Team" sheet for team specialist management
3. **Project Report (General Expenses)** - document for summary reports:
   - "Current Period" sheet - current period with specialist data
   - Individual sheets for each specialist with IMPORTRANGE formulas
4. **Project Calculations (Payment Distribution)** - document for financial calculations:
   - "Current Period" sheet - payment calculations by specialists
   - Linking with timesheets through formulas

**Returned Data:**
- `drive_folder_id` and `drive_folder_url` - project folder
- `project_info_spreadsheet_id` and `project_info_spreadsheet_url` - project information
- `report_spreadsheet_id` and `report_spreadsheet_url` - reports
- `calculations_spreadsheet_id` and `calculations_spreadsheet_url` - calculations

#### 4.2 `/api/v1/projects/sync` Endpoint

**Result:** Automatically creates personal timesheets for specialists:

**Synchronization Process:**
1. Analyzes "Team" sheet in project information (see `GOOGLE_PROJECT_INFO_TEMPLATE_ID`)
2. Extracts specialist data (name, role, internal and external rates)
3. Creates personal timesheets for specialists who don't have them yet
4. Updates "Team" sheet with created timesheet IDs
5. Automatically creates specialist tabs in reports (General Expenses) and calculations (Payment Distribution)
6. Links all documents through IMPORTRANGE formulas for real-time updates

**Returned Data:**
- `specialists_found` - total number of found specialists
- `specialists_created` - number of created timesheets
- `specialists[]` - array of specialist objects with their data

**Timesheet Structure:** (see `GOOGLE_TIMESHEET_TEMPLATE_ID`)
- **Date** (column A) - work completion date
- **Project** (column B) - project name
- **Task Name** (column C) - description of completed task
- **Work Hours** (column D) - number of hours worked
- **Payment Period** (column E) - payment period (filled by Project Manager)
- **Payment Status** (column F) - payment status (filled by Project Manager)

**Timesheet Features:**
- Created based on template with pre-configured structure
- Name formatted as: "Time Tracking for [Specialist Name]. Project [Project Name]"
- Automatically placed in project folder
- Contains 100 rows for entries (rows 1-100)
- Integrated with reporting documents through IMPORTRANGE formulas

#### 4.3 Configuration Service Integration

**Automatic Formula Application:**

During project synchronization (`/api/v1/projects/sync`) the system automatically:

1. **Loads formulas** from configuration sheet
2. **Applies to new specialists:**
   - Working hours calculation formula in "Hours Worked" column
   - Gross total cost formula in "Total Cost (USD)" column
   - Net total cost formula in "Specialist Work Cost (USD)" column
   - Revenue formula in "Revenue (USD)" column
3. **Substitutes parameters:** Automatically replaces template values with actual IDs
4. **Updates references:** Corrects cell references for each specialist row

**System Benefits:**
- **Centralization:** Changing formula in one place affects all projects
- **Flexibility:** Ability to modify calculations without code changes
- **Consistency:** Unified formulas for all projects and specialists
- **Performance:** Caching minimizes Google Sheets API calls

### 5. Limitations and Assumptions

- No specialist notifications at this stage
- No separate DB, all data stored in Google Sheets
- Frontend implemented separately (Next.js application)
- Google Sheets template access must be configured with "Share by link" permissions
- Timesheets contain fixed number of rows (100) for time entries
- Payment period and status management done manually through Project Manager
- **Specialist management** done directly through editing "Team" sheet in Google Sheets, not through API
- **Timesheet and report generation** happens automatically in `/sync` endpoint, not through separate endpoints
- Single planned endpoint for periods - payment period closure
- **Configuration sheet** must be created and configured manually before first launch
- **Configuration formulas** require adherence to precise Google Sheets syntax
- **Formula cache** clears on application restart

---

