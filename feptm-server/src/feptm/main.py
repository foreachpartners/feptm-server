"""Main application module for the Time & Materials accounting service."""

from fastapi import FastAPI

from feptm.api.router import router as api_router
from feptm.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "message": "Time & Materials accounting service is running"}
