"""Unit tests for Project domain model."""

from datetime import datetime

import pytest

from feptm.domain.models.project import Project
from feptm.domain.models.specialist import Rate, Specialist
from datetime import date
from decimal import Decimal


class TestProject:
    """Tests for Project dataclass."""

    def test_project_creation(self) -> None:
        """Test creating a project."""
        project = Project(name="Test Project")
        assert project.name == "Test Project"
        assert isinstance(project.created, datetime)
        assert len(project.team) == 0

    def test_add_specialist(self) -> None:
        """Test adding specialist to project."""
        project = Project(name="Test Project")
        specialist = Specialist(
            name="Mark",
            role="Developer",
            rates=[
                Rate(
                    internal=Decimal("12"),
                    external=Decimal("14"),
                    start_date=date(2025, 1, 1),
                )
            ],
        )

        project.add_specialist(specialist)
        assert len(project.team) == 1
        assert project.team[0].name == "Mark"

    def test_add_specialist_duplicate(self) -> None:
        """Test adding duplicate specialist fails."""
        project = Project(name="Test Project")
        specialist = Specialist(
            name="Mark",
            role="Developer",
            rates=[
                Rate(
                    internal=Decimal("12"),
                    external=Decimal("14"),
                    start_date=date(2025, 1, 1),
                )
            ],
        )

        project.add_specialist(specialist)

        with pytest.raises(ValueError, match="already in team"):
            project.add_specialist(specialist)

    def test_remove_specialist(self) -> None:
        """Test removing specialist from project."""
        project = Project(name="Test Project")
        specialist = Specialist(
            name="Mark",
            role="Developer",
            rates=[
                Rate(
                    internal=Decimal("12"),
                    external=Decimal("14"),
                    start_date=date(2025, 1, 1),
                )
            ],
        )

        project.add_specialist(specialist)
        project.remove_specialist("Mark")
        assert len(project.team) == 0

    def test_remove_specialist_not_found(self) -> None:
        """Test removing non-existent specialist fails."""
        project = Project(name="Test Project")

        with pytest.raises(ValueError, match="not found in team"):
            project.remove_specialist("Mark")

    def test_project_validation_empty_name(self) -> None:
        """Test project validation rejects empty name."""
        with pytest.raises(ValueError, match="Project name MUST NOT be empty"):
            Project(name="")
