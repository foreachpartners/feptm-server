# Tasks: WF-14-event-loop-blocking-async-handlers-by

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Config: Add WORKERS and GOOGLE_API_TIMEOUT settings | AR-ARCH-007 | — | done | 2026-09-05T12:00 |
| T-02 | Singleton: Cache GoogleSheetsService in dependencies.py | AR-ARCH-007 | T-01 | done | 2026-09-05T12:01 |
| T-03 | Timeout: Add HTTP timeout to GoogleSheetsService.initialize() | AR-ARCH-007 | T-01 | done | 2026-09-05T12:02 |
| T-04 | Workers: Configure uvicorn workers in run_api.py | AR-ARCH-007 | T-01 | done | 2026-09-05T12:03 |
| T-05 | Handler: Wrap projects.py blocking calls with asyncio.to_thread | AR-ARCH-006 | T-02, T-03 | done | 2026-09-05T12:04 |
| T-06 | Handler: Wrap periods.py blocking calls with asyncio.to_thread | AR-ARCH-006 | T-02, T-03 | done | 2026-09-05T12:05 |
| T-07 | Audit: Full repo audit — zero ERR, zero WARN in touched files | AR-ARCH-006, AR-ARCH-007 | T-01..T-06 | done | 2026-09-05T12:06 |
