"""Unit tests for mappers."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from feptm.adapters.sheets.mappers import (
    merge_specialists_by_timesheet_id,
    project_to_row,
    row_to_project,
    row_to_specialist,
    specialist_to_row,
)
from feptm.domain.models.project import Project
from feptm.domain.models.specialist import Specialist


class TestRowToSpecialist:
    """Tests for row_to_specialist mapper."""

    def test_row_to_specialist_single_rate(self) -> None:
        """Test converting Team sheet row to Specialist."""
        row = ["Mark", "Developer", "12", "14", "2025-01-01", "abc123"]
        specialist = row_to_specialist(row, "abc123")

        assert specialist.name == "Mark"
        assert specialist.role == "Developer"
        assert len(specialist.rates) == 1
        assert specialist.rates[0].internal == Decimal("12")
        assert specialist.rates[0].external == Decimal("14")
        assert specialist.rates[0].start_date == date(2025, 1, 1)

    def test_row_to_specialist_invalid_row(self) -> None:
        """Test row_to_specialist with invalid row data."""
        row = ["Mark"]  # Insufficient columns
        with pytest.raises(Exception):  # ValidationError expected
            row_to_specialist(row, "abc123")

    def test_row_to_specialist_empty_name(self) -> None:
        """Test row_to_specialist rejects empty name."""
        row = ["", "Developer", "12", "14", "2025-01-01", "abc123"]
        with pytest.raises(Exception):  # ValidationError expected
            row_to_specialist(row, "abc123")


class TestSpecialistToRow:
    """Tests for specialist_to_row mapper."""

    def test_specialist_to_row_single_rate(self) -> None:
        """Test converting Specialist to Team sheet rows."""
        from feptm.domain.models.specialist import Rate

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

        rows = specialist_to_row(specialist, "abc123")
        assert len(rows) == 1
        assert rows[0] == ["Mark", "Developer", "12", "14", "2025-01-01", "abc123"]

    def test_specialist_to_row_multiple_rates(self) -> None:
        """Test converting Specialist with multiple rates (FR-002.1)."""
        from feptm.domain.models.specialist import Rate

        specialist = Specialist(
            name="Mark",
            role="Developer",
            rates=[
                Rate(
                    internal=Decimal("12"),
                    external=Decimal("14"),
                    start_date=date(2025, 1, 1),
                ),
                Rate(
                    internal=Decimal("15"),
                    external=Decimal("20"),
                    start_date=date(2025, 3, 26),
                ),
            ],
        )

        rows = specialist_to_row(specialist, "abc123")
        assert len(rows) == 2
        assert rows[0][4] == "2025-01-01"  # First rate start_date
        assert rows[1][4] == "2025-03-26"  # Second rate start_date


class TestProjectToRow:
    """Tests for project_to_row mapper."""

    def test_project_to_row(self) -> None:
        """Test converting Project to Project Info sheet rows."""
        project = Project(name="Test Project", created=datetime(2025, 1, 1, 12, 0, 0))
        rows = project_to_row(project, "project-id-123")

        assert len(rows) >= 3  # Header + Project ID + Name + Created
        assert any("Test Project" in str(row) for row in rows)
        assert any("project-id-123" in str(row) for row in rows)


class TestRowToProject:
    """Tests for row_to_project mapper."""

    def test_row_to_project(self) -> None:
        """Test converting Project Info sheet rows to Project."""
        data = [
            ["Field", "Value"],
            ["Project ID", "project-id-123"],
            ["Name", "Test Project"],
            ["Created", "2025-01-01 12:00:00 UTC"],
        ]

        project = row_to_project(data, "project-id-123")

        assert project.name == "Test Project"
        assert isinstance(project.created, datetime)


class TestMergeSpecialists:
    """Tests for merge_specialists_by_timesheet_id."""

    def test_merge_specialists_same_name(self) -> None:
        """Test merging specialists with same name."""
        from feptm.domain.models.specialist import Rate

        spec1 = Specialist(
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

        spec2 = Specialist(
            name="Mark",
            role="Developer",
            rates=[
                Rate(
                    internal=Decimal("15"),
                    external=Decimal("20"),
                    start_date=date(2025, 3, 26),
                )
            ],
        )

        merged = merge_specialists_by_timesheet_id([spec1, spec2])
        assert len(merged) == 1
        assert len(merged[0].rates) == 2  # Both rates merged
