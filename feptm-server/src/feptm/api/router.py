"""API router to manage all routes."""

from fastapi import APIRouter

from feptm.api.v1 import projects

# Create API router
router = APIRouter()

# Include router for projects
router.include_router(projects.router, prefix="/projects", tags=["projects"])
