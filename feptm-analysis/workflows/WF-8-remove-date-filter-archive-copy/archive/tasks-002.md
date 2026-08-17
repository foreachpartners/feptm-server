# Tasks: WF-8 fix2 — Archive before timesheet update

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Service: Reorder `close_period()` — archive FIRST, then update timesheets | FR-PAYMENT-001 | — | done | 2026-08-17T21:02 |
| T-02 | Tests: Update close_period tests to verify archive-before-update order | FR-PAYMENT-001 | T-01 | done | 2026-08-17T21:02 |
| T-03 | Audit: Full repo audit — zero ERR, zero WARN in touched files | FR-PAYMENT-001 | T-01–T-02 | done | 2026-08-17T21:03 |
