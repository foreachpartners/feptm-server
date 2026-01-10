"""Domain models for projects."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from feptm.domain.models.specialist import Specialist


@dataclass
class Project:
    """Project with team and payment periods.

    NO Google IDs: This domain model is infrastructure-agnostic.
    Google IDs are handled in adapters layer.

    Attributes:
        name: Project name
        created: Project creation timestamp
        team: List of specialists in the project
    """

    name: str
    created: datetime = field(default_factory=datetime.utcnow)
    team: List[Specialist] = field(default_factory=list)

    def add_specialist(self, specialist: Specialist) -> None:
        """Add specialist to project team.

        Args:
            specialist: Specialist to add

        Raises:
            ValueError: If specialist with same name already in team
        """
        if any(s.name == specialist.name for s in self.team):
            raise ValueError(f"Specialist {specialist.name} already in team")
        self.team.append(specialist)

    def remove_specialist(self, name: str) -> None:
        """Remove specialist from project team.

        Args:
            name: Specialist name to remove

        Raises:
            ValueError: If specialist not found
        """
        removed = any(s.name == name for s in self.team)
        if not removed:
            raise ValueError(f"Specialist {name} not found in team")
        self.team = [s for s in self.team if s.name != name]

    def __post_init__(self) -> None:
        """Validate project data."""
        if not self.name.strip():
            raise ValueError("Project name MUST NOT be empty")
