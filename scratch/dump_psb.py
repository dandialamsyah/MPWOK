import sys
import os
sys.path.append(os.path.abspath("."))

import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_NAME

def main():
    SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
    gc = gspread.authorize(creds)
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("PSB")
    rows = ws.get_all_values()
    print("ALL PSB ROWS:")
    for r in rows:
        print(r)

if __name__ == "__main__":
    main()
