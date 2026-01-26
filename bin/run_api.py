#!/usr/bin/env python
"""Script to run the FastAPI application."""

import sys
from pathlib import Path

# Add src directory to Python path
# bin/run_api.py is in project_root/bin/, so project_root/src is parent/src
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import uvicorn

from feptm.core.config import settings
from feptm.core.log import log
from feptm.main import app


if __name__ == "__main__":
    log.info(f"Starting server on http://{settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "feptm.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    ) 