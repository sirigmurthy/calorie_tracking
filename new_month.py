#!/usr/bin/env python3
"""Set up a new month's Food Tracker sheet in one command.

Usage:
    python new_month.py <sheet_url_or_id> [year] [month]

This runs all 3 steps:
  1. Populates the blank sheet with template data
  2. Injects all formulas
  3. Applies formatting

Example:
    python new_month.py https://docs.google.com/spreadsheets/d/1abc.../edit 2026 11
"""

import sys
from datetime import date

from upload_template import populate, _extract_sheet_id
from add_formulas import main as add_formulas_main
from format_sheet import main as format_main


def main():
    if len(sys.argv) < 2:
        print("Usage: python new_month.py <sheet_url_or_id> [year] [month]")
        print()
        print("Steps:")
        print("  1. Create a blank Google Sheet in your Drive folder")
        print("  2. Share it with the service account as Editor")
        print("  3. Run this script with the sheet URL")
        sys.exit(1)

    sheet_id = _extract_sheet_id(sys.argv[1])

    if len(sys.argv) >= 4:
        year, month = int(sys.argv[2]), int(sys.argv[3])
    else:
        today = date.today()
        year, month = today.year, today.month

    print("=" * 50)
    print(f"Setting up Food Tracker for {year}-{month:02d}")
    print("=" * 50)

    print("\n[1/3] Populating template...")
    populate(sheet_id, year, month)

    print("\n[2/3] Adding formulas...")
    sys.argv = ["add_formulas.py", sheet_id]
    add_formulas_main()

    print("\n[3/3] Applying formatting...")
    sys.argv = ["format_sheet.py", sheet_id]
    format_main()

    print("\n" + "=" * 50)
    print(f"All done! Sheet is ready for {year}-{month:02d}")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    print("=" * 50)


if __name__ == "__main__":
    main()
