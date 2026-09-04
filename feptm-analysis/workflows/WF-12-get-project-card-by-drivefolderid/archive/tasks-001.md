# Tasks: GET /api/projects/{drive_folder_id}/

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Models: ProjectCardTable, ProjectCardTimesheet, ProjectCardResponse in models/project.py; export from models/__init__.py | FR-PROJECT-001, FR-SHEET-001 | — | done | 2026-09-04T21:34 |
| T-02 | Exceptions: ProjectFolderNotFoundError, ProjectSpreadsheetNotFoundError in core/exceptions.py | FR-PROJECT-001, FR-SHEET-001 | — | done | 2026-09-04T21:34 |
| T-03 | GoogleSheetsService: list_drive_spreadsheets() method | FR-SHEET-001 | — | done | 2026-09-04T21:34 |
| T-04 | ProjectStorageProtocol: add get_project_card() signature | FR-PROJECT-001, FR-SHEET-001 | T-03 | done | 2026-09-04T21:34 |
| T-05 | ProjectStorage: implement get_project_card() | FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001 | T-02, T-03, T-04 | done | 2026-09-04T21:34 |
| T-06 | TimesheetProjectService: add get_project_card() facade method | FR-PROJECT-001, FR-SHEET-001 | T-05 | done | 2026-09-04T21:34 |
| T-07 | API handler: GET /{drive_folder_id}/ in api/v1/projects.py | FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001 | T-01, T-02, T-06 | done | 2026-09-04T21:34 |
| T-08 | Tests: 7 tests in tests/api/v1/test_projects.py | FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001 | T-07 | done | 2026-09-04T21:34 |
| T-09 | Verification: make lint && make typecheck && make test | FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001 | T-08 | done | 2026-09-04T21:35 |
| T-10 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001 | T-09 | done | 2026-09-04T21:35 |
