# FEPTM Server - Time & Materials Accounting Backend

Backend service for automating time and materials accounting using Google Sheets as the single source of truth.

## Overview

FEPTM (FEP Time & Materials) server provides automation for project management, team tracking, and timesheet synchronization with Google Sheets. The system uses Google Sheets as the primary interface where all calculations are performed, while the backend handles operations like project creation, team changes, and payment period closures.

## Architecture

The application follows a clean architecture pattern with clear separation of concerns:

```text
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
- Google credentials file (`credentials.json`)

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

4. Place Google credentials in project root as `credentials.json`

   **Option A: Service Account (Recommended for production)**

   **Step 1: Create Service Account**

   1. Go to [Google Cloud Console](https://console.cloud.google.com/)
   2. Select your project or create a new one
   3. Enable **Google Sheets API** and **Google Drive API**:
      - Go to **APIs & Services** > **Library**
      - Search for "Google Sheets API" and click **Enable**
      - Search for "Google Drive API" and click **Enable**
   4. Go to **IAM & Admin** > **Service Accounts**
   5. Click **Create Service Account**
   6. Fill in the service account details:
      - Service account name: e.g., "feptm-server"
      - Service account ID: auto-generated
   7. Click **Create and Continue**
   8. Grant necessary roles (optional for API access, but recommended):
      - **Editor** role (or specific roles like "Service Account User")
   9. Click **Continue** > **Done**
   10. Click on the created service account > **Keys** tab
   11. Click **Add Key** > **Create new key**
   12. Select **JSON** format and click **Create**
   13. Save the downloaded JSON file as `credentials.json` in the project root

   **Step 2: Grant Access to Files and Folders**

   Service account needs explicit access to all Google Drive files and folders it will use.

   1. **Find your service account email:**
      - **Quick method:** Run `uv run python bin/get_service_account_email.py`
      - **Manual method:** Open `credentials.json` in a text editor
        - Find the `client_email` field (e.g., `feptm-server@your-project.iam.gserviceaccount.com`)
        - Copy this email address

   2. **Share templates with service account:**
      - Open Google Drive in your browser
      - Find each template spreadsheet (Project Info, Report, Calculations, Timesheet)
      - Right-click on the file > **Share**
      - Paste the service account email in "Add people and groups"
      - Set permission to **Editor**
      - Click **Send** (uncheck "Notify people" if you want)
      - Repeat for all template spreadsheets

   3. **Share parent folder with service account:**
      - If you use `GOOGLE_PROJECTS_FOLDER_ID`, share that folder with service account email
      - Right-click folder > **Share** > Add service account email as **Editor**
      - This allows service account to create projects inside the folder

   4. **Verify access:**
      - Service account can only access files/folders explicitly shared with it
      - Files created by service account belong to the service account (visible in its Drive)
      - To access files created by service account, share them back to your user account

   **Important Notes:**
   - Service account has its own Google Drive storage (15GB free)
   - If you see "storage quota exceeded" error, check service account's Drive quota
   - Files copied/created by service account count against service account's quota, not yours
   - Consider using OAuth (Option B) if you need to use your personal Drive quota

   **Option B: OAuth 2.0 Client (For user-specific access)**

   Use OAuth if you want to use your personal Google Drive quota and have direct access to files.

   **Step 1: Create OAuth Credentials**

   1. Go to [Google Cloud Console](https://console.cloud.google.com/)
   2. Select your project
   3. Enable **Google Sheets API** and **Google Drive API**:
      - Go to **APIs & Services** > **Library**
      - Search for "Google Sheets API" and click **Enable**
      - Search for "Google Drive API" and click **Enable**
   4. Go to **APIs & Services** > **Credentials**
   5. Click **Create Credentials** > **OAuth client ID**
   6. If prompted, configure OAuth consent screen:
      - Choose **External** user type (or **Internal** if using Google Workspace)
      - Fill in required fields:
        - App name: e.g., "FEPTM Server"
        - User support email: your email
        - Developer contact: your email
      - Add scopes:
        - `https://www.googleapis.com/auth/spreadsheets`
        - `https://www.googleapis.com/auth/drive`
      - Add test users if needed (for external apps in testing mode)
      - Click **Save and Continue** > **Save and Continue** > **Back to Dashboard**
   7. Select **Desktop app** as application type
   8. Click **Create**
   9. Download the JSON file and save it as `credentials.json` in the project root

   **Step 2: Authenticate (First Run Only)**

   1. On first run, you'll be prompted to authenticate via browser
   2. A URL will be printed in console - open it in browser
   3. Grant permissions for Sheets and Drive access
   4. Copy the authorization code from browser
   5. Paste it in terminal when prompted
   6. Token will be saved for future use (no need to re-authenticate)

   **Advantages of OAuth:**
   - Uses your personal Google Drive quota
   - Direct access to files in your Drive
   - No need to share files/folders manually

## Running the Application

### Development Server

Run from project root directory:

```bash
uv run python -m bin.run_api
```

Or using uvicorn directly:

```bash
uv run uvicorn feptm.main:app --reload --host 0.0.0.0 --port 8000
```

**Note:** Application entry point is `src/feptm/main.py`. The `bin/run_api.py` script automatically adds `src` to Python path.

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

## Quick Start: Grant Access to Service Account

If you're using Service Account (Option A), run this command to get the service account email:

```bash
uv run python bin/get_service_account_email.py
```

Then share all template spreadsheets and parent folder with this email address as **Editor** in Google Drive.

## Configuration

Key environment variables (see `env.example`):

- `GOOGLE_CREDENTIALS_FILE` - Optional override path to credentials file (default: `credentials.json` in project root)
- `GOOGLE_PROJECT_INFO_TEMPLATE_ID` - Template spreadsheet ID for project info
- `GOOGLE_PROJECT_REPORT_TEMPLATE_ID` - Template for General Expenses report
- `GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID` - Template for Payment Distribution
- `GOOGLE_TIMESHEET_TEMPLATE_ID` - Template for specialist timesheets
- `GOOGLE_PROJECTS_FOLDER_ID` - Google Drive folder ID for projects (must be shared with service account if using Option A)

### Finding Spreadsheet and Folder IDs

1. **Spreadsheet ID:**
   - Open spreadsheet in browser
   - URL format: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
   - Copy the `{SPREADSHEET_ID}` part

2. **Folder ID:**
   - Open folder in Google Drive
   - URL format: `https://drive.google.com/drive/folders/{FOLDER_ID}`
   - Copy the `{FOLDER_ID}` part

3. **Service Account Email:**
   - Open `credentials.json`
   - Find `"client_email"` field
   - Copy the email (e.g., `xxx@xxx.iam.gserviceaccount.com`)

### Troubleshooting Access Issues

**Error: "storage quota exceeded"**
- Service account has its own 15GB Drive quota
- Check service account's Drive usage in [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts)
- Or switch to OAuth (Option B) to use your personal quota

**Error: "Permission denied" or "File not found"**
- Ensure all template spreadsheets are shared with service account email as Editor
- Ensure parent folder (`GOOGLE_PROJECTS_FOLDER_ID`) is shared with service account as Editor
- For OAuth: ensure you granted all required permissions during authentication

**Finding service account's Drive files:**
- Files created by service account are in service account's Drive (not visible in your Drive by default)
- To access: share the file/folder with your personal email, or use OAuth instead

## Project Structure

```text
feptm-server/
├── src/
│   └── feptm/              # Main package
│       ├── domain/         # Business logic, domain models, service protocols
│       ├── adapters/       # Google Sheets integration via pygsheets, Google Drive operations
│       ├── interfaces/     # FastAPI endpoints, request/response models
│       ├── core/           # Configuration, exceptions, logging utilities
│       └── main.py         # FastAPI application entry point (DO NOT MOVE)
├── bin/
│   └── run_api.py          # Server startup script (adds src to PYTHONPATH)
├── tests/                  # Test suite
├── credentials.json        # Google credentials (MUST be in project root)
└── .env                    # Environment variables
```

**Important Notes:**
- Main application entry point: `src/feptm/main.py`
- Credentials file `credentials.json` MUST be placed in project root directory
- The `bin/run_api.py` script automatically adds `src/` to Python path, allowing imports
- Always run the server from project root: `uv run python -m bin.run_api`

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
