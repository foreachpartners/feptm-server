"""FastAPI error handlers."""

from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from feptm.core.exceptions import FEPTMError
from feptm.core.log import log


def add_error_handlers(app: FastAPI) -> None:
    """Register error handlers for the application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(FEPTMError)
    async def feptm_error_handler(
        request: Request,
        exc: FEPTMError,
    ) -> JSONResponse:
        """Handle all application-specific errors.

        Args:
            request: FastAPI request
            exc: Raised exception

        Returns:
            JSON response with error details
        """
        log.error(
            "Request failed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.code,
                "error_message": exc.message,
                "error_details": exc.details,
            },
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected errors.

        Args:
            request: FastAPI request
            exc: Raised exception

        Returns:
            JSON response with error details
        """
        log.exception(
            "Unhandled error occurred",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred",
                }
            },
        )
