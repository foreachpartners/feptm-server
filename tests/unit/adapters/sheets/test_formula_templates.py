"""Unit tests for formula templates."""

import pytest

from feptm.adapters.sheets.formula_templates import (
    CALCULATE_HOURS,
    GROSS_TOTAL,
    IMPORT_TIMESHEET,
    NET_TOTAL,
    REVENUE,
    FormulaTemplate,
)


class TestFormulaTemplate:
    """Tests for FormulaTemplate."""

    def test_render_with_substitutions(self) -> None:
        """Test rendering formula with substitutions."""
        template = FormulaTemplate('=IMPORTRANGE("{spreadsheet_id}", "sheet!A:E")')
        result = template.render(spreadsheet_id="abc123")
        assert result == '=IMPORTRANGE("abc123", "sheet!A:E")'

    def test_render_multiple_substitutions(self) -> None:
        """Test rendering formula with multiple substitutions."""
        template = FormulaTemplate('=IF({cond}, "{yes}", "{no}")')
        result = template.render(cond="A1>0", yes="Yes", no="No")
        assert result == '=IF(A1>0, "Yes", "No")'


class TestPredefinedTemplates:
    """Tests for predefined formula templates."""

    def test_import_timesheet(self) -> None:
        """Test IMPORTRANGE template."""
        formula = IMPORT_TIMESHEET.render(spreadsheet_id="abc123")
        assert 'abc123' in formula
        assert "IMPORTRANGE" in formula

    def test_calculate_hours(self) -> None:
        """Test CALCULATE_HOURS template."""
        formula = CALCULATE_HOURS.render(row="2")
        assert "2" in formula
        assert "SUMIF" in formula or "INDIRECT" in formula

    def test_gross_total(self) -> None:
        """Test GROSS_TOTAL template."""
        formula = GROSS_TOTAL.render(row="2")
        assert "2" in formula
        assert "$D" in formula
        assert "$E" in formula

    def test_net_total(self) -> None:
        """Test NET_TOTAL template."""
        formula = NET_TOTAL.render(row="2")
        assert "2" in formula
        assert "$D" in formula
        assert "$G" in formula

    def test_revenue(self) -> None:
        """Test REVENUE template."""
        formula = REVENUE.render(row="2")
        assert "2" in formula
        assert "$F" in formula or "$H" in formula
