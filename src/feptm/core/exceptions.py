"""Core exceptions for the application."""

from typing import Any, Dict, Optional


class FEPTMError(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize base exception.

        Args:
            message: Human-readable error description
            code: Machine-readable error code
            details: Additional error context
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class GoogleAPIError(FEPTMError):
    """Raised when Google API operations fail."""

    def __init__(
        self,
        message: str,
        api_error: Optional[Exception] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Google API error.

        Args:
            message: Error description
            api_error: Original Google API exception
            **kwargs: Additional context
        """
        details = kwargs.copy()
        if api_error:
            details["original_error"] = str(api_error)
        super().__init__(
            message=message,
            code="google_api_error",
            details=details,
        )


class ValidationError(FEPTMError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error description
            field: Name of the invalid field
            value: Invalid value
        """
        details = {}
        if field:
            details["field"] = field
        if value:
            details["value"] = str(value)
        super().__init__(
            message=message,
            code="validation_error",
            details=details,
        )


class ResourceNotFoundError(FEPTMError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        **kwargs: Any,
    ) -> None:
        """Initialize not found error.

        Args:
            resource_type: Type of resource (project, specialist, etc.)
            resource_id: ID of the resource
            **kwargs: Additional context
        """
        message = f"{resource_type} with id {resource_id} not found"
        details = kwargs.copy()
        details.update(
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
            }
        )
        super().__init__(
            message=message,
            code="not_found",
            details=details,
        )


class OperationError(FEPTMError):
    """Raised when business operation fails."""

    def __init__(
        self,
        operation: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Initialize operation error.

        Args:
            operation: Name of the failed operation
            message: Error description
            **kwargs: Additional context
        """
        details = kwargs.copy()
        details["operation"] = operation
        super().__init__(
            message=message,
            code="operation_error",
            details=details,
        )
