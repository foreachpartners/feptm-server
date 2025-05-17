#!/usr/bin/env python
"""Script to run the FastAPI application."""

import uvicorn

from feptm.core.config import settings
from feptm.core.log import log
from feptm.main import app


if __name__ == "__main__":
    log.info(f"Starting server on http://{settings.HOST}:{settings.PORT}")
    log.info(f"Debug mode: {'enabled' if settings.DEBUG else 'disabled'}")
    
    uvicorn.run(
        "feptm.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    ) 