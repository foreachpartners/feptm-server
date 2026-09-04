"""Custom exceptions for feptm application."""


class PeriodAlreadyClosedError(Exception):
    """Raised when attempting to close a period that has already been closed."""

    def __init__(self, period_name: str) -> None:
        self.period_name = period_name
        super().__init__(f"Period '{period_name}' is already closed")


class ProjectFolderNotFoundError(Exception):
    def __init__(self, folder_id: str) -> None:
        self.folder_id = folder_id
        super().__init__(f"Project folder not found: {folder_id}")


class ProjectSpreadsheetNotFoundError(Exception):
    def __init__(self, expected_name: str) -> None:
        self.expected_name = expected_name
        super().__init__(f"Project spreadsheet not found: {expected_name}")
