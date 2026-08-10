# WF-2: Status

**Date**: 2026-08-10
**Ceremony**: medium
**FRs**: FR-SYNC-001

## Plan

Fix `_copy_row_formatting` in project_storage.py — replace `copyPaste PASTE_NORMAL` with `PASTE_FORMULA` + `PASTE_FORMAT` to prevent template row values from overwriting new specialist data during sync. The previous fix (WF-2 run 1) addressed the timesheet ID write-back guard; this fix addresses the row insertion data race.

## History

| # | Plan | Tasks | Date | Outcome |
|---|------|-------|------|---------|
| 1 | sync-fix | plan.md (v1) | 2026-08-08 | Planned: 5 tasks |
| 2 | implement | archive/tasks-001.md | 2026-08-08 | 5/5 done, 0 ERR, 0 WARN |
| 5 | url-fix | archive/plan-004.md | 2026-08-10 | 4/4 done, 0 ERR, 0 WARN |
