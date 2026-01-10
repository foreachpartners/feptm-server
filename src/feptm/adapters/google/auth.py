"""Authentication for pygsheets."""

import json
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

    Supports both service account JSON and OAuth client secret JSON files.
    Credentials file must be located in project root as credentials.json.

    Args:
        credentials_file: Optional override path to credentials file
        token_file: Path to token file for OAuth flow (optional)

    Returns:
        Authorized pygsheets client

    Raises:
        GoogleApiError: If authorization fails or credentials file not found
    """
    # Always use credentials.json from project root unless explicitly overridden
    if credentials_file:
        creds_path = Path(credentials_file).resolve()
        if not creds_path.is_absolute():
            creds_path = (settings.BASE_DIR / creds_path).resolve()
    else:
        # Default: credentials.json in project root
        creds_path = (settings.BASE_DIR / "credentials.json").resolve()
    
    token_path = Path(token_file) if token_file else settings.GOOGLE_TOKEN_FILE

    if not creds_path.exists():
        raise GoogleApiError(
            f"Credentials file not found: {creds_path}. "
            f"Please place credentials.json in project root ({settings.BASE_DIR}). "
            f"See README.md for instructions on obtaining credentials."
        )

    try:
        # Read file to determine type (service account vs OAuth client secret)
        with open(creds_path, "r") as f:
            creds_data = json.load(f)
        
        # Service account has 'type' field set to 'service_account'
        if creds_data.get("type") == "service_account":
            log.info(f"Authorizing with service account: {creds_path}")
            gc = pygsheets.authorize(service_file=str(creds_path))
        # OAuth client secret has 'installed' or 'web' field with 'client_id' and 'client_secret'
        elif "installed" in creds_data or "web" in creds_data:
            log.info(f"Authorizing with OAuth client secret: {creds_path}")
            gc = pygsheets.authorize(
                client_secret=str(creds_path),
                credentials_directory=str(token_path.parent) if token_path else None,
            )
        else:
            raise GoogleApiError(
                f"Unknown credentials format in {creds_path}. "
                f"Expected service account JSON or OAuth client secret JSON. "
                f"See README.md for correct format."
            )

        log.info("Successfully authorized pygsheets client")
        return gc

    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in credentials file: {e}")
        raise GoogleApiError(f"Credentials file is not valid JSON: {e}") from e
    except Exception as e:
        log.error(f"Failed to authorize pygsheets: {e}")
        raise GoogleApiError(f"Authorization failed: {e}") from e
