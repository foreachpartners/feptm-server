"""Authentication for pygsheets."""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pygsheets

from feptm.core.config import settings
from feptm.core.exceptions import GoogleApiError
from feptm.core.log import log

if TYPE_CHECKING:
    from pygsheets.client import Client


def authorize_pygsheets(
    credentials_file: Optional[str | Path] = None,
    token_file: Optional[str | Path] = None,
) -> "Client":
    """Authorize pygsheets client.

    Supports both service account (JSON file) and OAuth flows.

    Args:
        credentials_file: Path to credentials file (service account JSON or OAuth client secret)
        token_file: Path to token file for OAuth flow (optional)

    Returns:
        Authorized pygsheets client

    Raises:
        GoogleApiError: If authorization fails
    """
    creds_path = Path(credentials_file) if credentials_file else settings.GOOGLE_CREDENTIALS_FILE
    token_path = Path(token_file) if token_file else settings.GOOGLE_TOKEN_FILE

    if not creds_path:
        raise GoogleApiError(
            "Credentials file not specified. Set GOOGLE_CREDENTIALS_FILE in settings."
        )

    if not creds_path.exists():
        raise GoogleApiError(f"Credentials file not found: {creds_path}")

    try:
        # Service account (JSON file)
        if creds_path.suffix == ".json":
            log.info(f"Authorizing with service account: {creds_path}")
            gc = pygsheets.authorize(service_file=str(creds_path))
        else:
            # OAuth flow
            log.info(f"Authorizing with OAuth client secret: {creds_path}")
            gc = pygsheets.authorize(
                client_secret=str(creds_path),
                credentials_directory=str(token_path.parent) if token_path else None,
            )

        log.info("Successfully authorized pygsheets client")
        return gc

    except Exception as e:
        log.error(f"Failed to authorize pygsheets: {e}")
        raise GoogleApiError(f"Authorization failed: {e}") from e
