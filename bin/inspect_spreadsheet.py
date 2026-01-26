#!/usr/bin/env python
"""Inspect Google Spreadsheet structure and content.

Usage:
    uv run python bin/inspect_spreadsheet.py <spreadsheet_id> [sheet_name] [range]

Examples:
    # List all sheets
    uv run python bin/inspect_spreadsheet.py 1LJRcO4TxwmWK76w4ZfLScaWi2ZJasj4TOPQJkUjwlwk

    # View specific sheet
    uv run python bin/inspect_spreadsheet.py 1LJRcO4TxwmWK76w4ZfLScaWi2ZJasj4TOPQJkUjwlwk "Team"

    # View specific range
    uv run python bin/inspect_spreadsheet.py 1LJRcO4TxwmWK76w4ZfLScaWi2ZJasj4TOPQJkUjwlwk "Team" "A1:G10"

    # From URL
    uv run python bin/inspect_spreadsheet.py "https://docs.google.com/spreadsheets/d/1LJRcO4TxwmWK76w4ZfLScaWi2ZJasj4TOPQJkUjwlwk/edit"
"""

import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from feptm.adapters.google.auth import authorize_pygsheets


def extract_spreadsheet_id(input_str: str) -> str:
    """Extract spreadsheet ID from URL or return as-is if already an ID."""
    if "docs.google.com" in input_str:
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", input_str)
        if match:
            return match.group(1)
    return input_str.strip()


def print_sheet_info(ws) -> None:
    """Print worksheet info."""
    print(f"  📋 {ws.title}")
    print(f"     Rows: {ws.rows}, Cols: {ws.cols}")


def print_data_table(data: list, max_col_width: int = 30) -> None:
    """Print data as formatted table."""
    if not data:
        print("     (empty)")
        return
    
    # Calculate column widths
    col_count = max(len(row) for row in data) if data else 0
    col_widths = [0] * col_count
    
    for row in data:
        for i, cell in enumerate(row):
            cell_str = str(cell) if cell else ""
            col_widths[i] = min(max(col_widths[i], len(cell_str)), max_col_width)
    
    # Print header row
    if data:
        header = data[0]
        header_strs = []
        for i, cell in enumerate(header):
            cell_str = str(cell) if cell else ""
            if len(cell_str) > max_col_width:
                cell_str = cell_str[:max_col_width-3] + "..."
            header_strs.append(cell_str.ljust(col_widths[i]))
        print("     " + " | ".join(header_strs))
        print("     " + "-+-".join("-" * w for w in col_widths))
    
    # Print data rows
    for row_idx, row in enumerate(data[1:], start=2):
        row_strs = []
        for i in range(col_count):
            cell = row[i] if i < len(row) else ""
            cell_str = str(cell) if cell else ""
            if len(cell_str) > max_col_width:
                cell_str = cell_str[:max_col_width-3] + "..."
            row_strs.append(cell_str.ljust(col_widths[i] if i < len(col_widths) else 10))
        print(f"  {row_idx:2d}: " + " | ".join(row_strs))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    spreadsheet_input = sys.argv[1]
    sheet_name = sys.argv[2] if len(sys.argv) > 2 else None
    cell_range = sys.argv[3] if len(sys.argv) > 3 else "A1:Z20"
    
    spreadsheet_id = extract_spreadsheet_id(spreadsheet_input)
    
    print(f"Connecting to Google Sheets...")
    gc = authorize_pygsheets()
    
    print(f"\n=== Opening spreadsheet ===")
    print(f"ID: {spreadsheet_id}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    
    ss = gc.open_by_key(spreadsheet_id)
    print(f"Title: {ss.title}")
    print()
    
    print("=== Sheets ===")
    for ws in ss.worksheets():
        print_sheet_info(ws)
    print()
    
    if sheet_name:
        print(f"=== Content of '{sheet_name}' ({cell_range}) ===")
        ws = ss.worksheet_by_title(sheet_name)
        if ws:
            # Parse range
            if ":" in cell_range:
                start, end = cell_range.split(":")
            else:
                start, end = cell_range, cell_range
            
            data = ws.get_values(start, end)
            print_data_table(data)
            
            # Also show formulas for first few cells
            print()
            print("=== Formulas (if any) ===")
            try:
                for row_idx in range(1, min(6, len(data) + 1)):
                    for col_idx in range(1, min(8, (len(data[0]) if data else 0) + 1)):
                        cell = ws.cell((row_idx, col_idx))
                        if cell.formula:
                            col_letter = chr(ord('A') + col_idx - 1)
                            print(f"  {col_letter}{row_idx}: {cell.formula}")
            except Exception as e:
                print(f"  (could not read formulas: {e})")
        else:
            print(f"  Sheet '{sheet_name}' not found!")
    else:
        # Show first 10 rows of each sheet
        for ws in ss.worksheets():
            print(f"=== Content of '{ws.title}' (A1:G10) ===")
            try:
                data = ws.get_values("A1", "G10")
                print_data_table(data)
            except Exception as e:
                print(f"  (error reading sheet: {e})")
            print()


if __name__ == "__main__":
    main()
