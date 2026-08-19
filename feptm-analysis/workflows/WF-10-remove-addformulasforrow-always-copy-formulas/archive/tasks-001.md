# Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Restore `_add_formulas_for_row()` function in project_storage.py | FR-FORMULA-001 | — | done | 2026-08-19T20:03 |
| T-02 | Restore `formula_provider` parameter in `update_current_period()` and `_insert_and_update_row()` in project_storage.py | FR-FORMULA-001 | T-01 | done | 2026-08-19T20:03 |
| T-03 | Restore `formula_provider` parameter in `update_current_period()` signature in protocols.py | FR-FORMULA-001 | T-02 | done | 2026-08-19T20:03 |
| T-04 | Restore `self._formulas` in `update_current_period()` calls in project_service.py | FR-FORMULA-001 | T-03 | done | 2026-08-19T20:03 |
| T-05 | Verify: make lint && make typecheck && make test | FR-FORMULA-001 | T-04 | done | 2026-08-19T20:03 |

**Notes:**
- T-03: `protocols.py` was restored to its original state (parameter was already there before the initial incorrect removal), so no diff is expected.
