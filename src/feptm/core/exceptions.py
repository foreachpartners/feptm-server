"""Exception hierarchy for FEPTM application."""


class FeptmError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str = "FEPTM_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(FeptmError):
    """Raised when input validation fails."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message, code)


class NotFoundError(FeptmError):
    """Raised when resource not found."""

    def __init__(self, message: str, code: str = "NOT_FOUND") -> None:
        super().__init__(message, code)


class GoogleApiError(FeptmError):
    """Raised when Google API call fails."""

    def __init__(self, message: str, code: str = "GOOGLE_API_ERROR") -> None:
        super().__init__(message, code)


class SpreadsheetError(FeptmError):
    """Raised when spreadsheet operation fails."""

    def __init__(self, message: str, code: str = "SPREADSHEET_ERROR") -> None:
        super().__init__(message, code)
