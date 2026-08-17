# Tasks: WF-8 — Remove date filter, copy Current Period for archive

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Model: Remove `start_date`/`end_date` from `ClosePeriodRequest` | FR-PAYMENT-001 | — | done | 2026-08-17T20:20 |
| T-02 | Protocol: Update `close_period_in_timesheet` and `archive_current_period` signatures | FR-PAYMENT-001 | T-01 | done | 2026-08-17T20:22 |
| T-03 | Storage: Rewrite `close_period_in_timesheet` without date filter | FR-PAYMENT-001 | T-02 | done | 2026-08-17T20:25 |
| T-04 | Storage: Rewrite `archive_current_period` to use `duplicateSheet` | FR-PAYMENT-001 | T-02 | done | 2026-08-17T20:30 |
| T-05 | Storage: Remove `_sum_period_hours` and `_serial_to_date` | FR-PAYMENT-001 | T-03, T-04 | done | 2026-08-17T20:35 |
| T-06 | Service: Remove `_has_invalid_dates` and update `close_period` | FR-SPECIALIST-001 | T-02 | done | 2026-08-17T20:40 |
| T-07 | API: Update `close_payment_period` handler | FR-PAYMENT-001 | T-06 | done | 2026-08-17T20:42 |
| T-08 | Tests: Update model tests for `ClosePeriodRequest` | FR-PAYMENT-001 | T-01 | done | 2026-08-17T20:45 |
| T-09 | Tests: Update API tests for `PUT /api/periods` | FR-PAYMENT-001 | T-07 | done | 2026-08-17T20:47 |
| T-10 | Tests: Update service/storage tests for new signatures | FR-PAYMENT-001, FR-SPECIALIST-001 | T-06 | done | 2026-08-17T20:50 |
| T-11 | Audit: Full repo audit — zero ERR, zero WARN in touched files | FR-PAYMENT-001, FR-SPECIALIST-001 | T-01–T-10 | done | 2026-08-17T20:52 |
