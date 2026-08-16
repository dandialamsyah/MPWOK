import sys
import os
import time
sys.path.append(os.path.abspath("."))

from sheets_handler import parse_report_text, save_report_to_sheet

def test():
    print("Testing parse_report_text...")
    test_text = (
        "FORMAT LAPORAN GANGGUAN MEMPAWAH\n"
        "/request\n"
        "\n"
        "INET : 162407226877\n"
        "NAMA : ACHMAD MASYHURILIANSYAH\n"
        "CP AKTIF WA : 081234567890\n"
        "ALAMAT : JALAN RAYA MEMPAWAH NO. 10\n"
        "KENDALA : Inet tidak bisa di gunakan\n"
        "modem LOS merah terus sejak pagi"
    )
    
    parsed = parse_report_text(test_text)
    print("Parsed result:")
    for k, v in parsed.items():
        print(f"  {k}: {repr(v)}")
        
    print("\nSaving to Google Sheets...")
    sender_id = 999999999
    username = "test_user_new"
    sender_name = "New Test User"
    msg_timestamp = int(time.time())
    
    try:
        returned_id = save_report_to_sheet(
            report_text=test_text,
            sender_id=sender_id,
            username=username,
            sender_name=sender_name,
            msg_timestamp=msg_timestamp
        )
        if returned_id:
            print(f"Successfully saved report to Google Sheet! Generated ID: {returned_id}")
        else:
            print("Failed to save report to Google Sheet.")
    except Exception as e:
        print(f"Exception raised: {e}")

if __name__ == "__main__":
    test()
