#!/usr/bin/env python
"""Inspect a FEPTM project structure and data.

Usage:
    uv run python bin/inspect_project.py <project_info_spreadsheet_id>

Shows:
- Project Info sheet content
- Team sheet with all specialists
- Links to related spreadsheets (Report, Calculations)
- Timesheets for each specialist
"""

import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from feptm.adapters.google.auth import authorize_pygsheets


def extract_id_from_url(url: str) -> str | None:
    """Extract ID from Google URL."""
    if not url:
        return None
    if "spreadsheets/d/" in url:
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
    if "folders/" in url:
        match = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
    return None


def extract_id_from_hyperlink_formula(gc, ws, cell_addr: str) -> str | None:
    """Extract ID from HYPERLINK formula in cell."""
    try:
        cell = ws.cell(cell_addr)
        formula = cell.formula
        if formula:
            return extract_id_from_url(formula)
        # Try value as URL
        value = cell.value
        if value:
            return extract_id_from_url(str(value))
    except Exception:
        pass
    return None


def print_table(data: list, indent: int = 0) -> None:
    """Print data as simple table."""
    prefix = "  " * indent
    if not data:
        print(f"{prefix}(empty)")
        return
    
    for i, row in enumerate(data):
        row_str = " | ".join(str(c)[:25] if c else "" for c in row)
        if i == 0:
            print(f"{prefix}Header: {row_str}")
            print(f"{prefix}" + "-" * 60)
        else:
            print(f"{prefix}Row {i+1}: {row_str}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    project_id = sys.argv[1]
    if "docs.google.com" in project_id:
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", project_id)
        if match:
            project_id = match.group(1)
    
    print("Connecting to Google Sheets...")
    gc = authorize_pygsheets()
    drive = gc.drive
    
    print(f"\n{'='*70}")
    print("PROJECT INSPECTION")
    print(f"{'='*70}")
    print(f"Project Info ID: {project_id}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{project_id}")
    
    ss = gc.open_by_key(project_id)
    print(f"Title: {ss.title}")
    
    # 1. Project Info sheet
    print(f"\n{'='*70}")
    print("PROJECT INFO SHEET")
    print(f"{'='*70}")
    ws = ss.worksheet_by_title("Project info")
    if ws:
        data = ws.get_values("A1", "B10")
        for row in data:
            if len(row) >= 2:
                print(f"  {row[0]}: {row[1][:50] if row[1] else ''}")
        
        # Extract linked IDs
        folder_id = None
        report_id = None
        calculations_id = None
        
        for i, row in enumerate(data, start=1):
            if len(row) >= 1:
                field = str(row[0]).strip()
                if field == "Project Folder":
                    folder_id = extract_id_from_hyperlink_formula(gc, ws, f"B{i}")
                elif field == "General Expenses":
                    report_id = extract_id_from_hyperlink_formula(gc, ws, f"B{i}")
                elif field == "Payment Distribution":
                    calculations_id = extract_id_from_hyperlink_formula(gc, ws, f"B{i}")
    else:
        print("  (Project info sheet not found)")
        folder_id = report_id = calculations_id = None
    
    # 2. Team sheet
    print(f"\n{'='*70}")
    print("TEAM SHEET")
    print(f"{'='*70}")
    ws = ss.worksheet_by_title("Team")
    if ws:
        data = ws.get_values("A1", "G20")
        print_table(data)
        
        # Extract timesheet IDs
        timesheet_ids = []
        if data and len(data) > 1:
            # Find Timesheet column (usually last)
            header = data[0]
            timesheet_col = None
            for i, h in enumerate(header):
                if h and "timesheet" in str(h).lower():
                    timesheet_col = i
                    break
            
            if timesheet_col is not None:
                for row in data[1:]:
                    if len(row) > timesheet_col and row[timesheet_col]:
                        ts_id = str(row[timesheet_col]).strip()
                        if ts_id and len(ts_id) > 10:  # Looks like an ID
                            name = row[0] if row else "Unknown"
                            timesheet_ids.append((name, ts_id))
    else:
        print("  (Team sheet not found)")
        timesheet_ids = []
    
    # 3. Project Folder contents
    if folder_id:
        print(f"\n{'='*70}")
        print("PROJECT FOLDER CONTENTS")
        print(f"{'='*70}")
        print(f"Folder ID: {folder_id}")
        
        try:
            results = drive.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType)",
                orderBy="name",
                supportsAllDrives=True,
            ).execute()
            
            files = results.get("files", [])
            for f in files:
                emoji = "📁" if "folder" in f["mimeType"] else "📊" if "spreadsheet" in f["mimeType"] else "📄"
                print(f"  {emoji} {f['name']}")
                print(f"     ID: {f['id']}")
        except Exception as e:
            print(f"  (error listing folder: {e})")
    
    # 4. Timesheets
    if timesheet_ids:
        print(f"\n{'='*70}")
        print("TIMESHEETS")
        print(f"{'='*70}")
        
        for name, ts_id in timesheet_ids:
            print(f"\n📋 Timesheet for: {name}")
            print(f"   ID: {ts_id}")
            print(f"   URL: https://docs.google.com/spreadsheets/d/{ts_id}")
            
            try:
                ts_ss = gc.open_by_key(ts_id)
                print(f"   Title: {ts_ss.title}")
                print(f"   Sheets: {', '.join(ws.title for ws in ts_ss.worksheets())}")
            except Exception as e:
                print(f"   (error opening: {e})")
    else:
        print(f"\n{'='*70}")
        print("TIMESHEETS")
        print(f"{'='*70}")
        print("  No timesheets found (Timesheet column empty)")
    
    # 5. Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Project Info: {project_id}")
    print(f"  Folder: {folder_id or 'NOT FOUND'}")
    print(f"  General Expenses: {report_id or 'NOT FOUND'}")
    print(f"  Payment Distribution: {calculations_id or 'NOT FOUND'}")
    print(f"  Timesheets: {len(timesheet_ids)} found")


if __name__ == "__main__":
    main()
