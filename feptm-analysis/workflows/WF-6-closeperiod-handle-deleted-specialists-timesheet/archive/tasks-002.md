# WF-6: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Contract: add `get_stale_specialists()` to `ProjectStorageProtocol` | FR-SPECIALIST-001, FR-PAYMENT-001 | — | done | 2026-08-12 |
| T-02 | Storage: add `valueRenderOption="UNFORMATTED_VALUE"` to `_read_current_period()` | FR-SPECIALIST-001, FR-PAYMENT-001 | — | done | 2026-08-12 |
| T-03 | Storage: implement `get_stale_specialists()` in `ProjectStorage` | FR-SPECIALIST-001, FR-PAYMENT-001 | T-01, T-02 | done | 2026-08-12 |
| T-04 | Service: modify `close_period()` to process stale specialists | FR-SPECIALIST-001, FR-PAYMENT-001 | T-01, T-03 | done | 2026-08-12 |
| T-05 | Typecheck: `make typecheck` in feptm-server | — | T-01, T-02, T-03, T-04 | done | 2026-08-12 |
| T-06 | Audit: `verify --phase implement` — zero ERR, zero WARN | FR-SPECIALIST-001, FR-PAYMENT-001 | T-05 | done | 2026-08-12 |
