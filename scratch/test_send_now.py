import sys
import os
sys.path.append(os.path.abspath("."))

# Reconfigure stdout to use UTF-8 encoding to support emojis in Windows Terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import telebot
from google import genai
from config import BOT_TOKEN, GEMINI_KEY
from sheets_handler import fetch_open_tickets_alert

# Mengambil GROUP_ID dari env, jika kosong gunakan default grup -4666727876
group_id_env = os.getenv("GROUP_ID")
if not group_id_env:
    group_id_env = "-4666727876"
GROUP_ID = int(group_id_env)

client = None
MODEL_ID = "gemini-3.5-flash"
if GEMINI_KEY:
    try:
        client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        print(f"Gagal inisialisasi Gemini: {e}")

bot = telebot.TeleBot(BOT_TOKEN)

print(f"Mengirim hasil cek open TIKET URGENT MPW ke Group ID: {GROUP_ID}...")
try:
    report = fetch_open_tickets_alert(client, MODEL_ID, sheet_name="TIKET URGENT MPW")
    print("\n--- ISI LAPORAN ---")
    print(report)
    print("-------------------\n")
    bot.send_message(GROUP_ID, report, parse_mode="MarkdownV2")
    print("✅ Berhasil terkirim ke grup!")
except Exception as e:
    print(f"❌ Gagal mengirim ke grup: {e}")
