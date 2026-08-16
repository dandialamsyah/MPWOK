import sys
import os
sys.path.append(os.path.abspath("."))

from sheets_handler import get_worksheet, SHEET_NAME
import gspread
from google.oauth2.service_account import Credentials

def main():
    print(f"Spreadsheet Name: {SHEET_NAME}")
    ws = get_worksheet("LAPORAN MPW")
    if not ws:
        print("Sheet 'LAPORAN MPW' not found via get_worksheet")
        return
    rows = ws.get_all_values()
    print(f"Total rows: {len(rows)}")
    if rows:
        print("Headers:")
        print(rows[0])
        print("Rows:")
        for r in rows[1:6]:
            print(r)

if __name__ == "__main__":
    main()
