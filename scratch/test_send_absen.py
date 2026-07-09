import sys
import os
sys.path.append(os.path.abspath("."))

from main import send_all_attendance_reminders, GROUP_ID_ABSEN, GROUP_ID_ABSEN_PROV

def main():
    print(f"GROUP_ID_ABSEN from config: {GROUP_ID_ABSEN}")
    print(f"GROUP_ID_ABSEN_PROV from config: {GROUP_ID_ABSEN_PROV}")
    
    try:
        print("Attempting to run send_all_attendance_reminders...")
        res = send_all_attendance_reminders(chat_id_to_notify=None, type_absen="malam")
        print(f"Success! Result: {res}")
    except Exception as e:
        print("Failed with exception:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
