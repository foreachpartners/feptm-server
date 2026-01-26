"""PygSheets client wrapper for spreadsheet operations."""

from typing import Any, List, Optional

import pygsheets
from googleapiclient.errors import HttpError
from pygsheets import Spreadsheet, Worksheet

from feptm.adapters.google.auth import authorize_pygsheets
from feptm.core.config import settings
from feptm.core.exceptions import GoogleApiError, SpreadsheetError
from feptm.core.log import log


class PygSheetsClient:
    """Wrapper over pygsheets for spreadsheet operations."""

    def __init__(self, credentials_file: Optional[str] = None) -> None:
        """Initialize PygSheetsClient.

        Args:
            credentials_file: Path to credentials file (optional, uses settings if not provided)
        """
        self._gc = authorize_pygsheets(credentials_file=credentials_file)

    def open_spreadsheet(self, spreadsheet_id: str) -> Spreadsheet:
        """Open spreadsheet by ID.

        Args:
            spreadsheet_id: Google Spreadsheet ID

        Returns:
            Spreadsheet object

        Raises:
            NotFoundError: If spreadsheet not found
            GoogleApiError: If API call fails
        """
        try:
            log.debug(f"Opening spreadsheet: {spreadsheet_id}")
            spreadsheet = self._gc.open_by_key(spreadsheet_id)
            return spreadsheet
        except pygsheets.SpreadsheetNotFound:
            from feptm.core.exceptions import NotFoundError

            raise NotFoundError(f"Spreadsheet not found: {spreadsheet_id}")
        except Exception as e:
            log.error(f"Failed to open spreadsheet {spreadsheet_id}: {e}")
            raise GoogleApiError(f"Failed to open spreadsheet: {e}") from e

    def create_spreadsheet(
        self, title: str, folder_id: Optional[str] = None
    ) -> Spreadsheet:
        """Create new spreadsheet.

        Args:
            title: Spreadsheet title
            folder_id: Google Drive folder ID (optional)

        Returns:
            Created Spreadsheet object

        Raises:
            GoogleApiError: If creation fails
        """
        try:
            log.debug(f"Creating spreadsheet: {title}")
            spreadsheet = self._gc.create(title, folder=folder_id)
            log.info(f"Created spreadsheet: {spreadsheet.id}")
            return spreadsheet
        except Exception as e:
            log.error(f"Failed to create spreadsheet: {e}")
            raise GoogleApiError(f"Failed to create spreadsheet: {e}") from e

    def copy_spreadsheet(
        self, source_id: str, title: str, folder_id: Optional[str] = None
    ) -> Spreadsheet:
        """Copy spreadsheet from template.

        Args:
            source_id: Source spreadsheet ID
            title: New spreadsheet title
            folder_id: Google Drive folder ID (optional)

        Returns:
            Copied Spreadsheet object

        Raises:
            NotFoundError: If source spreadsheet not found
            GoogleApiError: If copy operation fails
        """
        try:
            log.debug(f"Copying spreadsheet {source_id} to {title}")
            
            # Use Google Drive API directly to copy file
            # Build copy request body
            copy_body = {"name": title}
            if folder_id:
                copy_body["parents"] = [folder_id]
            
            # Copy file via Drive API
            # supportsAllDrives=True enables support for Shared Drives (Google Workspace)
            # This is required when copying to Shared Drives or when using service accounts
            copied_file = (
                self._gc.drive.service.files()
                .copy(
                    fileId=source_id,
                    body=copy_body,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )
            
            copied_file_id = copied_file["id"]
            
            # Open copied spreadsheet as pygsheets Spreadsheet object
            copied_spreadsheet = self.open_spreadsheet(copied_file_id)
            
            log.info(f"Copied spreadsheet: {copied_spreadsheet.id}")
            return copied_spreadsheet
        except pygsheets.SpreadsheetNotFound:
            from feptm.core.exceptions import NotFoundError

            raise NotFoundError(f"Source spreadsheet not found: {source_id}")
        except HttpError as e:
            # Check for storage quota exceeded error
            error_str = str(e)
            error_details = getattr(e, "error_details", [])
            
            # Check error details for storageQuotaExceeded reason
            is_quota_error = False
            for detail in error_details:
                if isinstance(detail, dict) and detail.get("reason") == "storageQuotaExceeded":
                    is_quota_error = True
                    break
            
            # Also check error message string as fallback
            if not is_quota_error and "storage quota" in error_str.lower():
                is_quota_error = True
            
            if is_quota_error:
                log.error("Google Drive storage quota exceeded")
                raise GoogleApiError(
                    "Google Drive storage quota exceeded. "
                    "Possible causes:\n"
                    "1. Service account's Drive quota is full (15GB free limit)\n"
                    "2. Files are being copied to a user-owned folder (consumes service account quota)\n"
                    "Solutions:\n"
                    "- Use a Shared Drive (Google Workspace) - files there use Shared Drive quota\n"
                    "- Use OAuth instead of Service Account to use your personal quota\n"
                    "- Free up space in service account's Drive\n"
                    "- Check service account's Drive usage in Google Cloud Console"
                ) from e
            
            # Other HTTP errors
            log.error(f"Failed to copy spreadsheet: {e}")
            raise GoogleApiError(f"Failed to copy spreadsheet: {e}") from e
        except Exception as e:
            log.error(f"Failed to copy spreadsheet: {e}")
            raise GoogleApiError(f"Failed to copy spreadsheet: {e}") from e

    def get_cell_formula(self, worksheet: Worksheet, addr: str) -> Optional[str]:
        """Get formula from cell (None if no formula).

        Args:
            worksheet: Worksheet object
            addr: Cell address (e.g., "A1")

        Returns:
            Formula string or None if cell has no formula
        """
        try:
            cell = worksheet.cell(addr)
            return cell.formula if cell.formula else None
        except Exception as e:
            log.error(f"Failed to get cell formula {addr}: {e}")
            raise SpreadsheetError(f"Failed to get cell formula: {e}") from e

    def set_cell_formula(self, worksheet: Worksheet, addr: str, formula: str) -> None:
        """Set formula in cell.

        Args:
            worksheet: Worksheet object
            addr: Cell address (e.g., "A1")
            formula: Formula string (e.g., "=SUM(A1:A10)")

        Raises:
            SpreadsheetError: If setting formula fails
        """
        try:
            cell = worksheet.cell(addr)
            cell.formula = formula
            cell.update()
            log.debug(f"Set formula in {addr}: {formula}")
        except Exception as e:
            log.error(f"Failed to set cell formula {addr}: {e}")
            raise SpreadsheetError(f"Failed to set cell formula: {e}") from e

    def copy_range_with_formulas(
        self, worksheet: Worksheet, source_range: str, dest_range: str
    ) -> None:
        """Copy range preserving formulas with relative reference adjustment.

        Args:
            worksheet: Worksheet object
            source_range: Source range (e.g., "A1:B1")
            dest_range: Destination range (e.g., "A2:B2")

        Raises:
            SpreadsheetError: If copy operation fails
        """
        try:
            log.debug(f"Copying range {source_range} to {dest_range}")
            # pygsheets copy_range preserves formulas with relative reference adjustment
            worksheet.copy_range(
                source_range,
                dest_range,
                paste_type="PASTE_NORMAL",  # Preserves formulas with stretching
            )
            log.debug(f"Copied range {source_range} to {dest_range}")
        except Exception as e:
            log.error(f"Failed to copy range: {e}")
            raise SpreadsheetError(f"Failed to copy range: {e}") from e

    def batch_update_values(
        self, worksheet: Worksheet, updates: List[tuple[str, Any]]
    ) -> None:
        """Batch update cell values.

        Args:
            worksheet: Worksheet object
            updates: List of (address, value) tuples. Values starting with '=' are treated as formulas.

        Raises:
            SpreadsheetError: If batch update fails
        """
        try:
            cells = []
            for addr, value in updates:
                cell = worksheet.cell(addr)
                if isinstance(value, str) and value.startswith("="):
                    cell.formula = value
                else:
                    cell.value = value
                cells.append(cell)

            if cells:
                worksheet.update_cells(cells)
                log.debug(f"Batch updated {len(cells)} cells")
        except Exception as e:
            log.error(f"Failed to batch update values: {e}")
            raise SpreadsheetError(f"Failed to batch update values: {e}") from e
