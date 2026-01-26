# FEPTM Server

Backend for time & materials accounting with Google Sheets.

## Requirements

- Python 3.12+
- Google Cloud Project with Sheets API and Drive API enabled
- OAuth credentials (`credentials.json`)

## Installation

```bash
git clone <repository-url>
cd feptm-server
uv sync
cp .env.example .env
```

## Google OAuth Setup

Service accounts cannot own files in Google Drive. Use OAuth for personal accounts.

### Step 1: Create OAuth Credentials

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select project
3. Enable APIs:
   - **APIs & Services** > **Library**
   - Enable "Google Sheets API"
   - Enable "Google Drive API"
4. Configure OAuth consent screen:
   - **APIs & Services** > **OAuth consent screen**
   - User type: External
   - App name: "FEPTM Server"
   - Scopes: `spreadsheets`, `drive`
   - Add your email as test user
5. Create credentials:
   - **APIs & Services** > **Credentials**
   - **Create Credentials** > **OAuth client ID**
   - Application type: **Desktop app**
   - Download JSON, save as `credentials.json` in project root

### Step 2: First Run Authentication

On first run, browser opens for authorization. Grant access to Sheets and Drive. Token saved automatically.

## Configuration

Edit `.env`:

```bash
# Required: Template spreadsheet IDs
GOOGLE_PROJECT_INFO_TEMPLATE_ID=<spreadsheet_id>
GOOGLE_PROJECT_REPORT_TEMPLATE_ID=<spreadsheet_id>
GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID=<spreadsheet_id>
GOOGLE_TIMESHEET_TEMPLATE_ID=<spreadsheet_id>

# Optional: Parent folder for projects
GOOGLE_PROJECTS_FOLDER_ID=<folder_id>
```

### Finding IDs

- **Spreadsheet ID:** `https://docs.google.com/spreadsheets/d/{ID}/edit`
- **Folder ID:** `https://drive.google.com/drive/folders/{ID}`

## Running

```bash
make run      # Production
make run-dev  # Development (auto-reload)
```

Or directly:

```bash
uv run python -m bin.run_api
```

Server runs at `http://0.0.0.0:8000`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/projects/create` | Create project |
| POST | `/api/v1/projects/sync` | Sync specialists |
| GET | `/api/v1/specialists/project/{id}` | Get specialists |

## Testing

```bash
make test              # Run tests
make test-coverage     # Run with coverage
```

## Code Quality

```bash
make lint       # Linting
make format     # Format code
make typecheck  # Type checking
make all        # All checks
```

## Project Structure

```
feptm-server/
├── src/feptm/
│   ├── domain/       # Business logic, models
│   ├── adapters/     # Google Sheets/Drive integration
│   ├── interfaces/   # FastAPI endpoints
│   └── core/         # Config, exceptions, logging
├── bin/              # Scripts
├── tests/            # Test suite
├── credentials.json  # OAuth credentials (project root)
└── .env              # Environment config
```

## Troubleshooting

**"Permission denied" or "File not found"**
- Verify OAuth authentication completed successfully
- Check template IDs are correct
- Ensure templates are accessible to your Google account

**Token expired**
- Delete `~/.google_sheets_token.json`
- Restart server to re-authenticate

## Service Account (Google Workspace only)

Service accounts work only with Shared Drives (Google Workspace). For personal accounts, use OAuth.

If using Google Workspace:
1. Create service account in Cloud Console
2. Create Shared Drive, add service account as Content Manager
3. Place templates and projects folder in Shared Drive
4. Use service account JSON as `credentials.json`

## License

Proprietary
