import sys
import os
sys.path.append(os.path.abspath("."))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from sheets_handler import fetch_psb_data

def main():
    print("Testing fetch_psb_data...")
    res = fetch_psb_data()
    print("--- RESULT ---")
    print(res)
    print("--------------")

if __name__ == "__main__":
    main()
