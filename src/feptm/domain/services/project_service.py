"""Project domain service."""

from feptm.domain.models.project import Project
from feptm.domain.models.specialist import Specialist
from feptm.domain.services.protocols import ProjectRepository


class ProjectService:
    """Service for project operations.

    Orchestrates project creation and management using injected repository.
    """

    def __init__(self, repository: ProjectRepository) -> None:
        """Initialize ProjectService.

        Args:
            repository: Project repository implementation
        """
        self._repository = repository

    def create_project(self, name: str) -> tuple[str, Project]:
        """Create new project with empty team.

        Args:
            name: Project name

        Returns:
            Tuple of (project_id, project) where project_id is external ID

        Raises:
            ValidationError: If project name is invalid
            GoogleApiError: If project creation fails
        """
        from feptm.core.exceptions import ValidationError

        if not name or not name.strip():
            raise ValidationError("Project name MUST NOT be empty")

        project = Project(name=name.strip())
        project_id = self._repository.create(project)
        return project_id, project

    def get_project(self, project_id: str) -> Project:
        """Get project by ID.

        Args:
            project_id: External project ID

        Returns:
            Project domain model

        Raises:
            NotFoundError: If project not found
        """
        return self._repository.get_by_id(project_id)

    def add_specialist(self, project_id: str, specialist: Specialist) -> None:
        """Add specialist to project team.

        Args:
            project_id: External project ID
            specialist: Specialist to add

        Raises:
            NotFoundError: If project not found
            ValidationError: If specialist already in team
        """
        project = self._repository.get_by_id(project_id)
        project.add_specialist(specialist)
        self._repository.save(project_id, project)

    def save_project(self, project_id: str, project: Project) -> None:
        """Save project changes.

        Args:
            project_id: External project ID
            project: Updated project domain model

        Raises:
            NotFoundError: If project not found
            GoogleApiError: If save operation fails
        """
        self._repository.save(project_id, project)
