"""Formula templates with placeholder substitution."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FormulaTemplate:
    """Formula template with placeholder substitution.

    Example:
        template = FormulaTemplate('=IMPORTRANGE("{id}", "sheet!A:E")')
        formula = template.render(id="abc123")
        # Returns: '=IMPORTRANGE("abc123", "sheet!A:E")'
    """

    template: str

    def render(self, **substitutions: str) -> str:
        """Render formula with substitutions.

        Args:
            **substitutions: Key-value pairs for placeholder substitution

        Returns:
            Rendered formula string

        Example:
            template = FormulaTemplate('=IF({cond}, "{yes}", "{no}")')
            result = template.render(cond="A1>0", yes="Yes", no="No")
            # Returns: '=IF(A1>0, "Yes", "No")'
        """
        result = self.template
        for key, value in substitutions.items():
            result = result.replace(f"{{{key}}}", value)
        return result


# Predefined formula templates

# Import timesheet data via IMPORTRANGE
IMPORT_TIMESHEET = FormulaTemplate('=IMPORTRANGE("{spreadsheet_id}", "timesheet!A:E")')

# Calculate hours worked by specialist
# FR-002: Hours Worked formula from product-requirements.md
CALCULATE_HOURS = FormulaTemplate(
    '=SUMIF(INDIRECT("\'"&$A{row}&"\'!$E$2:$E", true), TRIM($C{row}), INDIRECT("\'"&$A{row}&"\'!$D$2:$D", true))'
)

# FR-002: Total Cost formula
GROSS_TOTAL = FormulaTemplate("=$D{row}*$E{row}")

# FR-002: Specialist Cost formula
NET_TOTAL = FormulaTemplate("=$D{row}*$G{row}")

# FR-002: Revenue formula
REVENUE = FormulaTemplate("=$F{row}-$H{row}")

# Hyperlink formula for linking to documents
HYPERLINK = FormulaTemplate('=HYPERLINK("{url}")')
