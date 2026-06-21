import time
import threading
import logging
import telebot
from google import genai

from config import BOT_TOKEN, GEMINI_KEY, GROUP_ID
from sheets_handler import perform_auto_assign, fetch_actcomp_data, fetch_rekap_data

# Inisialisasi Client Gemini API
client = None
MODEL_ID = "gemini-3.5-flash"
if GEMINI_KEY:
    try:
        client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        logging.error(f"Gagal inisialisasi Gemini API: {e}")

# Inisialisasi Bot Telegram
if not BOT_TOKEN:
    logging.critical("BOT_TOKEN tidak ditemukan di file .env! Bot tidak dapat berjalan.")
    raise ValueError("BOT_TOKEN tidak boleh kosong.")

bot = telebot.TeleBot(BOT_TOKEN)

# Mengatur daftar menu perintah di pojok kiri bawah Telegram
try:
    bot.set_my_commands([
        telebot.types.BotCommand("start", "Mulai bot & Tampilkan menu utama"),
        telebot.types.BotCommand("rekap", "Melihat rekap produktivitas berkala"),
        telebot.types.BotCommand("cek_actcomp", "Memeriksa status ACTCOMP / BAI pending"),
        telebot.types.BotCommand("cek_assign", "Memeriksa dan memproses antrean auto-assign WO"),
        telebot.types.BotCommand("id", "Melihat ID chat saat ini")
    ])
except Exception as e:
    logging.error(f"Gagal mengatur perintah bot: {e}")

# Helper untuk membuat keyboard menu utama
def get_main_menu_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton("📊 Tampilkan Rekap", callback_data="btn_rekap"))
    markup.row(telebot.types.InlineKeyboardButton("🔔 Cek ACTCOMP (Pending BAI)", callback_data="btn_cek_actcomp"))
    markup.row(telebot.types.InlineKeyboardButton("🔍 Jalankan Auto-Assign", callback_data="btn_cek_assign"))
    markup.row(telebot.types.InlineKeyboardButton("🆔 Cek ID Chat", callback_data="btn_id"))
    return markup

# ==================== WORKERS BACKGROUND ====================

def auto_assign_worker():
    while True:
        try:
            # Berjalan otomatis setiap jam 08:00 sampai 21:00
            if 8 <= time.localtime().tm_hour < 21: 
                perform_auto_assign()
            time.sleep(180) 
        except Exception as e:
            logging.error(f"Worker Assign Error: {e}")
            time.sleep(60)

def auto_report_worker():
    last_rekap, last_actcomp = 0, 0
    while True:
        try:
            now = time.time()
            if 8 <= time.localtime().tm_hour < 23:
                # Hanya mengirim laporan otomatis jika GROUP_ID ditentukan di .env
                if GROUP_ID:
                    if now - last_rekap > 1800:
                        bot.send_message(GROUP_ID, fetch_rekap_data(), parse_mode="MarkdownV2")
                        last_rekap = now
                    if now - last_actcomp > 3600:
                        bot.send_message(GROUP_ID, fetch_actcomp_data(client, MODEL_ID), parse_mode="MarkdownV2")
                        last_actcomp = now
            time.sleep(60)
        except Exception as e:
            logging.error(f"Worker Report Error: {e}")
            time.sleep(60)

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    msg = (
        "👋 *Selamat datang di Bot WOTRAX\\!*\n\n"
        "Silakan pilih menu di bawah ini untuk berinteraksi dengan bot secara langsung:"
    )
    bot.send_message(message.chat.id, msg, parse_mode="MarkdownV2", reply_markup=get_main_menu_keyboard())

@bot.message_handler(commands=['id'])
def handle_id(message):
    chat_id = message.chat.id
    chat_type = message.chat.type
    msg = (
        f"🆔 *Informasi Chat Anda:*\n\n"
        f"• ID Chat: `{chat_id}`\n"
        f"• Tipe Chat: `{chat_type}`\n\n"
        f"Gunakan ID di atas pada file `.env` sebagai `GROUP_ID` jika diperlukan\\."
    )
    bot.reply_to(message, msg, parse_mode="MarkdownV2")

@bot.message_handler(commands=['rekap'])
def handle_rekap(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, fetch_rekap_data(), parse_mode="MarkdownV2")

@bot.message_handler(commands=['cek_actcomp'])
def handle_cek_actcomp(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(message, fetch_actcomp_data(client, MODEL_ID), parse_mode="MarkdownV2")

@bot.message_handler(commands=['cek_assign'])
def handle_cek_assign(message):
    bot.reply_to(message, "🔍 Memeriksa antrean WO...")
    threading.Thread(target=perform_auto_assign).start()

# ==================== CALLBACK QUERY HANDLER ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_queries(call):
    # Menghapus status loading pada tombol setelah diklik
    bot.answer_callback_query(call.id)
    
    if call.data == "btn_rekap":
        bot.send_chat_action(call.message.chat.id, 'typing')
        bot.send_message(call.message.chat.id, fetch_rekap_data(), parse_mode="MarkdownV2")
        
    elif call.data == "btn_cek_actcomp":
        bot.send_chat_action(call.message.chat.id, 'typing')
        bot.send_message(call.message.chat.id, fetch_actcomp_data(client, MODEL_ID), parse_mode="MarkdownV2")
        
    elif call.data == "btn_cek_assign":
        bot.send_message(call.message.chat.id, "🔍 Memeriksa antrean WO...")
        threading.Thread(target=perform_auto_assign).start()
        
    elif call.data == "btn_id":
        chat_id = call.message.chat.id
        chat_type = call.message.chat.type
        msg = (
            f"🆔 *Informasi Chat Anda:*\n\n"
            f"• ID Chat: `{chat_id}`\n"
            f"• Tipe Chat: `{chat_type}`\n\n"
            f"Gunakan ID di atas pada file `.env` sebagai `GROUP_ID` jika diperlukan\\."
        )
        bot.send_message(call.message.chat.id, msg, parse_mode="MarkdownV2")

# ==================== MAIN PROGRAM ====================

if __name__ == "__main__":
    logging.info("🚀 Bot WOTRAX Activated & Running...")
    
    # Jalankan worker background di thread terpisah
    threading.Thread(target=auto_assign_worker, daemon=True).start()
    threading.Thread(target=auto_report_worker, daemon=True).start()
    
    # Mulai bot polling
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
