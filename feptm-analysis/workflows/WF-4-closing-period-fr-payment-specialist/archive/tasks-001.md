# Tasks: Close Payment Period (FR-PAYMENT-001)

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Models: Create `src/feptm/models/payment_period.py` with ClosePeriodRequest, ClosePeriodResponse | FR-PAYMENT-001 | — | done | 2026-08-09T20:10 |
| T-02 | Models: Update `src/feptm/models/__init__.py` exports | FR-PAYMENT-001 | T-01 | done | 2026-08-09T20:11 |
| T-03 | Config: Add timesheet ColumnName enums and TIMESHEET_DATA RangeFormat to `config_service.py` | FR-PAYMENT-001 | — | done | 2026-08-09T20:11 |
| T-04 | Protocol: Add close_period_in_timesheet, archive_current_period, protect_archived_sheet to `protocols.py` | FR-PAYMENT-001 | T-01 | done | 2026-08-09T20:12 |
| T-05 | Storage: Implement close_period_in_timesheet in `project_storage.py` | FR-PAYMENT-001 | T-03, T-04 | done | 2026-08-09T20:14 |
| T-06 | Storage: Implement archive_current_period in `project_storage.py` | FR-PAYMENT-001 | T-03, T-04 | done | 2026-08-09T20:14 |
| T-07 | Storage: Implement protect_archived_sheet in `project_storage.py` | FR-PAYMENT-001 | T-03, T-04 | done | 2026-08-09T20:14 |
| T-08 | Service: Add close_period to TimesheetProjectService in `project_service.py` | FR-PAYMENT-001 | T-05, T-06, T-07 | done | 2026-08-09T20:15 |
| T-09 | API: Create `src/feptm/api/v1/periods.py` with PUT /api/periods handler | FR-PAYMENT-001 | T-02, T-08 | done | 2026-08-09T20:16 |
| T-10 | API: Register periods router in `api/router.py` | FR-PAYMENT-001 | T-09 | done | 2026-08-09T20:16 |
| T-11 | Tests: Create `tests/models/test_payment_period.py` | FR-PAYMENT-001 | T-01 | done | 2026-08-09T20:18 |
| T-12 | Tests: Create `tests/api/v1/test_periods.py` | FR-PAYMENT-001 | T-09, T-10 | done | 2026-08-09T20:19 |
| T-13 | Tests: Add close_period tests to `tests/timesheets/test_project_service.py` | FR-PAYMENT-001 | T-08 | done | 2026-08-09T20:19 |
| T-14 | Audit: Full repo audit — zero ERR, zero WARN in touched files | FR-PAYMENT-001 | T-01..T-13 | done | 2026-08-09T20:20 |
| T-15 | Storage: Fix archive_current_period to compute values from timesheet data instead of reading zeros | FR-PAYMENT-001 | T-06 | done | 2026-08-09T20:55 |
