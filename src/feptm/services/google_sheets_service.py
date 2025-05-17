"""Service for working with Google Sheets API."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import Resource, build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from feptm.core.config import settings
from feptm.core.log import log


class GoogleSheetsService:
    """Service for working with Google Sheets API."""

    def __init__(self) -> None:
        """Initialize service with credentials."""
        self.credentials_file = (
            settings.GOOGLE_CREDENTIALS_FILE or self._find_credentials_file()
        )

        # Use path from settings without additional processing
        self.token_file = (
            settings.GOOGLE_TOKEN_FILE or Path.home() / ".google_sheets_token.json"
        )

        self.sheets_service: Optional[Resource] = None
        self.drive_service: Optional[Resource] = None
        self.initialize()

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

    def initialize(self) -> bool:
        """Initialize the Google Drive and Sheets API services.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Set up OAuth 2.0 credentials
            creds = self._get_credentials()
            if not creds:
                log.error("Failed to obtain OAuth credentials")
                return False

            # Build the services
            self.drive_service = build("drive", "v3", credentials=creds)
            self.sheets_service = build("sheets", "v4", credentials=creds)

            log.info("Google Drive and Sheets services initialized successfully")
            return True

        except Exception as e:
            log.error(f"Error initializing Google services: {str(e)}")
            self.drive_service = None
            self.sheets_service = None
            return False

    def _get_credentials(self) -> Optional[UserCredentials]:
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
                log.error(f"Error loading token file: {str(e)}")

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

        return cast(Optional[UserCredentials], creds)

    def create_spreadsheet(self, title: str) -> Dict[str, str]:
        """Create a new Google Sheets spreadsheet.

        Args:
            title: Title of the spreadsheet

        Returns:
            Dictionary with spreadsheet ID and URL
        """
        if not self.sheets_service:
            raise Exception("Sheets service not initialized")

        spreadsheet_body = {
            "properties": {"title": title}
            # We don't create sheets because we copy from templates that already have the needed structure
        }

        try:
            spreadsheet = (
                self.sheets_service.spreadsheets()
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

    def get_sheet_by_name(
        self, spreadsheet_id: str, sheet_name: str
    ) -> Optional[Dict[str, Any]]:
        """Finds a sheet in the spreadsheet by its name.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet to find

        Returns:
            Dictionary with information about the found sheet or None if not found
        """
        if not self.sheets_service:
            raise Exception("Sheets service not initialized")

        try:
            # Get spreadsheet metadata
            spreadsheet_metadata = (
                self.sheets_service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
                .execute()
            )

            # Get list of sheets
            sheets = spreadsheet_metadata.get("sheets", [])
            if not sheets:
                log.warning(
                    f"Warning: No sheets found in the spreadsheet with ID {spreadsheet_id}"
                )
                return None

            # Find sheet with specified name
            target_sheet = None
            available_sheets = []
            for sheet in sheets:
                sheet_title = sheet["properties"]["title"]
                available_sheets.append(sheet_title)
                if sheet_title == sheet_name:
                    target_sheet = sheet
                    break

            if not target_sheet:
                log.warning(
                    f"Warning: Sheet '{sheet_name}' not found. Available sheets: {', '.join(available_sheets)}"
                )
                return None

            return cast(Dict[str, Any], target_sheet)

        except Exception as error:
            log.error(f"Error getting sheet by name: {error}")
            return None

    def create_drive_folder(
        self, folder_name: str, parent_folder_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder
            parent_folder_id: ID of the parent folder (optional)

        Returns:
            Dictionary with folder ID and URL
        """
        if not self.drive_service:
            raise Exception("Drive service not initialized")

        # Prepare folder metadata
        folder_metadata: Dict[str, Any] = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        # If parent folder ID is provided, set it as parent
        if parent_folder_id:
            folder_metadata["parents"] = [parent_folder_id]

        # Create the folder
        try:
            folder = (
                self.drive_service.files()
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
    ) -> Dict[str, str]:
        """Copy a spreadsheet from a template and move it to a folder.

        Args:
            template_id: ID of the template spreadsheet
            new_title: Title for the new spreadsheet
            folder_id: ID of the folder where to place the copy

        Returns:
            Dictionary with spreadsheet ID and URL
        """
        if not self.drive_service:
            raise Exception("Drive service not initialized")

        try:
            # Copy the spreadsheet
            copied_file = (
                self.drive_service.files()
                .copy(fileId=template_id, body={"name": new_title}, fields="id")
                .execute()
            )

            spreadsheet_id = copied_file.get("id")

            # Move the spreadsheet to the specified folder
            self.drive_service.files().update(
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
    ) -> Dict[str, str]:
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

    def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file information from Google Drive.

        Args:
            file_id: ID of the file to get

        Returns:
            Dictionary with file information
        """
        if not self.drive_service:
            raise Exception("Drive service not initialized")

        try:
            result = (
                self.drive_service.files()
                .get(fileId=file_id, fields="id,name,mimeType,parents")
                .execute()
            )
            return cast(Dict[str, Any], result)
        except HttpError as error:
            raise Exception(f"Failed to get file with ID {file_id}: {error}")

    def delete_file(self, file_id: str) -> None:
        """Delete a file from Google Drive.

        Args:
            file_id: ID of the file to delete

        Returns:
            None
        """
        if not self.drive_service:
            raise Exception("Drive service not initialized")

        try:
            self.drive_service.files().delete(fileId=file_id).execute()
        except HttpError as error:
            raise Exception(f"Failed to delete file with ID {file_id}: {error}")

    def move_file(self, file_id: str, folder_id: str) -> None:
        """Move a file to a different folder in Google Drive.

        Args:
            file_id: ID of the file to move
            folder_id: ID of the destination folder

        Returns:
            None
        """
        if not self.drive_service:
            raise Exception("Drive service not initialized")

        try:
            # First get the current parents
            file = (
                self.drive_service.files()
                .get(fileId=file_id, fields="parents")
                .execute()
            )

            # Remove current parents and add new parent
            # Convert list of parents to comma-separated string for removeParents parameter
            parents_list = file.get("parents", [])
            previous_parents = ",".join(parents_list)

            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields="id, parents",
            ).execute()
        except HttpError as error:
            raise Exception(
                f"Failed to move file with ID {file_id} to folder {folder_id}: {error}"
            )

    def clear_range(self, spreadsheet_id: str, range_name: str) -> None:
        """Clear values in a range.

        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to clear (A1 notation)

        Returns:
            None
        """
        if not self.sheets_service:
            raise Exception("Sheets service not initialized")

        try:
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id, range=range_name, body={}
            ).execute()
        except Exception as error:
            log.warning(f"Warning: Failed to clear range {range_name}: {error}")
            # We don't raise an exception here since clearing might be optional

    def update_range(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "RAW",
    ) -> Dict[str, Any]:
        """Update a range in a Google Sheet.

        Args:
            spreadsheet_id: ID of the spreadsheet
            range_name: Range to update (e.g. "Sheet1!A1:B10")
            values: 2D array of values to update
            value_input_option: How to interpret the values ("RAW" or "USER_ENTERED")

        Returns:
            Response from the API
        """
        if not self.sheets_service:
            raise Exception("Sheets service not initialized")

        try:
            result = (
                self.sheets_service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body={"values": values},
                )
                .execute()
            )
            return cast(Dict[str, Any], result)
        except HttpError as error:
            raise Exception(f"Failed to update range {range_name}: {error}")

    def update_sheet_data(
        self, spreadsheet_id: str, sheet_name: str, data: List[List[Any]]
    ) -> Dict[str, Any]:
        """Update a sheet with data.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet to update
            data: 2D array of data to update

        Returns:
            Response from the API
        """
        if not self.sheets_service:
            raise Exception("Sheets service not initialized")

        try:
            # Get the sheet
            sheet = self.get_sheet_by_name(spreadsheet_id, sheet_name)
            if not sheet:
                raise Exception(
                    f"Sheet '{sheet_name}' not found in spreadsheet with ID {spreadsheet_id}"
                )

            sheet_title = sheet["properties"]["title"]

            # First clear the range to remove old data
            self.clear_range(
                spreadsheet_id=spreadsheet_id,
                range_name=f"{sheet_title}!A1:B{len(data) + 5}",  # Add buffer for safety
            )

            # Update the sheet with new data
            response = self.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=f"{sheet_title}!A1:B{len(data)}",
                values=data,
                value_input_option="USER_ENTERED",
            )

            return cast(Dict[str, Any], response)
        except Exception as error:
            raise Exception(f"Failed to update sheet: {error}")

    def batch_update(
        self, spreadsheet_id: str, requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform batch update operations on a Google Sheet.

        Args:
            spreadsheet_id: ID of the spreadsheet
            requests: List of requests to execute

        Returns:
            Response from the API
        """
        if not self.sheets_service:
            raise Exception("Sheets service not initialized")

        try:
            result = (
                self.sheets_service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )
            return cast(Dict[str, Any], result)
        except HttpError as error:
            raise Exception(f"Failed to batch update spreadsheet: {error}")

    def is_initialized(self) -> bool:
        """Check if the service is properly initialized.

        Returns:
            True if both drive and sheets services are initialized, False otherwise
        """
        return self.drive_service is not None and self.sheets_service is not None


# Create singleton instance
google_sheets_service = GoogleSheetsService()
