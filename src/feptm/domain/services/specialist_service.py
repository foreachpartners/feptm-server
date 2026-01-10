"""Specialist domain service."""

from feptm.domain.models.specialist import Specialist
from feptm.domain.services.protocols import SpecialistRepository


class SpecialistService:
    """Service for specialist operations.

    Orchestrates timesheet creation and team management.
    """

    def __init__(self, repository: SpecialistRepository) -> None:
        """Initialize SpecialistService.

        Args:
            repository: Specialist repository implementation
        """
        self._repository = repository

    def add_to_project(
        self, project_id: str, specialist: Specialist
    ) -> str:
        """Add specialist to project and create timesheet.

        FR-002: Creates timesheet for new specialist.
        FR-002.1: Supports multiple rate periods per specialist.

        Args:
            project_id: External project ID
            specialist: Specialist domain model (may contain multiple rates)

        Returns:
            Timesheet ID (serves as specialist identifier)

        Raises:
            NotFoundError: If project not found
            GoogleApiError: If timesheet creation fails
        """
        # Create timesheet for specialist
        timesheet_id = self._repository.create_timesheet(specialist, project_id)

        # Update Team sheet with specialist info and rate periods
        # FR-002.1: Multiple rows for multiple rate periods
        self._repository.update_team_sheet(project_id, specialist, timesheet_id)

        return timesheet_id

    def get_project_team(self, project_id: str) -> list[Specialist]:
        """Get all specialists for a project.

        FR-002.1: Returns specialists with their rate periods.

        Args:
            project_id: External project ID

        Returns:
            List of Specialist domain models with rate periods

        Raises:
            NotFoundError: If project not found
        """
        return self._repository.get_by_project(project_id)
