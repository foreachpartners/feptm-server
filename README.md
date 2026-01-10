# FEPTM Server - Time & Materials Accounting Backend

Backend service for automating time and materials accounting using Google Sheets as the single source of truth.

## Overview

FEPTM (FEP Time & Materials) server provides automation for project management, team tracking, and timesheet synchronization with Google Sheets. The system uses Google Sheets as the primary interface where all calculations are performed, while the backend handles operations like project creation, team changes, and payment period closures.

## Architecture

The application follows a clean architecture pattern with clear separation of concerns:

```
src/feptm/
├── domain/           # Business logic and domain models (infrastructure-agnostic)
│   ├── models/       # Domain entities (Project, Specialist, PaymentPeriod)
│   └── services/     # Domain services and repository protocols
├── adapters/         # External integrations
│   ├── google/       # Google API adapters (auth, drive)
│   └── sheets/       # Google Sheets adapter using pygsheets
├── interfaces/       # HTTP API endpoints (FastAPI)
│   └── api/v1/       # API v1 endpoints
└── core/             # Core utilities (config, exceptions, logging)
```

### Key Principles

- **Domain models are infrastructure-agnostic**: No Google IDs in domain models
- **Repository pattern**: Abstracts data access from Google Sheets
- **Dependency injection**: Services injected via FastAPI Depends
- **Formula preservation**: Formulas maintained as formulas during sync
- **Rate periods support (FR-002.1)**: Specialists can have multiple rate periods over time

## Technology Stack

- **Python 3.12+**
- **FastAPI 0.110.0+** - Web framework
- **pygsheets 2.0.0+** - Google Sheets integration
- **pydantic 2.0.0+** - Data validation
- **pytest 8.3.5+** - Testing framework
- **uv** - Package management

## Setup and Installation

### Prerequisites

- Python 3.12 or higher
- Google Cloud Project with Sheets API and Drive API enabled
- OAuth 2.0 credentials file (`credentials.json`)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd feptm-server
   ```

2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

3. Configure environment variables:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. Place Google OAuth credentials in project root as `credentials.json`

## Running the Application

### Development Server

```bash
uv run python -m bin.run_api
```

Or using uvicorn directly:

```bash
uv run uvicorn feptm.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server

```bash
uv run uvicorn feptm.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Projects

- `POST /api/v1/projects/create` - Create new project
- `POST /api/v1/projects/sync` - Synchronize project specialists

### Specialists

- `GET /api/v1/specialists/project/{project_id}` - Get project specialists

### Periods

- `POST /api/v1/periods/close` - Close payment period (TODO)

## Testing

Run all tests:

```bash
uv run pytest
```

Run with coverage:

```bash
uv run pytest --cov=src/feptm --cov-report=term-missing
```

Target coverage: ≥80%

Run specific test categories:

```bash
uv run pytest tests/unit/          # Unit tests only
uv run pytest tests/integration/   # Integration tests only
```

## Code Quality

### Type Checking

```bash
uv run mypy src/
```

### Linting

```bash
uv run ruff check src/
uv run black --check src/
uv run isort --check src/
```

### Formatting

```bash
uv run black src/
uv run isort src/
```

## Configuration

Key environment variables (see `env.example`):

- `GOOGLE_CREDENTIALS_FILE` - Path to OAuth credentials JSON
- `GOOGLE_PROJECT_INFO_TEMPLATE_ID` - Template spreadsheet ID for project info
- `GOOGLE_PROJECT_REPORT_TEMPLATE_ID` - Template for General Expenses report
- `GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID` - Template for Payment Distribution
- `GOOGLE_TIMESHEET_TEMPLATE_ID` - Template for specialist timesheets
- `GOOGLE_PROJECTS_FOLDER_ID` - Google Drive folder for projects

## Project Structure

- **Domain Layer** (`domain/`): Business logic, domain models, service protocols
- **Adapters Layer** (`adapters/`): Google Sheets integration via pygsheets, Google Drive operations
- **Interfaces Layer** (`interfaces/`): FastAPI endpoints, request/response models
- **Core** (`core/`): Configuration, exceptions, logging utilities

## Features

### FR-001: Project Creation

Creates project structure with:
- Google Drive folder
- Project Info spreadsheet
- General Expenses report spreadsheet
- Payment Distribution calculations spreadsheet

### FR-002: Team Member Addition

When specialist added to Team sheet:
- Creates personal timesheet from template
- Updates Team sheet with timesheet ID
- Creates specialist tabs in reports with IMPORTRANGE formulas
- Applies calculation formulas to Current Period sheets

### FR-002.1: Specialist Rate Periods

Supports multiple rate periods per specialist:
- Rate lookup based on timesheet entry date
- Multiple rows in Team sheet with same Timesheet ID represent rate history
- Formulas handle period-appropriate rates

### FR-004: Payment Period Close

Automates period closure (future enhancement):
- Period name propagation
- Snapshot creation

## Development

### Adding New Features

1. Define domain model in `domain/models/`
2. Create repository protocol in `domain/services/protocols.py`
3. Implement repository in `adapters/sheets/`
4. Create domain service in `domain/services/`
5. Add API endpoint in `interfaces/api/v1/`
6. Write tests in `tests/unit/` and `tests/integration/`

### Code Style

Follow PEP 8, use type hints, Google-style docstrings. See `.cursor/rules/python/` for detailed guidelines.

## License

Proprietary
