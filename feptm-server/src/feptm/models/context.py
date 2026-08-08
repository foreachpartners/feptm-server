"""Context objects for business operations."""

from dataclasses import dataclass


@dataclass
class TimesheetContext:
    """Context for timesheet creation operations.

    Contains information needed to create timesheets without
    the service needing to know about projects directly.
    """

    folder_id: str
    project_name: str

    def __post_init__(self) -> None:
        """Validate context after initialization."""
        if not self.folder_id:
            raise ValueError("folder_id is required")
        if not self.project_name:
            raise ValueError("project_name is required")
