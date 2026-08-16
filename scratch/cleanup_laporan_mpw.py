import sys
import os
sys.path.append(os.path.abspath("."))

from sheets_handler import get_worksheet

def main():
    print("Cleaning up test data in LAPORAN MPW sheet...")
    ws = get_worksheet("LAPORAN MPW")
    if ws:
        rows = ws.get_all_values()
        if len(rows) > 1:
            ws.delete_rows(2, len(rows))
            print("Successfully cleaned up test rows!")
        else:
            print("No test rows to clean up.")

if __name__ == "__main__":
    main()
