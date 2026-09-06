"""Service for working with Google Sheets API."""

import contextvars
import json
import random
import time
from pathlib import Path
from typing import Any, cast

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_httplib2 import AuthorizedHttp  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import Resource, build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from feptm.core.config import settings
from feptm.core.log import log

# Suppress googleapiclient discovery cache warnings
import logging
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)

_metadata_cache: contextvars.ContextVar[dict[str, dict[str, Any]]] = (
    contextvars.ContextVar("_metadata_cache", default={})
)


class GoogleSheetsRateLimitError(Exception):
    """Raised when Google Sheets API rate limit is exhausted after all retries."""

    def __init__(self, operation: str, spreadsheet_id: str, attempts: int) -> None:
        self.operation = operation
        self.spreadsheet_id = spreadsheet_id
        self.attempts = attempts
        super().__init__(
            f"Rate limit exhausted for {operation} on {spreadsheet_id} "
            f"after {attempts} retries"
        )


class GoogleSheetsService:
    """Service for working with Google Sheets API."""

    def __init__(self) -> None:
        """Initialize service with credentials."""
        self.credentials_file = (
            settings.GOOGLE_CREDENTIALS_FILE or self._find_credentials_file()
        )

        self.token_file = (
            settings.GOOGLE_TOKEN_FILE or Path.home() / ".google_sheets_token.json"
        )

        self._credentials: UserCredentials | None = None
        self._initialize_credentials()

    def _find_credentials_file(self) -> str:
        """Find the credentials file in default locations.

        Returns:
            Path to the credentials file

        Raises:
            FileNotFoundError: If no credentials file can be found
        """
        default_locations = [
            "credentials.json",
        ]

        # Check default locations
        for location in default_locations:
            if Path(location).is_file():
                return str(location)

        # If we get here, no credentials file was found
        locations_str = "\n- ".join([""] + default_locations)
        raise FileNotFoundError(
            f"Could not find Google API credentials file. "
            f"Please place credentials.json in one of the following locations:{locations_str}"
        )

    def _initialize_credentials(self) -> bool:
        """Load OAuth credentials once at startup.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._credentials = self._get_credentials()
            if not self._credentials:
                log.error("Failed to obtain OAuth credentials")
                return False

            log.info("Google credentials loaded successfully")
            return True

        except Exception as e:
            log.error(f"Error loading Google credentials: {e!s}")
            self._credentials = None
            return False

    def _get_services(self) -> tuple[Resource, Resource]:
        """Create thread-local API service instances.

        Returns:
            Tuple of (drive_service, sheets_service)

        Raises:
            Exception: If credentials are not available
        """
        if not self._credentials:
            raise Exception("Google credentials not initialized")

        http = AuthorizedHttp(
            self._credentials,
            http=httplib2.Http(timeout=settings.GOOGLE_API_TIMEOUT),
        )
        drive_service = build("drive", "v3", http=http, cache_discovery=False)
        sheets_service = build("sheets", "v4", http=http, cache_discovery=False)
        return drive_service, sheets_service

    @property
    def sheets_service(self) -> Resource:
        """Return a thread-local sheets service instance."""
        _, sheets = self._get_services()
        return sheets

    @property
    def drive_service(self) -> Resource:
        """Return a thread-local drive service instance."""
        drive, _ = self._get_services()
        return drive

    def _get_credentials(self) -> UserCredentials | None:
        """Get OAuth credentials for Google API.

        Returns:
            OAuth credentials
        """
        creds = None
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]

        # Check if token file exists and load credentials from it
        token_path = Path(self.token_file)

        if token_path.exists():
            try:
                creds = UserCredentials.from_authorized_user_info(
                    json.loads(token_path.read_text()), scopes
                )
            except Exception as e:
                log.error(f"Error loading token file: {e!s}")

        # If there are no valid credentials, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Load client secrets from the credentials file
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, scopes
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            token_path = Path(self.token_file)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(
                json.dumps(
                    {
                        "token": creds.token,
                        "refresh_token": creds.refresh_token,
                        "token_uri": creds.token_uri,
                        "client_id": creds.client_id,
                        "client_secret": creds.client_secret,
                        "scopes": creds.scopes,
                    }
                )
            )
            log.info(f"Saved credentials to {token_path}")

        return cast(UserCredentials | None, creds)

    def create_spreadsheet(self, title: str) -> dict[str, str]:
        """Create a new Google Sheets spreadsheet.

        Args:
            title: Title of the spreadsheet

        Returns:
            Dictionary with spreadsheet ID and URL
        """
        _, sheets_service = self._get_services()

        spreadsheet_body = {
            "properties": {"title": title}
        }

        try:
            spreadsheet = (
                sheets_service.spreadsheets()
                .create(body=spreadsheet_body)
                .execute()
            )

            spreadsheet_id = spreadsheet.get("spreadsheetId")
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
            }
        except HttpError as error:
            raise Exception(f"Failed to create spreadsheet: {error}")

    def get_all_sheets(self, spreadsheet_id: str) -> list[dict[str, Any]]:
        """Return all sheets for a spreadsheet, using cache if available.

        Args:
            spreadsheet_id: ID of the spreadsheet

        Returns:
            List of sheet metadata dicts
        """
        cache = _metadata_cache.get({})
        if spreadsheet_id in cache:
            return cast(list[dict[str, Any]], cache[spreadsheet_id].get("sheets", []))

        _, sheets_service = self._get_services()

        try:
            spreadsheet = (
                sheets_service.spreadsheets()
                .get(
                    spreadsheetId=spreadsheet_id,
                    fields="sheets(properties(title,sheetId))",
                )
                .execute()
            )

            cache[spreadsheet_id] = spreadsheet
            _metadata_cache.set(cache)

            return cast(list[dict[str, Any]], spreadsheet.get("sheets", []))
        except Exception as error:
            log.error(f"Error getting spreadsheet metadata: {error}")
            return []

    def invalidate_metadata_cache(self, spreadsheet_id: str) -> None:
        """Remove spreadsheet from metadata cache after mutations.

        Args:
            spreadsheet_id: ID of the spreadsheet to invalidate
        """
        cache = _metadata_cache.get({})
        if spreadsheet_id in cache:
            del cache[spreadsheet_id]
            _metadata_cache.set(cache)

    def get_sheet_by_name(
        self, spreadsheet_id: str, sheet_name: str
    ) -> dict[str, Any] | None:
        """Finds a sheet in the spreadsheet by its name.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet to find

        Returns:
            Dictionary with information about the found sheet or None if not found
        """
        sheets = self.get_all_sheets(spreadsheet_id)
        if not sheets:
            log.warning(
                f"Warning: No sheets found in the spreadsheet with ID {spreadsheet_id}"
            )
            return None

        for sheet in sheets:
            if sheet.get("properties", {}).get("title") == sheet_name:
                return cast(dict[str, Any], sheet)

        available_sheets = [
            s.get("properties", {}).get("title", "") for s in sheets
        ]
        log.warning(
            f"Warning: Sheet '{sheet_name}' not found. Available sheets: {', '.join(available_sheets)}"
        )
        return None

    def create_drive_folder(
        self, folder_name: str, parent_folder_id: str | None = None
    ) -> dict[str, str]:
        """Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder
            parent_folder_id: ID of the parent folder (optional)

        Returns:
            Dictionary with folder ID and URL
        """
        drive_service, _ = self._get_services()

        folder_metadata: dict[str, Any] = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_folder_id:
            folder_metadata["parents"] = [parent_folder_id]

        try:
            folder = (
                drive_service.files()
                .create(body=folder_metadata, fields="id")
                .execute()
            )

            folder_id = folder.get("id")
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"

            return {"folder_id": folder_id, "folder_url": folder_url}
        except HttpError as error:
            raise Exception(f"Failed to create folder: {error}")

    def copy_spreadsheet_from_template(
        self, template_id: str, new_title: str, folder_id: str
    ) -> dict[str, str]:
        """Copy a spreadsheet from a template and move it to a folder.

        Args:
            template_id: ID of the template spreadsheet
            new_title: Title for the new spreadsheet
            folder_id: ID of the folder where to place the copy

        Returns:
            Dictionary with spreadsheet ID and URL
        """
        drive_service, _ = self._get_services()

        try:
            copied_file = (
                drive_service.files()
                .copy(fileId=template_id, body={"name": new_title}, fields="id")
                .execute()
            )

            spreadsheet_id = copied_file.get("id")

            drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                removeParents="root",
                fields="id, parents",
            ).execute()

            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
            }
        except HttpError as error:
            if error.resp.status == 404:
                raise Exception(
                    f"Failed to copy spreadsheet: Template with ID {template_id} not found. Make sure the file exists and you have access to it."
                )
            else:
                raise Exception(f"Failed to copy spreadsheet: {error}")
        except Exception as e:
            raise Exception(f"Failed to copy spreadsheet: {e}")

    def ensure_spreadsheet_from_template(
        self, template_id: str, new_title: str, folder_id: str
    ) -> dict[str, str]:
        """Verifies a template exists and creates a spreadsheet from it.

        This method checks if the template exists, handles potential errors,
        and creates a new spreadsheet from the template.

        Args:
            template_id: ID of the template spreadsheet
            new_title: Title for the new spreadsheet
            folder_id: ID of the folder where to place the copy

        Returns:
            Dictionary with spreadsheet ID and URL

        Raises:
            Exception: If template doesn't exist or other errors occur
        """
        try:
            # First check if template exists and is accessible
            template_info = self.get_file(template_id)
            log.info(
                f"Template found: {template_info.get('name')} (ID: {template_info.get('id')})"
            )

            # Then create spreadsheet from template
            return self.copy_spreadsheet_from_template(
                template_id, new_title, folder_id
            )
        except Exception as error:
            if isinstance(error, HttpError) and error.resp.status == 404:
                raise Exception(
                    f"Template with ID {template_id} not found. Please check the template ID."
                )
            raise Exception(f"Failed to create spreadsheet from template: {error}")

    def get_file(self, file_id: str) -> dict[str, Any]:
        """Get file information from Google Drive.

        Args:
            file_id: ID of the file to get

        Returns:
            Dictionary with file information
        """
        drive_service, _ = self._get_services()

        try:
            result = (
                drive_service.files()
                .get(fileId=file_id, fields="id,name,mimeType,parents")
                .execute()
            )
            return cast(dict[str, Any], result)
        except HttpError as error:
            raise Exception(f"Failed to get file with ID {file_id}: {error}")

    def list_drive_folders(self, parent_folder_id: str) -> list[dict[str, str]]:
        """List folders in a Google Drive folder.

        Args:
            parent_folder_id: ID of the parent folder

        Returns:
            List of dicts with 'id' and 'name' for each folder
        """
        drive_service, _ = self._get_services()

        folders: list[dict[str, str]] = []
        page_token: str | None = None

        try:
            while True:
                query = (
                    f"'{parent_folder_id}' in parents and "
                    "mimeType='application/vnd.google-apps.folder' and trashed=false"
                )
                request = drive_service.files().list(
                    q=query,
                    fields="nextPageToken, files(id,name)",
                    pageToken=page_token,
                )
                result = request.execute()
                for f in result.get("files", []):
                    folders.append({"id": f["id"], "name": f["name"]})
                page_token = result.get("nextPageToken")
                if not page_token:
                    break
            return folders
        except HttpError as error:
            raise Exception(f"Failed to list folders in {parent_folder_id}: {error}")

    def list_drive_spreadsheets(
        self, folder_id: str
    ) -> list[dict[str, str]]:
        drive_service, _ = self._get_services()

        spreadsheets: list[dict[str, str]] = []
        page_token: str | None = None

        try:
            while True:
                query = (
                    f"'{folder_id}' in parents and "
                    "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
                )
                request = drive_service.files().list(
                    q=query,
                    fields="nextPageToken, files(id,name)",
                    pageToken=page_token,
                )
                result = request.execute()
                for f in result.get("files", []):
                    spreadsheets.append({"id": f["id"], "name": f["name"]})
                page_token = result.get("nextPageToken")
                if not page_token:
                    break
            return spreadsheets
        except HttpError as error:
            raise Exception(
                f"Failed to list spreadsheets in {folder_id}: {error}"
            )

    def delete_file(self, file_id: str) -> None:
        """Delete a file from Google Drive.

        Args:
            file_id: ID of the file to delete

        Returns:
            None
        """
        drive_service, _ = self._get_services()

        try:
            drive_service.files().delete(fileId=file_id).execute()
        except HttpError as error:
            raise Exception(f"Failed to delete file with ID {file_id}: {error}")

    def find_file_in_folder(self, folder_id: str, file_name: str) -> str | None:
        """Search for a spreadsheet by name in a Drive folder.

        Args:
            folder_id: ID of the folder to search in
            file_name: Exact file name to match

        Returns:
            File ID if found, None otherwise
        """
        drive_service, _ = self._get_services()

        try:
            query = (
                f"'{folder_id}' in parents and name = '{file_name}'"
                f" and mimeType = 'application/vnd.google-apps.spreadsheet'"
                f" and trashed = false"
            )
            results = (
                drive_service.files()
                .list(q=query, fields="files(id, name)")
                .execute()
            )
            files = results.get("files", [])
            return files[0]["id"] if files else None
        except HttpError as error:
            raise Exception(
                f"Failed to search files in folder {folder_id}: {error}"
            )

    def move_file(self, file_id: str, folder_id: str) -> None:
        """Move a file to a different folder in Google Drive.

        Args:
            file_id: ID of the file to move
            folder_id: ID of the destination folder

        Returns:
            None
        """
        drive_service, _ = self._get_services()

        try:
            file = (
                drive_service.files()
                .get(fileId=file_id, fields="parents")
                .execute()
            )

            parents_list = file.get("parents", [])
            previous_parents = ",".join(parents_list)

            drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields="id, parents",
            ).execute()
        except HttpError as error:
            raise Exception(
                f"Failed to move file with ID {file_id} to folder {folder_id}: {error}"
            )

    def _retry_api_call(
        self,
        operation_name: str,
        spreadsheet_id: str,
        callable_fn: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        max_retries = 5
        base_delay = 1.0
        max_delay = 60.0
        for attempt in range(max_retries + 1):
            try:
                return callable_fn(*args, **kwargs)
            except HttpError as error:
                status = error.resp.status
                if status == 429:
                    retry_header = error.resp.get("Retry-After")
                    if retry_header:
                        retry_after = float(retry_header)
                    else:
                        retry_after = base_delay * (2**attempt) + random.uniform(
                            0, 1
                        )
                    delay = min(retry_after, max_delay)
                    log.warning(
                        "Rate limited (%s, %s): attempt %d/%d, waiting %.1fs",
                        operation_name,
                        spreadsheet_id,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                if status >= 500:
                    delay = min(
                        base_delay * (2**attempt) + random.uniform(0, 1),
                        max_delay,
                    )
                    log.warning(
                        "Server error %d (%s, %s): attempt %d/%d, waiting %.1fs",
                        status,
                        operation_name,
                        spreadsheet_id,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise Exception(f"Failed to {operation_name}: {error}")
        raise GoogleSheetsRateLimitError(
            operation_name, spreadsheet_id, max_retries
        )

    def clear_range(self, spreadsheet_id: str, range_name: str) -> None:
        """Clear values in a range.

        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to clear (A1 notation)

        Returns:
            None
        """
        _, sheets_service = self._get_services()

        try:
            self._retry_api_call(
                "clear_range",
                spreadsheet_id,
                lambda: sheets_service.spreadsheets()
                .values()
                .clear(spreadsheetId=spreadsheet_id, range=range_name, body={})
                .execute(),
            )
        except GoogleSheetsRateLimitError:
            raise
        except Exception as error:
            log.warning(f"Warning: Failed to clear range {range_name}: {error}")

    def update_range(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        value_input_option: str = "RAW",
    ) -> dict[str, Any]:
        """Update a range in a Google Sheet.

        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to update (e.g. "Sheet1!A1:B10")
            values: 2D array of values to update
            value_input_option: How to interpret the values ("RAW" or "USER_ENTERED")

        Returns:
            Response from the API
        """
        _, sheets_service = self._get_services()

        try:
            result = self._retry_api_call(
                "update_range",
                spreadsheet_id,
                lambda: sheets_service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body={"values": values},
                )
                .execute(),
            )
            return cast(dict[str, Any], result)
        except HttpError as error:
            raise Exception(f"Failed to update range {range_name}: {error}")

    def update_sheet_data(
        self, spreadsheet_id: str, sheet_name: str, data: list[list[Any]]
    ) -> dict[str, Any]:
        """Update a sheet with data.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet to update
            data: 2D array of data to update

        Returns:
            Response from the API
        """
        try:
            sheet = self.get_sheet_by_name(spreadsheet_id, sheet_name)
            if not sheet:
                raise Exception(
                    f"Sheet '{sheet_name}' not found in spreadsheet with ID {spreadsheet_id}"
                )

            sheet_title = sheet["properties"]["title"]

            self.clear_range(
                spreadsheet_id=spreadsheet_id,
                range_name=f"{sheet_title}!A1:B{len(data) + 5}",
            )

            response = self.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=f"{sheet_title}!A1:B{len(data)}",
                values=data,
                value_input_option="USER_ENTERED",
            )

            return cast(dict[str, Any], response)
        except Exception as error:
            raise Exception(f"Failed to update sheet: {error}")

    def batch_update(
        self, spreadsheet_id: str, requests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Perform batch update operations on a Google Sheet.

        Args:
            spreadsheet_id: ID of the spreadsheet
            requests: List of requests to execute

        Returns:
            Response from the API
        """
        _, sheets_service = self._get_services()

        try:
            result = self._retry_api_call(
                "batch_update",
                spreadsheet_id,
                lambda: sheets_service.spreadsheets()
                .batchUpdate(
                    spreadsheetId=spreadsheet_id, body={"requests": requests}
                )
                .execute(),
            )
            return cast(dict[str, Any], result)
        except Exception as error:
            raise Exception(f"Failed to batch update spreadsheet: {error}")

    # Utility methods for Google Sheets operations

    def find_column_index(
        self, headers: list[str], column_names: list[str]
    ) -> int | None:
        """Find column index by possible header names.

        Args:
            headers: List of column headers
            column_names: List of possible names for the column

        Returns:
            Index of the column or None if not found
        """
        for name in column_names:
            for i, header in enumerate(headers):
                if header.strip().lower() == name.lower():
                    return i
        return None

    def column_index_to_letter(self, col_idx: int) -> str:
        """Convert column index to letter (A, B, C, etc.).

        Args:
            col_idx: Zero-based column index

        Returns:
            Column letter
        """
        result = ""
        while col_idx >= 0:
            result = chr(col_idx % 26 + ord("A")) + result
            col_idx = col_idx // 26 - 1
        return result

    def column_letter_to_index(self, letter: str) -> int:
        """Convert column letter to zero-based index.

        Args:
            letter: Column letter (A, B, C, etc.)

        Returns:
            Zero-based column index
        """
        result = 0
        for char in letter.upper():
            result = result * 26 + (ord(char) - ord("A") + 1)
        return result - 1

    def format_range(
        self, sheet_name: str, start_col: str, end_col: str, row: int
    ) -> str:
        """Format a range string for Google Sheets API.

        Args:
            sheet_name: Name of the sheet
            start_col: Starting column letter
            end_col: Ending column letter
            row: Row number

        Returns:
            Formatted range string
        """
        return f"{sheet_name}!{start_col}{row}:{end_col}{row}"

    def find_specialist_row_index(  # AR-DATA-001:allow
        self, values: list[list], name_col_idx: int, specialist_name: str
    ) -> int | None:
        """Find row index for a specialist by name.

        Args:
            values: Sheet values
            name_col_idx: Index of the name column
            specialist_name: Name of the specialist to find

        Returns:
            Zero-based row index or None if not found
        """
        for i, row in enumerate(values[1:], start=1):  # Skip header row
            if name_col_idx < len(row) and row[name_col_idx].strip() == specialist_name:
                return i
        return None

    def get_sheet_data_with_headers(
        self, spreadsheet_id: str, sheet_name: str, range_format: str
    ) -> tuple[list[list], list[str]]:
        """Get sheet data along with headers.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet
            range_format: Range format string (can contain {sheet_name} placeholder)

        Returns:
            Tuple of (values, headers)

        Raises:
            Exception: If sheet cannot be read
        """
        _, sheets_service = self._get_services()

        range_name = range_format.format(sheet_name=sheet_name)

        try:
            result = (
                sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueRenderOption="UNFORMATTED_VALUE",
                )
                .execute()
            )

            values = result.get("values", [])
            if not values:
                return [], []

            headers = values[0] if values else []
            return values, headers

        except HttpError as error:
            raise Exception(f"Failed to get sheet data: {error}")

    def is_initialized(self) -> bool:
        """Check if the service is properly initialized.

        Returns:
            True if credentials are loaded, False otherwise
        """
        return self._credentials is not None
