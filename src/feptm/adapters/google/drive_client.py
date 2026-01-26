"""Google Drive operations via pygsheets internal client."""

from typing import TYPE_CHECKING, Optional

import pygsheets

from feptm.core.exceptions import GoogleApiError, NotFoundError
from feptm.core.log import log

if TYPE_CHECKING:
    from pygsheets.client import Client


class GoogleDriveClient:
    """Google Drive operations via pygsheets internal client."""

    def __init__(self, gc: "Client") -> None:
        """Initialize GoogleDriveClient.

        Args:
            gc: Authorized pygsheets client
        """
        self._drive = gc.drive

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create folder, return folder ID.

        Args:
            name: Folder name
            parent_id: Parent folder ID (optional)

        Returns:
            Created folder ID

        Raises:
            GoogleApiError: If folder creation fails
        """
        try:
            log.debug(f"Creating folder: {name} (parent: {parent_id})")
            folder_metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                folder_metadata["parents"] = [parent_id]

            # supportsAllDrives=True enables support for Shared Drives (Google Workspace)
            # This is required when creating folders in Shared Drives or when using service accounts
            folder = (
                self._drive.service.files()
                .create(body=folder_metadata, fields="id", supportsAllDrives=True)
                .execute()
            )

            folder_id = folder["id"]
            log.info(f"Created folder: {folder_id}")
            return folder_id
        except Exception as e:
            log.error(f"Failed to create folder: {e}")
            raise GoogleApiError(f"Failed to create folder: {e}") from e

    def move_file(self, file_id: str, folder_id: str) -> None:
        """Move file to folder.

        Args:
            file_id: File ID to move
            folder_id: Destination folder ID

        Raises:
            NotFoundError: If file or folder not found
            GoogleApiError: If move operation fails
        """
        try:
            log.debug(f"Moving file {file_id} to folder {folder_id}")
            # pygsheets drive.move_file may need different parameters
            # Using low-level API call if needed
            self._drive.move_file(file_id, folder_id)
            log.info(f"Moved file {file_id} to folder {folder_id}")
        except (pygsheets.SpreadsheetNotFound, Exception) as e:
            if isinstance(e, pygsheets.SpreadsheetNotFound):
                raise NotFoundError(f"File not found: {file_id}")
            log.error(f"Failed to move file: {e}")
            raise GoogleApiError(f"Failed to move file: {e}") from e

    def delete_file(self, file_id: str) -> None:
        """Delete file by ID.

        Args:
            file_id: File ID to delete

        Raises:
            NotFoundError: If file not found
            GoogleApiError: If delete operation fails
        """
        try:
            log.debug(f"Deleting file: {file_id}")
            self._drive.delete(file_id)
            log.info(f"Deleted file: {file_id}")
        except pygsheets.SpreadsheetNotFound:
            raise NotFoundError(f"File not found: {file_id}")
        except Exception as e:
            log.error(f"Failed to delete file: {e}")
            raise GoogleApiError(f"Failed to delete file: {e}") from e

    def get_folder_url(self, folder_id: str) -> str:
        """Generate Drive folder URL.

        Args:
            folder_id: Folder ID

        Returns:
            Folder URL
        """
        return f"https://drive.google.com/drive/folders/{folder_id}"
