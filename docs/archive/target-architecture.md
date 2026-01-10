# Target Architecture: FEPTM Server

## Overview

Layered architecture with clean separation between domain logic, spreadsheet abstraction, and external APIs.

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         interfaces/                                 │
│                    FastAPI REST Endpoints                          │
│               POST /api/v1/projects/create                         │
│               POST /api/v1/projects/sync                           │
│               PUT /api/v1/periods/close                            │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                          domain/                                    │
│                     Business Services                               │
│        ProjectService, SpecialistService, PeriodService            │
│                                                                     │
│                      Domain Models                                  │
│           Project, Specialist, PaymentPeriod, Team                 │
│              (NO Google IDs, pure business logic)                  │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                         adapters/                                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    sheets/                                    │  │
│  │              pygsheets Wrapper Layer                          │  │
│  │    PygSheetsClient, Repository, FormulaTemplates             │  │
│  │         (wraps pygsheets.Spreadsheet, Worksheet)             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                │                                    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    pygsheets                                  │  │
│  │              Third-party Library                              │  │
│  │         Spreadsheet, Worksheet, Cell, DataRange              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                           core/                                     │
│              Configuration, Logging, Utilities                     │
│                    Settings, log, utils                            │
└────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
src/feptm/
├── __init__.py
├── main.py                      # FastAPI app factory
├── py.typed                     # PEP 561 marker
│
├── core/
│   ├── __init__.py
│   ├── config.py                # Settings via pydantic-settings
│   ├── log.py                   # Structured logging setup
│   ├── utils.py                 # Pure utility functions
│   └── exceptions.py            # Base exception classes
│
├── domain/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py           # Project, ProjectInfo
│   │   ├── specialist.py        # Specialist, Rate
│   │   ├── period.py            # PaymentPeriod
│   │   └── team.py              # Team, TeamMember
│   │
│   └── services/
│       ├── __init__.py
│       ├── project_service.py   # ProjectService
│       ├── specialist_service.py # SpecialistService
│       └── period_service.py    # PeriodService
│
├── adapters/
│   ├── __init__.py
│   │
│   ├── sheets/
│   │   ├── __init__.py
│   │   ├── client.py            # PygSheetsClient (wraps pygsheets)
│   │   ├── formula_templates.py # Formula templates with substitutions
│   │   ├── project_repository.py    # ProjectRepository implementation
│   │   ├── specialist_repository.py # SpecialistRepository implementation
│   │   └── mappers.py           # Domain <-> Spreadsheet mapping
│   │
│   └── google/
│       ├── __init__.py
│       ├── auth.py              # OAuth2 credential handling (for pygsheets)
│       └── drive_client.py      # Google Drive API wrapper (folder ops)
│
└── interfaces/
    ├── __init__.py
    └── api/
        ├── __init__.py
        ├── router.py            # Main API router
        └── v1/
            ├── __init__.py
            ├── projects.py      # Project endpoints
            ├── specialists.py   # Specialist endpoints
            └── periods.py       # Period endpoints

tests/
├── __init__.py
├── conftest.py                  # Shared fixtures
│
├── unit/
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── test_project_service.py
│   │   ├── test_specialist_service.py
│   │   └── test_period_service.py
│   │
│   └── adapters/
│       ├── __init__.py
│       └── sheets/
│           ├── __init__.py
│           ├── test_formula_templates.py
│           ├── test_project_repository.py
│           └── test_specialist_repository.py
│
└── integration/
    ├── __init__.py
    └── api/
        ├── __init__.py
        └── test_projects_api.py
```

## Layer Specifications

### core/ Layer

**Purpose:** Cross-cutting concerns, no business logic.

**Dependencies:** External libraries only (pydantic, logging).

**Modules:**

```python
# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Google API
    google_credentials_file: str = "credentials.json"
    google_token_file: str = "~/.google_sheets_token.json"
    
    # Templates
    google_timesheet_template_id: str
    google_project_info_template_id: str
    google_report_template_id: str
    google_calculations_template_id: str
    google_config_sheet_id: str
    google_projects_folder_id: str | None = None
    
    # Application
    project_name: str = "FEPTM API"
    version: str = "0.2.0"
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# core/exceptions.py
class FeptmError(Exception):
    """Base exception for all application errors."""
    
    def __init__(self, message: str, code: str = "FEPTM_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)

class ValidationError(FeptmError):
    """Raised when input validation fails."""
    pass

class NotFoundError(FeptmError):
    """Raised when resource not found."""
    pass

class GoogleApiError(FeptmError):
    """Raised when Google API call fails."""
    pass
```

### domain/ Layer

**Purpose:** Business logic, domain models. NO external dependencies.

**Dependencies:** core/ only.

**Domain Models (MUST):**
- Immutable where possible (frozen dataclasses or Pydantic with frozen=True)
- No Google Sheets IDs
- No infrastructure concerns

```python
# domain/models/specialist.py
from dataclasses import dataclass
from decimal import Decimal
from datetime import date

@dataclass(frozen=True)
class Rate:
    """Hourly rate for a specialist."""
    internal: Decimal  # Rate paid to specialist
    external: Decimal  # Rate charged to client
    
    def revenue_per_hour(self) -> Decimal:
        return self.external - self.internal

@dataclass
class Specialist:
    """Team member with timesheet."""
    name: str
    role: str
    rate: Rate
    joined_date: date
    
    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Specialist name MUST NOT be empty")
```

```python
# domain/models/project.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from .specialist import Specialist

@dataclass
class Project:
    """Project with team and payment periods."""
    name: str
    created: datetime = field(default_factory=datetime.utcnow)
    team: List[Specialist] = field(default_factory=list)
    
    def add_specialist(self, specialist: Specialist) -> None:
        if any(s.name == specialist.name for s in self.team):
            raise ValueError(f"Specialist {specialist.name} already in team")
        self.team.append(specialist)
```

**Domain Services (MUST):**
- Orchestrate domain operations
- Receive repositories via constructor injection
- Return domain objects, not infrastructure objects

```python
# domain/services/project_service.py
from typing import Protocol
from ..models.project import Project
from ..models.specialist import Specialist

class ProjectRepository(Protocol):
    """Repository interface for project persistence."""
    
    def create(self, project: Project) -> str:
        """Create project, return external ID."""
        ...
    
    def get_by_id(self, project_id: str) -> Project:
        """Load project by external ID."""
        ...
    
    def save(self, project_id: str, project: Project) -> None:
        """Save project changes."""
        ...

class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository
    
    def create_project(self, name: str) -> tuple[str, Project]:
        """Create new project with empty team."""
        project = Project(name=name)
        project_id = self._repository.create(project)
        return project_id, project
    
    def add_specialist(self, project_id: str, specialist: Specialist) -> None:
        """Add specialist to project team."""
        project = self._repository.get_by_id(project_id)
        project.add_specialist(specialist)
        self._repository.save(project_id, project)
```

### adapters/sheets/ Layer

**Purpose:** Thin wrapper over pygsheets, isolating domain from library specifics.

**Dependencies:** core/, pygsheets.

**Key Principle:** Domain layer MUST NOT import pygsheets directly. All spreadsheet operations go through this adapter layer.

**pygsheets Client Wrapper:**

```python
# adapters/sheets/client.py
from typing import Any, List
import pygsheets
from pygsheets import Spreadsheet, Worksheet, Cell

class PygSheetsClient:
    """Wrapper over pygsheets for spreadsheet operations."""
    
    def __init__(self, credentials_file: str) -> None:
        self._gc = pygsheets.authorize(service_file=credentials_file)
    
    def open_spreadsheet(self, spreadsheet_id: str) -> Spreadsheet:
        """Open spreadsheet by ID."""
        return self._gc.open_by_key(spreadsheet_id)
    
    def create_spreadsheet(self, title: str, folder_id: str | None = None) -> Spreadsheet:
        """Create new spreadsheet."""
        return self._gc.create(title, folder=folder_id)
    
    def copy_spreadsheet(
        self, 
        source_id: str, 
        title: str, 
        folder_id: str | None = None
    ) -> Spreadsheet:
        """Copy spreadsheet from template."""
        source = self._gc.open_by_key(source_id)
        return self._gc.drive.copy_file(source_id, title, folder_id)

    # Formula operations
    def get_cell_formula(self, worksheet: Worksheet, addr: str) -> str | None:
        """Get formula from cell (None if no formula)."""
        cell = worksheet.cell(addr)
        return cell.formula if cell.formula else None
    
    def set_cell_formula(self, worksheet: Worksheet, addr: str, formula: str) -> None:
        """Set formula in cell."""
        cell = worksheet.cell(addr)
        cell.formula = formula
        cell.update()
    
    # Range copy with stretching
    def copy_range_with_formulas(
        self,
        worksheet: Worksheet,
        source_range: str,
        dest_range: str
    ) -> None:
        """Copy range preserving formulas with relative reference adjustment."""
        worksheet.copy_range(
            source_range,
            dest_range,
            paste_type='PASTE_NORMAL'  # Preserves formulas with stretching
        )
    
    # Batch operations
    def batch_update_values(
        self,
        worksheet: Worksheet,
        updates: List[tuple[str, Any]]  # [(addr, value), ...]
    ) -> None:
        """Batch update cell values."""
        cells = []
        for addr, value in updates:
            cell = worksheet.cell(addr)
            if isinstance(value, str) and value.startswith('='):
                cell.formula = value
            else:
                cell.value = value
            cells.append(cell)
        
        worksheet.update_cells(cells)
```

**Formula Templates:**

```python
# adapters/sheets/formula_templates.py
from dataclasses import dataclass

@dataclass(frozen=True)
class FormulaTemplate:
    """Formula template with placeholder substitution."""
    template: str
    
    def render(self, **substitutions: str) -> str:
        """Render formula with substitutions."""
        result = self.template
        for key, value in substitutions.items():
            result = result.replace(f"{{{key}}}", value)
        return result

# Predefined formulas
IMPORT_TIMESHEET = FormulaTemplate(
    '=IMPORTRANGE("{spreadsheet_id}", "timesheet!A:E")'
)

CALCULATE_HOURS = FormulaTemplate(
    '=SUMIF(INDIRECT("\'"&$A{row}&"\'!$E$2:$E", true), TRIM($C{row}), INDIRECT("\'"&$A{row}&"\'!$D$2:$D", true))'
)

GROSS_TOTAL = FormulaTemplate('=$D{row}*$E{row}')
NET_TOTAL = FormulaTemplate('=$D{row}*$G{row}')
REVENUE = FormulaTemplate('=$F{row}-$H{row}')

HYPERLINK = FormulaTemplate('=HYPERLINK("{url}")')

# Usage:
# formula = IMPORT_TIMESHEET.render(spreadsheet_id="1abc123...")
# formula = GROSS_TOTAL.render(row="5")
```

**Repository Example:**

```python
# adapters/sheets/project_repository.py
from typing import Protocol
import pygsheets

from feptm.domain.models.project import Project
from feptm.domain.services.protocols import ProjectRepository
from .client import PygSheetsClient
from .formula_templates import HYPERLINK
from .mappers import project_to_row, row_to_project

class SpreadsheetProjectRepository(ProjectRepository):
    """Project repository using Google Sheets via pygsheets."""
    
    def __init__(
        self,
        client: PygSheetsClient,
        template_id: str,
        folder_id: str
    ) -> None:
        self._client = client
        self._template_id = template_id
        self._folder_id = folder_id
    
    def create(self, project: Project) -> str:
        """Create project from template, return spreadsheet ID."""
        spreadsheet = self._client.copy_spreadsheet(
            source_id=self._template_id,
            title=f"{project.name} - Project info",
            folder_id=self._folder_id
        )
        
        # Fill project info sheet
        ws = spreadsheet.worksheet_by_title("Project info")
        ws.update_value("B1", spreadsheet.id)
        ws.update_value("B2", project.name)
        ws.update_value("B3", project.created.isoformat())
        
        return spreadsheet.id
    
    def get_by_id(self, project_id: str) -> Project:
        """Load project from spreadsheet."""
        spreadsheet = self._client.open_spreadsheet(project_id)
        ws = spreadsheet.worksheet_by_title("Project info")
        
        data = ws.get_values("A1", "B10")
        return row_to_project(data, project_id)
    
    def save(self, project_id: str, project: Project) -> None:
        """Save project changes to spreadsheet."""
        spreadsheet = self._client.open_spreadsheet(project_id)
        ws = spreadsheet.worksheet_by_title("Project info")
        
        row_data = project_to_row(project)
        ws.update_values("A1", row_data)
```

### adapters/google/ Layer

**Purpose:** Google Drive API operations (folder management, file operations not covered by pygsheets).

**Dependencies:** core/, pygsheets (uses internal drive client).

```python
# adapters/google/auth.py
import pygsheets
from pathlib import Path

def authorize_pygsheets(
    credentials_file: str | Path,
    token_file: str | Path | None = None
) -> pygsheets.Client:
    """
    Authorize pygsheets client.
    
    For service account: provide service_file path.
    For OAuth: provide client_secret and optional custom credentials.
    """
    credentials_path = Path(credentials_file)
    
    if credentials_path.suffix == '.json':
        # Service account
        return pygsheets.authorize(service_file=str(credentials_path))
    else:
        # OAuth flow
        return pygsheets.authorize(
            client_secret=str(credentials_path),
            credentials_directory=str(token_file) if token_file else None
        )
```

```python
# adapters/google/drive_client.py
from typing import Optional
import pygsheets

class GoogleDriveClient:
    """Google Drive operations via pygsheets internal client."""
    
    def __init__(self, gc: pygsheets.Client) -> None:
        self._drive = gc.drive
    
    def create_folder(
        self, 
        name: str, 
        parent_id: Optional[str] = None
    ) -> str:
        """Create folder, return folder ID."""
        folder_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        
        folder = self._drive.service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        return folder['id']
    
    def move_file(self, file_id: str, folder_id: str) -> None:
        """Move file to folder."""
        self._drive.move_file(file_id, folder_id)
    
    def delete_file(self, file_id: str) -> None:
        """Delete file by ID."""
        self._drive.delete(file_id)
    
    def get_folder_url(self, folder_id: str) -> str:
        """Generate Drive folder URL."""
        return f"https://drive.google.com/drive/folders/{folder_id}"
```

### interfaces/ Layer

**Purpose:** HTTP API endpoints.

**Dependencies:** All inner layers, FastAPI.

```python
# interfaces/api/v1/projects.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from feptm.domain.services.project_service import ProjectService
from feptm.adapters.google.sheets_client import GoogleSheetsClient
from feptm.adapters.sheets.unit_of_work import UnitOfWork

router = APIRouter(prefix="/projects", tags=["projects"])

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)

class CreateProjectResponse(BaseModel):
    project_id: str
    drive_folder_url: str
    project_info_url: str
    report_url: str
    calculations_url: str

def get_project_service() -> ProjectService:
    # Dependency injection setup
    ...

@router.post("/create", response_model=CreateProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service)
) -> CreateProjectResponse:
    try:
        project_id, project = service.create_project(request.name)
        # Map to response
        ...
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Testing Strategy

### Unit Tests

**Location:** `tests/unit/`

**Scope:** Domain services, spreadsheet abstractions.

**Mocking:** In-memory implementations of repositories and clients.

```python
# tests/unit/domain/test_project_service.py
import pytest
from feptm.domain.models.project import Project
from feptm.domain.services.project_service import ProjectService

class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._counter = 0
    
    def create(self, project: Project) -> str:
        self._counter += 1
        project_id = f"project_{self._counter}"
        self._projects[project_id] = project
        return project_id
    
    def get_by_id(self, project_id: str) -> Project:
        return self._projects[project_id]
    
    def save(self, project_id: str, project: Project) -> None:
        self._projects[project_id] = project

@pytest.fixture
def project_service() -> ProjectService:
    return ProjectService(repository=InMemoryProjectRepository())

def test_create_project_returns_id_and_project(project_service: ProjectService) -> None:
    project_id, project = project_service.create_project("Test Project")
    
    assert project_id == "project_1"
    assert project.name == "Test Project"
    assert project.team == []
```

```python
# tests/unit/adapters/sheets/test_formula_templates.py
import pytest
from feptm.adapters.sheets.formula_templates import (
    FormulaTemplate,
    IMPORT_TIMESHEET,
    GROSS_TOTAL,
    HYPERLINK
)

def test_formula_template_renders_single_substitution() -> None:
    result = IMPORT_TIMESHEET.render(spreadsheet_id="abc123")
    
    assert result == '=IMPORTRANGE("abc123", "timesheet!A:E")'

def test_formula_template_renders_row_number() -> None:
    result = GROSS_TOTAL.render(row="5")
    
    assert result == "=$D5*$E5"

def test_formula_template_renders_multiple_placeholders() -> None:
    template = FormulaTemplate('=IF({cond}, "{true_val}", "{false_val}")')
    result = template.render(cond="A1>0", true_val="Yes", false_val="No")
    
    assert result == '=IF(A1>0, "Yes", "No")'

def test_hyperlink_formula_renders_url() -> None:
    result = HYPERLINK.render(url="https://example.com")
    
    assert result == '=HYPERLINK("https://example.com")'
```

### Integration Tests

**Location:** `tests/integration/`

**Scope:** API endpoints with mocked Google services.

**Setup:** Use `httpx.AsyncClient` with `TestClient`.

```python
# tests/integration/api/test_projects_api.py
import pytest
from httpx import AsyncClient
from feptm.main import create_app

@pytest.fixture
async def client() -> AsyncClient:
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_create_project_returns_urls(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/projects/create",
        json={"name": "Integration Test Project"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert "drive_folder_url" in data
```

## Dependency Rules

| Layer | MAY depend on | MUST NOT depend on |
|-------|---------------|-------------------|
| core/ | External libs only | domain/, adapters/, interfaces/ |
| domain/ | core/ | adapters/, interfaces/ |
| adapters/ | core/, domain/ (protocols only) | interfaces/ |
| interfaces/ | All layers | — |

## Configuration

### pyproject.toml

```toml
[project]
name = "feptm"
version = "0.2.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.2.0",
    "uvicorn>=0.29.0",
    "pygsheets>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "httpx>=0.27.0",
    "black>=24.0.0",
    "isort>=5.13.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
]

[tool.black]
line-length = 88

[tool.isort]
profile = "black"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.coverage.run]
source = ["src/feptm"]
branch = true

[tool.coverage.report]
fail_under = 80
```

### Commands (uv)

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=feptm --cov-report=term-missing

# Format code
uv run black src/ tests/
uv run isort src/ tests/

# Type check
uv run mypy src/

# Lint
uv run ruff check src/ tests/

# Run server
uv run uvicorn feptm.main:app --reload
```

## Migration Notes

Migration from current architecture to target architecture SHOULD be incremental:

1. Add `pygsheets` dependency, keep `google-api-python-client` temporarily
2. Create `adapters/sheets/client.py` wrapping pygsheets
3. Create domain models without Google IDs
4. Implement repository interfaces using pygsheets
5. Migrate services one by one to use new repositories
6. Update API endpoints to use new services
7. Remove `google-api-python-client` and legacy code

## Out of Scope

- Authentication/authorization (Google handles)
- Caching layer
- Database persistence
- Event sourcing
- CQRS pattern
