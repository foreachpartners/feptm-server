# Tasks: Fix close_period 404 — spreadsheet URL vs ID mismatch

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-44 | Storage: Write bare IDs in _apply_updates instead of full URLs | FR-SPECIALIST-001 | — | done | 2026-08-11T21:16 |
| T-45 | Storage: Defensive extract_id_from_hyperlink_formula in close_period_in_timesheet | FR-PAYMENT-001 | — | done | 2026-08-11T21:17 |
| T-46 | Service: Normalize sp.timesheet with extract_id_from_hyperlink_formula in close_period | FR-PAYMENT-001 | — | done | 2026-08-11T21:18 |
| T-47 | Audit: Full repo audit — zero ERR/WARN in touched files | FR-PAYMENT-001, FR-SPECIALIST-001 | T-46 | done | 2026-08-11T21:19 |
