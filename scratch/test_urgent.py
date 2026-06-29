import sys
import os
sys.path.append(os.path.abspath("."))

# Reconfigure stdout to use UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from sheets_handler import get_open_tickets_data, fetch_open_tickets_alert, fetch_rekap_data

def main():
    print("Testing get_open_tickets_data for 'TIKET URGENT MPW'...")
    open_tickets = get_open_tickets_data("TIKET URGENT MPW")
    print(f"Found {len(open_tickets)} open urgent tickets.")
    for i, t in enumerate(open_tickets):
        print(f"[{i+1}] Incident: {t['incident']}, Team: {t['team']}, Status: {t['status']}, Device: {t['device']}, CustType: {t['cust_type']}, Duration: {t['duration']}")
    
    print("\nTesting fetch_open_tickets_alert for 'TIKET URGENT MPW'...")
    alert_msg = fetch_open_tickets_alert(client=None, model_id=None, sheet_name="TIKET URGENT MPW")
    print("--- ALERT MESSAGE ---")
    print(alert_msg)
    print("---------------------\n")
    
    print("Testing fetch_rekap_data for 'TIKET URGENT MPW'...")
    rekap_msg = fetch_rekap_data("TIKET URGENT MPW")
    print("--- REKAP MESSAGE ---")
    print(rekap_msg)
    print("---------------------")

if __name__ == "__main__":
    main()
