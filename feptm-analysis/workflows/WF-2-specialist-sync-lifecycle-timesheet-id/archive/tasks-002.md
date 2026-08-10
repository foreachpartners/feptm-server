# Tasks: Fix Current Period sync — new specialist rows show only names

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Storage: split `_copy_row_formatting` PASTE_NORMAL into PASTE_FORMULA + PASTE_FORMAT in batchUpdate | FR-SYNC-001 | — | done | 2026-08-10T12:30 |
| T-02 | Tests: verify `_copy_row_formatting` sends two copyPaste requests with correct paste types | FR-SYNC-001 | T-01 | done | 2026-08-10T12:40 |
| T-03 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-SYNC-001 | T-02 | done | 2026-08-10T12:45 |
