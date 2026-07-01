import sys
import os
sys.path.append(os.path.abspath("."))

# Reconfigure stdout to use UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import telebot
from google import genai
from config import BOT_TOKEN, GEMINI_KEY
from sheets_handler import fetch_open_tickets_alert

# Mengambil GROUP_ID_STA dari env
group_id_sta_env = os.getenv("GROUP_ID_STA")
if not group_id_sta_env:
    print("❌ ERROR: GROUP_ID_STA tidak ditemukan di file .env!")
    sys.exit(1)

GROUP_ID_STA = int(group_id_sta_env)

client = None
MODEL_ID = "gemini-3.5-flash"
if GEMINI_KEY:
    try:
        client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        print(f"Gagal inisialisasi Gemini: {e}")

bot = telebot.TeleBot(BOT_TOKEN)

print(f"Mengirim hasil cek open TIKET URGENT STA ke Group ID STA: {GROUP_ID_STA}...")
try:
    report = fetch_open_tickets_alert(client, MODEL_ID, sheet_name="TIKET URGENT STA")
    print("\n--- ISI LAPORAN ---")
    print(report)
    print("-------------------\n")
    bot.send_message(GROUP_ID_STA, report, parse_mode="MarkdownV2")
    print("✅ Berhasil terkirim ke grup STA!")
except Exception as e:
    print(f"❌ Gagal mengirim ke grup STA: {e}")
