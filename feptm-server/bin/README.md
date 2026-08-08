# Google Sheets Explorer

This utility script allows you to interact with Google Sheets, explore folders, and create test spreadsheets.

## Prerequisites

1. Create a Google Cloud project and enable the Google Drive API and Google Sheets API
2. Create OAuth 2.0 credentials (OAuth client ID) for a desktop application
3. Download the credentials JSON file and place it in one of the standard locations:
   - `credentials.json` (in the project root)
   - `backend/credentials.json` (recommended location)
   - `~/.config/google/credentials.json` (system-wide location)

## Installation

The required dependencies are already included in the project's `pyproject.toml`:

- google-api-python-client
- google-auth
- google-auth-oauthlib

## Usage

```bash
# List all Google Sheets in a folder
python -m backend.bin.google_sheets_explorer --folder FOLDER_ID

# Create a test spreadsheet in a folder
python -m backend.bin.google_sheets_explorer --folder FOLDER_ID --create-test

# Create a test spreadsheet with a custom name
python -m backend.bin.google_sheets_explorer --folder FOLDER_ID --create-test --name "My Test Spreadsheet"

# Specify a non-standard credentials file location
python -m backend.bin.google_sheets_explorer --credentials /custom/path/to/credentials.json --folder FOLDER_ID

# Specify a custom token file location
python -m backend.bin.google_sheets_explorer --folder FOLDER_ID --token /path/to/token.json
```

## Getting a Folder ID

To find a Google Drive folder ID:

1. Open the folder in Google Drive
2. The folder ID is in the URL: `https://drive.google.com/drive/folders/FOLDER_ID`

## First-time Authentication

When you run the script for the first time, it will:

1. Find the credentials file in one of the standard locations
2. Open a browser window for you to log in to your Google account
3. Ask for permission to access your Google Drive and Sheets
4. Store the authentication token in the specified token file (defaults to `~/.google_sheets_token.json` in your home directory)

## Example Output

```
2023-04-21 14:32:45 - __main__ - INFO - Found credentials file at: backend/credentials.json
2023-04-21 14:32:45 - __main__ - INFO - GoogleSheetsExplorer initialized with credentials file: backend/credentials.json
2023-04-21 14:32:45 - __main__ - INFO - Token file: /home/user/.google_sheets_token.json
2023-04-21 14:32:46 - __main__ - INFO - Google Drive and Sheets services initialized successfully
2023-04-21 14:32:47 - __main__ - INFO - Folder: My Google Sheets (ID: 1a2b3c4d5e6f7g8h9i)
2023-04-21 14:32:47 - __main__ - INFO - Found 3 Google Sheets files in folder 1a2b3c4d5e6f7g8h9i

2023-04-21 14:32:47 - google_sheets_explorer - INFO - Google Sheets files in folder:
2023-04-21 14:32:47 - google_sheets_explorer - INFO - 1. Budget 2023 (ID: abcd1234efgh5678)
2023-04-21 14:32:47 - google_sheets_explorer - INFO -    Created: 2023-01-15T10:30:00.000Z, Modified: 2023-04-20T15:45:00.000Z
2023-04-21 14:32:47 - google_sheets_explorer - INFO - 2. Project Timeline (ID: ijkl9012mnop3456)
2023-04-21 14:32:47 - google_sheets_explorer - INFO -    Created: 2023-02-10T09:15:00.000Z, Modified: 2023-04-18T11:20:00.000Z
2023-04-21 14:32:47 - google_sheets_explorer - INFO - 3. Team Contacts (ID: qrst7890uvwx1234)
2023-04-21 14:32:47 - google_sheets_explorer - INFO -    Created: 2023-03-05T14:00:00.000Z, Modified: 2023-04-15T16:30:00.000Z
``` 