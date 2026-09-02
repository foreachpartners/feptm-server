"""Protocol interfaces for storage abstraction layer."""

from typing import Protocol

from feptm.models.context import TimesheetContext
from feptm.models.project import Project
from feptm.models.specialist import Specialist


class ProjectStorageProtocol(Protocol):
    """Protocol for project-scoped spreadsheet operations."""

    def create_project(
        self,
        project_name: str,
        template_ids: dict[str, str],
        parent_folder_id: str | None,
    ) -> dict[str, str]:
        """Create a project with folder and spreadsheets from templates."""
        ...

    def update_project_info_sheet(self, spreadsheet_id: str, project: Project) -> None:
        """Write project metadata to the Project Info sheet."""
        ...

    def get_project_metadata(self, project_id: str) -> Project:
        """Read project metadata from the Project Info sheet."""
        ...

    def add_specialist_to_report(
        self,
        spreadsheet_id: str,
        specialist: Specialist,
        import_formula: str,
    ) -> None:
        """Create specialist tab and populate Current Period in a report sheet."""
        ...

    def update_current_period(
        self,
        spreadsheet_id: str,
        specialist: Specialist,
        formula_provider: "FormulaProviderProtocol",
    ) -> None:
        """Add or update a specialist row in the Current Period sheet."""
        ...

    def sync_rates_to_current_period(
        self,
        spreadsheet_id: str,
        specialist: Specialist,
    ) -> None:
        """Update rate fields for an existing specialist in the Current Period sheet."""
        ...

    def close_period_in_timesheet(
        self,
        timesheet_id: str,
        period_name: str,
    ) -> int:
        """Write period_name to Payment Period column for matching entries in a timesheet."""
        ...

    def archive_current_period(
        self,
        spreadsheet_id: str,
        period_name: str,
    ) -> bool:
        """Copy Current Period structure to period_name with values computed from timesheet data."""
        ...

    def protect_archived_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        payment_status_col_idx: int,
    ) -> None:
        """Add protected ranges to an archived tab, leaving Payment Status editable."""
        ...

    def get_stale_specialists(
        self,
        spreadsheet_id: str,
        active_names: set[str],
    ) -> list[Specialist]:
        """Find specialists in Current Period not in active_names, with rates and timesheet IDs."""
        ...

    def remove_stale_specialists(
        self,
        spreadsheet_id: str,
        active_names: set[str],
    ) -> int:
        """Remove Current Period rows for specialists not present in active_names."""
        ...

    def is_period_closed(
        self,
        spreadsheet_id: str,
        period_name: str,
    ) -> bool:
        """Check if a tab with period_name already exists (period already closed)."""
        ...

    def delete_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
    ) -> bool:
        """Delete a sheet tab from a spreadsheet. Returns True if deleted, False if not found."""
        ...


class SpecialistStorageProtocol(Protocol):
    """Protocol for specialist-scoped spreadsheet operations."""

    def list_from_sheet(
        self, spreadsheet_id: str, sheet_name: str = "Team"
    ) -> tuple[list[Specialist], int]:
        """Parse specialists from a Team sheet. Returns (specialists, existing_count)."""
        ...

    def create_timesheet(
        self, specialist: Specialist, context: TimesheetContext, template_id: str
    ) -> dict[str, str]:
        """Create a timesheet spreadsheet from template for a specialist."""
        ...

    def update_timesheet_ids(
        self, spreadsheet_id: str, sheet_name: str, specialists: list[Specialist]
    ) -> bool:
        """Write timesheet IDs back to the Team sheet."""
        ...


class FormulaProviderProtocol(Protocol):
    """Protocol for formula retrieval from config spreadsheet."""

    def get_formula(self, formula_name: str) -> str:
        """Get a named formula from the configuration spreadsheet."""
        ...

    def get_import_timesheet_formula(self, specialist_timesheet_id: str) -> str:
        """Get IMPORTRANGE formula with specialist timesheet ID substituted."""
        ...
