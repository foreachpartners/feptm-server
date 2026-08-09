"""API router to manage all routes."""

from fastapi import APIRouter

from feptm.api.v1 import periods, projects

# Create API router
router = APIRouter()

# Include router for projects
router.include_router(projects.router, prefix="/projects", tags=["projects"])
# Include router for periods
router.include_router(periods.router, prefix="/periods", tags=["periods"])
