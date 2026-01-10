#!/usr/bin/env python
"""Utility script to extract service account email from credentials.json."""

import json
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from feptm.core.config import settings


def main() -> int:
    """Extract and display service account email from credentials.json."""
    creds_path = settings.BASE_DIR / "credentials.json"

    if not creds_path.exists():
        print(f"ERROR: credentials.json not found at {creds_path}", file=sys.stderr)
        print("Please ensure credentials.json is in project root.", file=sys.stderr)
        return 1

    try:
        with open(creds_path, "r") as f:
            creds_data = json.load(f)

        cred_type = creds_data.get("type", "unknown")

        if cred_type == "service_account":
            email = creds_data.get("client_email")
            if email:
                print(f"Service Account Email: {email}")
                print("\nUse this email to share files and folders:")
                print("1. Open Google Drive in browser")
                print("2. Right-click on file/folder > Share")
                print(f"3. Paste: {email}")
                print("4. Set permission to 'Editor'")
                print("5. Click 'Send' (uncheck 'Notify people')")
                return 0
            else:
                print("ERROR: client_email not found in credentials.json", file=sys.stderr)
                return 1
        elif "installed" in creds_data or "web" in creds_data:
            print("INFO: Using OAuth credentials (not service account)")
            print("OAuth credentials don't need file sharing - authentication handles access.")
            return 0
        else:
            print(f"ERROR: Unknown credentials type: {cred_type}", file=sys.stderr)
            return 1

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in credentials.json: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
