"""Repository protocol definitions for domain services."""

from typing import Protocol

from feptm.domain.models.period import PaymentPeriod
from feptm.domain.models.project import Project
from feptm.domain.models.specialist import Specialist


class ProjectRepository(Protocol):
    """Repository interface for project persistence.

    All methods return domain models (no Google IDs in signatures).
    """

    def create(self, project: Project) -> str:
        """Create project, return external ID (spreadsheet ID).

        Args:
            project: Project to create

        Returns:
            External project ID (Google Spreadsheet ID)

        Raises:
            GoogleApiError: If spreadsheet creation fails
        """
        ...

    def get_by_id(self, project_id: str) -> Project:
        """Load project by external ID.

        Args:
            project_id: External project ID (Google Spreadsheet ID)

        Returns:
            Project domain model

        Raises:
            NotFoundError: If project not found
        """
        ...

    def save(self, project_id: str, project: Project) -> None:
        """Save project changes.

        Args:
            project_id: External project ID
            project: Updated project domain model

        Raises:
            NotFoundError: If project not found
            GoogleApiError: If save operation fails
        """
        ...


class SpecialistRepository(Protocol):
    """Repository interface for specialist persistence.

    Handles timesheet creation and linking to projects.
    """

    def create_timesheet(
        self, specialist: Specialist, project_id: str
    ) -> str:
        """Create timesheet for specialist, return timesheet ID.

        Args:
            specialist: Specialist domain model
            project_id: External project ID

        Returns:
            Timesheet ID (Google Spreadsheet ID)

        Raises:
            GoogleApiError: If timesheet creation fails
        """
        ...

    def get_by_project(self, project_id: str) -> list[Specialist]:
        """Get all specialists for a project.

        Args:
            project_id: External project ID

        Returns:
            List of Specialist domain models

        Raises:
            NotFoundError: If project not found
        """
        ...

    def update_team_sheet(
        self, project_id: str, specialist: Specialist, timesheet_id: str
    ) -> None:
        """Update Team sheet with specialist information.

        FR-002.1: Supports multiple rate periods per specialist (multiple rows
        with same Timesheet ID).

        Args:
            project_id: External project ID
            specialist: Specialist domain model (may contain multiple rates)
            timesheet_id: Timesheet ID (specialist identifier)

        Raises:
            NotFoundError: If project not found
            GoogleApiError: If update operation fails
        """
        ...


class PeriodRepository(Protocol):
    """Repository interface for payment period operations."""

    def close_period(
        self, project_id: str, period: PaymentPeriod
    ) -> None:
        """Close payment period for project.

        Args:
            project_id: External project ID
            period: Payment period to close

        Raises:
            NotFoundError: If project not found
            GoogleApiError: If period close operation fails
        """
        ...
