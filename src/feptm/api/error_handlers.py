"""Exception handlers for FastAPI application."""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from feptm.core.exceptions import FEPTMError
from feptm.core.log import log


async def feptm_exception_handler(
    request: Request,
    exc: FEPTMError,
) -> JSONResponse:
    """Handle application-specific exceptions.

    Args:
        request: FastAPI request instance
        exc: Application exception

    Returns:
        JSON response with error details
    """
    log.error(
        f"Request failed: {exc.message}",
        extra={
            "error_code": exc.code,
            "error_details": exc.details,
            "path": request.url.path,
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


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle request validation errors.

    Args:
        request: FastAPI request instance
        exc: Validation exception

    Returns:
        JSON response with validation errors
    """
    log.warning(
        "Request validation failed",
        extra={
            "path": request.url.path,
            "errors": exc.errors(),
        },
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()},
            }
        },
    )
