#!/usr/bin/env python
"""Add test specialists to a project's Team sheet.

Usage:
    uv run python bin/add_test_specialists.py <project_id>
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from feptm.adapters.google.auth import authorize_pygsheets


TEST_SPECIALISTS = [
    # Name, Role, Project, Internal Rate, External Rate, Date, Timesheet
    ["Alice", "Developer", "Backend", "15", "20", "2025-01-01", ""],
    ["Bob", "Designer", "UI/UX", "12", "18", "2025-01-01", ""],
]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    project_id = sys.argv[1]
    
    print("Connecting to Google Sheets...")
    gc = authorize_pygsheets()
    
    print(f"Opening project: {project_id}")
    ss = gc.open_by_key(project_id)
    
    ws = ss.worksheet_by_title("Team")
    if not ws:
        print("Team sheet not found!")
        sys.exit(1)
    
    print("Adding test specialists...")
    for i, specialist in enumerate(TEST_SPECIALISTS, start=2):
        ws.update_values(crange=f"A{i}", values=[specialist])
        print(f"  Added: {specialist[0]} - {specialist[1]}")
    
    print("Done! Test specialists added to Team sheet.")


if __name__ == "__main__":
    main()
