import sys
import os
sys.path.append(os.path.abspath("."))

from sheets_handler import get_worksheet, SHEET_NAME
import gspread
from google.oauth2.service_account import Credentials

def main():
    print(f"Spreadsheet Name: {SHEET_NAME}")
    SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
    gc = gspread.authorize(creds)
    sh = gc.open(SHEET_NAME)
    
    print("\nChecking sheet 'TIKET URGENT MPW'...")
    try:
        ws_urgent = sh.worksheet("TIKET URGENT MPW")
        print("Sheet found!")
        rows = ws_urgent.get_all_values()
        if not rows:
            print("TIKET URGENT MPW sheet is empty.")
        else:
            print(f"Total rows in TIKET URGENT MPW: {len(rows)}")
            print("Headers:")
            print(rows[0])
            print("First 5 rows of data:")
            for i, r in enumerate(rows[1:6]):
                print(f"Row {i+1}: {r}")
    except Exception as e:
        print(f"Error opening sheet: {e}")

if __name__ == "__main__":
    main()
