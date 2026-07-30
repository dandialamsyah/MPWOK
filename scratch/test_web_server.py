import sys
import os
import time
import urllib.request
import json
import threading

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard_server import start_dashboard_server

# Start server in a background daemon thread
t = threading.Thread(target=start_dashboard_server, daemon=True)
t.start()

print("Menunggu server menyala (3 detik)...")
time.sleep(3)

print("Menguji HTTP GET / ...")
try:
    with urllib.request.urlopen("http://localhost:5000/") as response:
        html = response.read().decode('utf-8')
        print(f"Status: {response.status}")
        print(f"HTML Length: {len(html)}")
        if "<title>MPWOK Bot Dashboard</title>" in html:
            print("OK: HTML page title found!")
        else:
            print("FAIL: Title not found in HTML page")
except Exception as e:
    print(f"FAIL: Error fetching /: {e}")
    sys.exit(1)

print("\nMenguji HTTP GET /api/data ...")
try:
    with urllib.request.urlopen("http://localhost:5000/api/data") as response:
        data_bytes = response.read()
        print(f"Status: {response.status}")
        data = json.loads(data_bytes.decode('utf-8'))
        print(f"Data status: {data['status']}")
        print(f"Timestamp: {data['data']['timestamp']}")
        print(f"MPW Open Tickets: {len(data['data']['mpw']['tickets'])}")
        print("OK: JSON API responds correctly!")
except Exception as e:
    print(f"FAIL: Error fetching /api/data: {e}")
    sys.exit(1)

print("\nSUCCESS: Dashboard Web Server dan API berjalan dengan baik!")
sys.exit(0)
