"""Legacy model definitions (for backward compatibility).

NOTE: These models contain Google IDs and are deprecated.
Use domain models from feptm.domain.models instead.
"""

# Legacy imports for backward compatibility
from feptm.models.project import (
    Project,
    ProjectMetaResponse,
    ProjectSyncRequest,
    ProjectSyncResponse,
)
from feptm.models.specialist import Specialist

__all__ = [
    "Project",
    "ProjectMetaResponse",
    "Specialist",
    "ProjectSyncRequest",
    "ProjectSyncResponse",
]
