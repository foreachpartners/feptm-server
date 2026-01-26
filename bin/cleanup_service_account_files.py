#!/usr/bin/env python
"""Script to list and delete files owned by service account."""

import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from feptm.adapters.google.auth import authorize_pygsheets
from feptm.core.log import log


def list_files(gc, page_size: int = 100):
    """List all files owned by service account."""
    drive = gc.drive
    
    # Query all files (service account only sees files it owns or has access to)
    results = drive.service.files().list(
        pageSize=page_size,
        fields="nextPageToken, files(id, name, mimeType, size, createdTime, parents)",
        q="'me' in owners",  # Only files owned by this account
    ).execute()
    
    files = results.get("files", [])
    return files


def delete_file(gc, file_id: str):
    """Delete a file by ID."""
    gc.drive.delete(file_id)


def main():
    print("Connecting to Google Drive as service account...")
    gc = authorize_pygsheets()
    
    print("\nListing files owned by service account:\n")
    files = list_files(gc)
    
    if not files:
        print("No files found. Service account's Drive is empty.")
        return
    
    total_size = 0
    print(f"{'#':<4} {'Name':<50} {'Type':<30} {'Size':<15} {'Created'}")
    print("-" * 120)
    
    for i, f in enumerate(files, 1):
        name = f.get("name", "Unknown")[:48]
        mime_type = f.get("mimeType", "Unknown")[:28]
        size = int(f.get("size", 0))
        total_size += size
        size_str = f"{size / 1024 / 1024:.2f} MB" if size > 0 else "N/A"
        created = f.get("createdTime", "Unknown")[:10]
        
        print(f"{i:<4} {name:<50} {mime_type:<30} {size_str:<15} {created}")
    
    print("-" * 120)
    print(f"Total files: {len(files)}")
    print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
    
    print("\nOptions:")
    print("  1. Delete ALL files (clear service account's Drive)")
    print("  2. Delete specific file by number")
    print("  3. Exit without deleting")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        confirm = input(f"Are you sure you want to delete ALL {len(files)} files? (yes/no): ").strip()
        if confirm.lower() == "yes":
            for f in files:
                try:
                    delete_file(gc, f["id"])
                    print(f"Deleted: {f['name']}")
                except Exception as e:
                    print(f"Failed to delete {f['name']}: {e}")
            print("\nDone! Service account's Drive has been cleared.")
        else:
            print("Cancelled.")
    
    elif choice == "2":
        try:
            num = int(input("Enter file number to delete: ").strip())
            if 1 <= num <= len(files):
                f = files[num - 1]
                confirm = input(f"Delete '{f['name']}'? (yes/no): ").strip()
                if confirm.lower() == "yes":
                    delete_file(gc, f["id"])
                    print(f"Deleted: {f['name']}")
                else:
                    print("Cancelled.")
            else:
                print("Invalid number.")
        except ValueError:
            print("Invalid input.")
    
    else:
        print("Exiting without changes.")


if __name__ == "__main__":
    main()
