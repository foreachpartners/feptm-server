"""Main application module for the Time & Materials accounting service."""

from typing import Dict

from fastapi import FastAPI

from feptm.api.router import router as api_router
from feptm.core.config import settings
from feptm.core.error_handlers import add_error_handlers

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
)

# Register error handlers
add_error_handlers(app)

# Register API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "message": "Time & Materials accounting service is running"}
