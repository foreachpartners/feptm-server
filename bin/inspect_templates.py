#!/usr/bin/env python
"""Inspect all configured Google Sheets templates.

Usage:
    uv run python bin/inspect_templates.py

Shows structure of all templates configured in .env:
- GOOGLE_PROJECT_INFO_TEMPLATE_ID
- GOOGLE_PROJECT_REPORT_TEMPLATE_ID
- GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID
- GOOGLE_TIMESHEET_TEMPLATE_ID
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from feptm.adapters.google.auth import authorize_pygsheets
from feptm.core.config import settings


def inspect_template(gc, template_id: str, template_name: str) -> None:
    """Inspect a single template."""
    if not template_id:
        print(f"\n=== {template_name} ===")
        print("  NOT CONFIGURED")
        return
    
    print(f"\n{'='*60}")
    print(f"=== {template_name} ===")
    print(f"{'='*60}")
    print(f"ID: {template_id}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{template_id}")
    
    try:
        ss = gc.open_by_key(template_id)
        print(f"Title: {ss.title}")
        print()
        
        for ws in ss.worksheets():
            print(f"📋 Sheet: {ws.title}")
            print(f"   Size: {ws.rows} rows x {ws.cols} cols")
            
            # Get header row
            try:
                headers = ws.get_values("A1", "Z1")
                if headers and headers[0]:
                    cols = []
                    for i, h in enumerate(headers[0]):
                        if h:
                            col_letter = chr(ord('A') + i)
                            cols.append(f"{col_letter}: {h}")
                    if cols:
                        print(f"   Columns: {' | '.join(cols)}")
                
                # Get sample data (rows 2-4)
                data = ws.get_values("A2", "Z4")
                if data:
                    print(f"   Sample data ({len(data)} rows):")
                    for i, row in enumerate(data, start=2):
                        row_str = " | ".join(str(c)[:20] if c else "" for c in row[:7])
                        print(f"     Row {i}: {row_str}")
            except Exception as e:
                print(f"   (error reading: {e})")
            print()
            
    except Exception as e:
        print(f"ERROR: {e}")


def main():
    print("Connecting to Google Sheets...")
    gc = authorize_pygsheets()
    
    templates = [
        (settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID, "Project Info Template"),
        (settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID, "General Expenses Report Template"),
        (settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID, "Payment Distribution Template"),
        (settings.GOOGLE_TIMESHEET_TEMPLATE_ID, "Timesheet Template"),
    ]
    
    print("\n" + "="*60)
    print("CONFIGURED TEMPLATES")
    print("="*60)
    
    for template_id, template_name in templates:
        inspect_template(gc, template_id, template_name)
    
    # Also show projects folder
    print("\n" + "="*60)
    print("PROJECTS FOLDER")
    print("="*60)
    if settings.GOOGLE_PROJECTS_FOLDER_ID:
        print(f"ID: {settings.GOOGLE_PROJECTS_FOLDER_ID}")
        print(f"URL: https://drive.google.com/drive/folders/{settings.GOOGLE_PROJECTS_FOLDER_ID}")
    else:
        print("NOT CONFIGURED")


if __name__ == "__main__":
    main()
