import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO)

try:
    from dashboard_server import compile_dashboard_data
    print("Inisialisasi berhasil. Mencoba mengambil data dashboard...")
    data = compile_dashboard_data()
    print("Data dashboard berhasil diambil:")
    print(f"- Timestamp: {data['timestamp']}")
    print(f"- MPW Open Tickets: {len(data['mpw']['tickets'])}")
    print(f"- STA Open Tickets: {len(data['sta']['tickets'])}")
    print(f"- Unspec STA Open Tickets: {len(data['unspec_sta']['tickets'])}")
    print(f"- Urgent MPW Open Tickets: {len(data['urgent_mpw']['tickets'])}")
    print(f"- Urgent STA Open Tickets: {len(data['urgent_sta']['tickets'])}")
    print(f"- PSB Grand Total: {data['psb']['grand_total']}")
    print("SUCCESS: VERIFIKASI SELESAI & SUKSES!")
except Exception as e:
    print(f"FAILED: TERJADI KESALAHAN SAAT VERIFIKASI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
