# Tasks: Enforce strict DD.MM.YYYY date format in close_period

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-51 | Storage: Strip _serial_to_date to %d.%m.%Y only, remove dead code | FR-PAYMENT-001 | — | done | 2026-08-11T23:52 |
| T-52 | Storage: close_period_in_timesheet — log.error + raise on invalid date | FR-PAYMENT-001 | T-51 | done | 2026-08-11T23:52 |
| T-53 | Storage: _sum_period_hours — log.error + raise on invalid date | FR-PAYMENT-001 | T-51 | done | 2026-08-11T23:52 |
| T-54 | Tests: Update for strict date format, add rejection tests | FR-PAYMENT-001 | T-53 | done | 2026-08-11T23:55 |
| T-55 | Audit: Full repo audit — zero ERR/WARN in touched files | FR-PAYMENT-001 | T-54 | done | 2026-08-11T23:55 |
