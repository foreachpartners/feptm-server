## TL;DR

This project does **not** run on Google Cloud infrastructure. It uses Google Sheets
as a database and Google Drive as file storage. Google requires all apps accessing
their APIs to register in the Google Cloud Console to obtain credentials — this is
Google's universal developer portal, not cloud hosting.

## What the project uses from Google

| Service | Role | API |
|---------|------|-----|
| Google Sheets | Database (projects, specialists, timesheets, formulas) | Sheets API v4 |
| Google Drive | File storage (project folders, templates) | Drive API v3 |
| Google Cloud Console | One-time: issue API credentials | IAM / OAuth |

## Why the Console is unavoidable

| Reason | Explanation |
|--------|------------|
| **API enablement** | Drive and Sheets APIs must be explicitly activated per project |
| **Credential issuance** | OAuth client IDs and service account keys are created here |
| **Quota tracking** | Google tracks and enforces API call limits per project |

Google provides **no way** to programmatically access Sheets or Drive without
registering in the Console. This is true for any third-party app that integrates
with Google Workspace.

## Current auth method: OAuth 2.0 (complex)

- Requires OAuth consent screen + Desktop client ID in the Console
- Interactive browser-based login at first run
- Token refresh handling (`~/.google_sheets_token.json`)
