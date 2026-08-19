# Plan: Restore `_add_formulas_for_row()` and `formula_provider` chain

## Workflow
- **ID:** WF-10-remove-addformulasforrow-always-copy-formulas
- **FR:** FR-FORMULA-001
- **Repo:** feptm-server
- **Session:** SID-1787157795-120f3763

## Problem

The previous implementation removed `_add_formulas_for_row()` entirely, assuming the sheet template would have formulas. However, the sheet template does NOT have formulas in row 2.

**Result:** Payment Distribution rows are empty — no formulas written for any specialist.

## Root Cause

Original logic was correct:
- **First specialist** (no existing rows) → write formulas from config spreadsheet
- **Subsequent specialists** → copy from last specialist row via `PASTE_FORMULA`

The removal broke the first-specialist case.

## Solution

**Restore** `_add_formulas_for_row()` and the `formula_provider` parameter chain.

**Keep removed:** The hardcoded column J formula (it's in the sheet template at J2, gets copied via `PASTE_FORMULA`).

## Changes

### 1. `project_storage.py`

#### Restore `_add_formulas_for_row()` function
- Add after `_column_letter()` function (after line ~922)
- Function writes formulas from config spreadsheet for the first specialist

#### Restore `formula_provider` parameter
- `update_current_period()` signature: add `formula_provider: Any`
- `_insert_and_update_row()` signature: add `formula_provider: Any`
- Pass `formula_provider` through the call chain

#### Fix logic in `_insert_and_update_row()`
```python
template_row = _find_template_row(values, headers, self._sheets)
if template_row is not None:
    # Copy from existing specialist row (subsequent specialists)
    self._copy_row_formatting(spreadsheet_id, sheet_name, template_row, target_row)
else:
    # Write formulas from config (first specialist)
    _add_formulas_for_row(self._sheets, spreadsheet_id, sheet_id, target_row, headers, formula_provider)
```

### 2. `protocols.py`

#### Restore `formula_provider` parameter
- `update_current_period()` signature: add `formula_provider: "FormulaProviderProtocol"`

### 3. `project_service.py`

#### Restore `self._formulas` in calls
- Line ~127: `self._projects.update_current_period(project.report_spreadsheet_id, sp, self._formulas)`
- Line ~134: `self._projects.update_current_period(project.calculations_spreadsheet_id, sp, self._formulas)`

### 4. Column J formula

**Keep removed** — the formula is in the sheet template at J2 and gets copied via `PASTE_FORMULA`.

## Verification

```bash
make lint && make typecheck && make test
```

SDD verify:
```bash
./scripts/sdd-cli.sh verify --wf-dir <wf_dir> --phase implement
```
