# WF-7: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Service: set `sp.project` in `sync_project_specialists()` | FR-PAYMENT-001 | — | pending | |
| T-02 | Service: set `sp.project` in `sync_project_rates()` | FR-PAYMENT-001 | — | pending | |
| T-03 | Service: set `sp.project` on stale specialists in `close_period()` | FR-PAYMENT-001 | — | pending | |
| T-04 | Storage: column J formula in `_write_specialist_fields()` for Payment Distribution | FR-PAYMENT-001 | T-01, T-02 | pending | |
| T-05 | Storage: column J text value in `archive_current_period()` for Payment Distribution | FR-PAYMENT-001 | T-03 | pending | |
| T-06 | Typecheck + verify | — | T-01–T-05 | pending | |
