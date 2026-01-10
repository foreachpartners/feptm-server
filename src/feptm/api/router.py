"""API router to manage all routes."""

from fastapi import APIRouter

from feptm.interfaces.api.v1 import periods, projects, specialists

# Create API router
router = APIRouter()

# Include v1 routers
router.include_router(projects.router, prefix="/v1")
router.include_router(specialists.router, prefix="/v1")
router.include_router(periods.router, prefix="/v1")
