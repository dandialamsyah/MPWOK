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
    
    print("\nAvailable Worksheets:")
    worksheets = sh.worksheets()
    for ws in worksheets:
        print(f"- {ws.title}")
        
    print("\nChecking sheet 'PSB'...")
    try:
        ws_psb = sh.worksheet("PSB")
        print("Sheet 'PSB' found!")
        rows = ws_psb.get_all_values()
        if not rows:
            print("PSB sheet is empty.")
        else:
            print(f"Total rows in PSB: {len(rows)}")
            print("Headers:")
            print(rows[0])
            print("First 3 rows of data:")
            for r in rows[1:4]:
                print(r)
    except Exception as e:
        print(f"Error opening sheet 'PSB': {e}")

if __name__ == "__main__":
    main()
