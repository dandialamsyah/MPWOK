import sys
import os
sys.path.append(os.path.abspath("."))
# Reconfigure stdout to use UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from sheets_handler import fetch_rekap_data, fetch_open_tickets_alert

def main():
    print("Testing fetch_rekap_data for 'UNDSEPC STA'...")
    rekap_res = fetch_rekap_data("UNDSEPC STA")
    print("--- REKAP RESULT ---")
    print(rekap_res)
    print("--------------------\n")

    print("Testing fetch_open_tickets_alert for 'UNDSEPC STA'...")
    open_res = fetch_open_tickets_alert(client=None, model_id=None, sheet_name="UNDSEPC STA")
    print("--- OPEN ALERTS RESULT ---")
    print(open_res)
    print("--------------------------")

if __name__ == "__main__":
    main()
