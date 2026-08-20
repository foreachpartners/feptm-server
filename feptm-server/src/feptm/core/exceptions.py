"""Custom exceptions for feptm application."""


class PeriodAlreadyClosedError(Exception):
    """Raised when attempting to close a period that has already been closed."""

    def __init__(self, period_name: str) -> None:
        self.period_name = period_name
        super().__init__(f"Period '{period_name}' is already closed")
