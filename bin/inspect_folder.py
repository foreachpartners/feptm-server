#!/usr/bin/env python
"""Inspect Google Drive folder contents.

Usage:
    uv run python bin/inspect_folder.py <folder_id>
    uv run python bin/inspect_folder.py <folder_url>

Examples:
    uv run python bin/inspect_folder.py 1kw8rS5F0ttZui9oT-CT1VGJutg4zFKZT
    uv run python bin/inspect_folder.py "https://drive.google.com/drive/folders/1kw8rS5F0ttZui9oT-CT1VGJutg4zFKZT"
"""

import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from feptm.adapters.google.auth import authorize_pygsheets


def extract_folder_id(input_str: str) -> str:
    """Extract folder ID from URL or return as-is if already an ID."""
    if "drive.google.com" in input_str:
        match = re.search(r"folders/([a-zA-Z0-9_-]+)", input_str)
        if match:
            return match.group(1)
    return input_str.strip()


def list_folder_contents(drive, folder_id: str, indent: int = 0) -> None:
    """List folder contents recursively."""
    prefix = "  " * indent
    
    results = drive.service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType, createdTime, modifiedTime)",
        orderBy="name",
        supportsAllDrives=True,
    ).execute()
    
    files = results.get("files", [])
    
    for f in files:
        name = f["name"]
        mime = f["mimeType"]
        file_id = f["id"]
        
        if mime == "application/vnd.google-apps.folder":
            print(f"{prefix}📁 {name}/")
            print(f"{prefix}   ID: {file_id}")
            # Recursively list subfolder
            list_folder_contents(drive, file_id, indent + 1)
        elif mime == "application/vnd.google-apps.spreadsheet":
            print(f"{prefix}📊 {name}")
            print(f"{prefix}   ID: {file_id}")
            print(f"{prefix}   URL: https://docs.google.com/spreadsheets/d/{file_id}")
        else:
            print(f"{prefix}📄 {name}")
            print(f"{prefix}   ID: {file_id}")
            print(f"{prefix}   Type: {mime}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    folder_input = sys.argv[1]
    folder_id = extract_folder_id(folder_input)
    
    print(f"Connecting to Google Drive...")
    gc = authorize_pygsheets()
    drive = gc.drive
    
    # Get folder name
    try:
        folder_info = drive.service.files().get(
            fileId=folder_id,
            fields="name",
            supportsAllDrives=True,
        ).execute()
        folder_name = folder_info.get("name", "Unknown")
    except Exception:
        folder_name = "Unknown"
    
    print(f"\n=== Folder: {folder_name} ===")
    print(f"ID: {folder_id}")
    print(f"URL: https://drive.google.com/drive/folders/{folder_id}")
    print()
    
    list_folder_contents(drive, folder_id)


if __name__ == "__main__":
    main()
