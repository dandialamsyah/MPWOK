import logging
# pyrefly: ignore [missing-import]
import telebot
# pyrefly: ignore [missing-import]
from google import genai
import threading
import time
from datetime import datetime, timezone, timedelta

from config import BOT_TOKEN, GEMINI_KEY, GROUP_ID, GROUP_ID_STA
from sheets_handler import fetch_open_tickets_alert, fetch_rekap_data, fetch_psb_data, get_open_tickets_data

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
        telebot.types.BotCommand("rekap", "Melihat rekap gangguan berkala"),
        telebot.types.BotCommand("cek_open", "Memeriksa gangguan yang masih OPEN"),
        telebot.types.BotCommand("rekap_sta", "Melihat rekap gangguan STA berkala"),
        telebot.types.BotCommand("cek_open_sta", "Memeriksa gangguan STA yang masih OPEN"),
        telebot.types.BotCommand("rekap_unspacsta", "Melihat rekap gangguan UNSPEC STA berkala"),
        telebot.types.BotCommand("unspacsta", "Memeriksa gangguan UNSPEC STA yang masih OPEN"),
        telebot.types.BotCommand("rekap_urgent", "Melihat rekap gangguan URGENT berkala"),
        telebot.types.BotCommand("urgent", "Memeriksa gangguan URGENT yang masih OPEN"),
        telebot.types.BotCommand("urgentsta", "Memeriksa gangguan URGENT STA yang masih OPEN"),
        telebot.types.BotCommand("psb", "Melihat rekap data PSB berkala"),
        telebot.types.BotCommand("id", "Melihat ID chat saat ini")
    ])
except Exception as e:
    logging.error(f"Gagal mengatur perintah bot: {e}")

# Helper untuk membuat keyboard menu utama
def get_main_menu_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("📊 Rekap MPW", callback_data="btn_rekap"),
        telebot.types.InlineKeyboardButton("🔔 Cek Open MPW", callback_data="btn_cek_open")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("📊 Rekap STA", callback_data="btn_rekap_sta"),
        telebot.types.InlineKeyboardButton("🔔 Cek Open STA", callback_data="btn_cek_open_sta")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("📊 Rekap Unspac STA", callback_data="btn_rekap_unspacsta"),
        telebot.types.InlineKeyboardButton("🔔 Cek Open Unspac STA", callback_data="btn_cek_open_unspacsta")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🚨 Rekap Urgent", callback_data="btn_rekap_urgent"),
        telebot.types.InlineKeyboardButton("🚨 Cek Open Urgent", callback_data="btn_cek_open_urgent")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("📊 Rekap PSB", callback_data="btn_rekap_psb"),
        telebot.types.InlineKeyboardButton("🆔 Cek ID Chat", callback_data="btn_id")
    )
    return markup



# Helper untuk mengirim pesan dengan aman menggunakan fallback jika parse_mode gagal
def safe_reply_to(message, text, parse_mode="MarkdownV2", reply_markup=None):
    try:
        return bot.reply_to(message, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "can't parse entities" in str(e) and parse_mode == "MarkdownV2":
            logging.warning(f"Gagal kirim MarkdownV2, mencoba fallback ke Plaintext: {e}")
            # Hapus backslash escape MarkdownV2 untuk pengiriman plaintext
            plain = text.replace(r'\.', '.').replace(r'\-', '-').replace(r'\_', '_').replace(r'\+', '+').replace(r'\!', '!').replace(r'\(', '(').replace(r'\)', ')').replace(r'\[', '[').replace(r'\]', ']').replace(r'\=', '=')
            plain = plain.replace('*', '').replace('`', '')
            try:
                return bot.reply_to(message, plain, reply_markup=reply_markup)
            except Exception as ex:
                logging.error(f"Gagal kirim fallback: {ex}")
                raise ex
        else:
            logging.error(f"Gagal kirim reply_to: {e}")
            raise e

def safe_send_message(chat_id, text, parse_mode="MarkdownV2", reply_markup=None):
    try:
        return bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "can't parse entities" in str(e) and parse_mode == "MarkdownV2":
            logging.warning(f"Gagal kirim MarkdownV2, mencoba fallback ke Plaintext: {e}")
            plain = text.replace(r'\.', '.').replace(r'\-', '-').replace(r'\_', '_').replace(r'\+', '+').replace(r'\!', '!').replace(r'\(', '(').replace(r'\)', ')').replace(r'\[', '[').replace(r'\]', ']').replace(r'\=', '=')
            plain = plain.replace('*', '').replace('`', '')
            try:
                return bot.send_message(chat_id, plain, reply_markup=reply_markup)
            except Exception as ex:
                logging.error(f"Gagal kirim fallback: {ex}")
                raise ex
        else:
            logging.error(f"Gagal kirim send_message: {e}")
            raise e

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    msg = (
        "👋 *Selamat datang di Bot Monitoring Gangguan Mempawah\\!*\n\n"
        "Silakan pilih menu di bawah ini untuk berinteraksi dengan bot secara langsung:"
    )
    safe_send_message(message.chat.id, msg, parse_mode="MarkdownV2", reply_markup=get_main_menu_keyboard())

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
    safe_reply_to(message, msg, parse_mode="MarkdownV2")

@bot.message_handler(commands=['rekap'])
def handle_rekap(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_rekap_data(), parse_mode="MarkdownV2")

@bot.message_handler(commands=['rekap_sta'])
def handle_rekap_sta(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_rekap_data(sheet_name="sta"), parse_mode="MarkdownV2")

@bot.message_handler(commands=['cek_open'])
def handle_cek_open(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_open_tickets_alert(client, MODEL_ID), parse_mode="MarkdownV2")

@bot.message_handler(commands=['cek_open_sta'])
def handle_cek_open_sta(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_open_tickets_alert(client, MODEL_ID, sheet_name="sta"), parse_mode="MarkdownV2")

@bot.message_handler(commands=['rekap_unspacsta'])
def handle_rekap_unspacsta(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_rekap_data(sheet_name="UNDSEPC STA"), parse_mode="MarkdownV2")

@bot.message_handler(commands=['unspacsta'])
def handle_unspacsta(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_open_tickets_alert(client, MODEL_ID, sheet_name="UNDSEPC STA"), parse_mode="MarkdownV2")

@bot.message_handler(commands=['PSB', 'psb'])
def handle_psb(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_psb_data(), parse_mode="MarkdownV2")

@bot.message_handler(commands=['urgent'])
def handle_urgent(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_open_tickets_alert(client, MODEL_ID, sheet_name="TIKET URGENT MPW"), parse_mode="MarkdownV2")

@bot.message_handler(commands=['rekap_urgent'])
def handle_rekap_urgent(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_rekap_data(sheet_name="TIKET URGENT MPW"), parse_mode="MarkdownV2")

@bot.message_handler(commands=['urgentsta'])
def handle_urgentsta(message):
    bot.send_chat_action(message.chat.id, 'typing')
    safe_reply_to(message, fetch_open_tickets_alert(client, MODEL_ID, sheet_name="TIKET URGENT STA"), parse_mode="MarkdownV2")

# ==================== CALLBACK QUERY HANDLER ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_queries(call):
    # Menghapus status loading pada tombol setelah diklik
    bot.answer_callback_query(call.id)
    
    if call.data == "btn_rekap":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_rekap_data(), parse_mode="MarkdownV2")
        
    elif call.data == "btn_rekap_sta":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_rekap_data(sheet_name="sta"), parse_mode="MarkdownV2")
        
    elif call.data == "btn_rekap_unspacsta":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_rekap_data(sheet_name="UNDSEPC STA"), parse_mode="MarkdownV2")
        
    elif call.data == "btn_rekap_psb":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_psb_data(), parse_mode="MarkdownV2")
        
    elif call.data == "btn_rekap_urgent":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_rekap_data(sheet_name="TIKET URGENT MPW"), parse_mode="MarkdownV2")
        
    elif call.data == "btn_cek_open":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_open_tickets_alert(client, MODEL_ID), parse_mode="MarkdownV2")
        
    elif call.data == "btn_cek_open_sta":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_open_tickets_alert(client, MODEL_ID, sheet_name="sta"), parse_mode="MarkdownV2")
        
    elif call.data == "btn_cek_open_unspacsta":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_open_tickets_alert(client, MODEL_ID, sheet_name="UNDSEPC STA"), parse_mode="MarkdownV2")
        
    elif call.data == "btn_cek_open_urgent":
        bot.send_chat_action(call.message.chat.id, 'typing')
        safe_send_message(call.message.chat.id, fetch_open_tickets_alert(client, MODEL_ID, sheet_name="TIKET URGENT MPW"), parse_mode="MarkdownV2")
        
    elif call.data == "btn_id":
        chat_id = call.message.chat.id
        chat_type = call.message.chat.type
        msg = (
            f"🆔 *Informasi Chat Anda:*\n\n"
            f"• ID Chat: `{chat_id}`\n"
            f"• Tipe Chat: `{chat_type}`\n\n"
            f"Gunakan ID di atas pada file `.env` sebagai `GROUP_ID` jika diperlukan\\."
        )
        safe_send_message(call.message.chat.id, msg, parse_mode="MarkdownV2")

def run_scheduler():
    logging.info("Background scheduler thread started...")
    last_rekap_time_mpw = None
    last_rekap_time_sta = None
    first_run_mpw = True
    first_run_sta = True
    
    while True:
        try:
            # Dapatkan waktu saat ini di WIB (UTC+7)
            tz_wib = timezone(timedelta(hours=7))
            now = datetime.now(tz_wib)
            
            current_hour = now.hour
            
            # Rentang waktu operasional (06:00 - 19:00 WIB)
            if 6 <= current_hour <= 19:
                
                # --- JADWAL REKAP BERKALA TIMING MPW (Setiap 60 menit) ---
                if first_run_mpw:
                    first_run_mpw = False
                    logging.info("Menjalankan pengiriman pertama MPW saat startup...")
                    if GROUP_ID:
                        try:
                            open_tickets = get_open_tickets_data(sheet_name="TIKET URGENT MPW")
                            if open_tickets:
                                logging.info(f"Mengirim laporan startup {len(open_tickets)} tiket urgent open ke grup MPW...")
                                report = fetch_open_tickets_alert(client, MODEL_ID, sheet_name="TIKET URGENT MPW", tickets=open_tickets)
                                safe_send_message(GROUP_ID, report, parse_mode="MarkdownV2")
                            else:
                                logging.info("Tidak ada tiket urgent MPW open saat startup.")
                        except Exception as e:
                            logging.error(f"Gagal mengirim rekap startup MPW: {e}")
                    last_rekap_time_mpw = now
                    
                elif last_rekap_time_mpw is None or (now - last_rekap_time_mpw) >= timedelta(minutes=60):
                    logging.info(f"Waktu penjadwalan berkala MPW (1 jam) tercapai: {now.strftime('%H:%M')} WIB.")
                    if GROUP_ID:
                        try:
                            open_tickets = get_open_tickets_data(sheet_name="TIKET URGENT MPW")
                            if open_tickets:
                                logging.info(f"Mengirim rekap berkala {len(open_tickets)} tiket urgent open ke grup MPW...")
                                report = fetch_open_tickets_alert(client, MODEL_ID, sheet_name="TIKET URGENT MPW", tickets=open_tickets)
                                safe_send_message(GROUP_ID, report, parse_mode="MarkdownV2")
                            else:
                                logging.info("Tidak ada tiket urgent MPW open, pengiriman berkala dilewati.")
                        except Exception as e:
                            logging.error(f"Gagal mengirim rekap berkala MPW: {e}")
                    last_rekap_time_mpw = now
                
                # --- JADWAL REKAP BERKALA TIMING STA (Setiap 60 menit, beda 5 menit dengan MPW) ---
                if first_run_sta:
                    first_run_sta = False
                    logging.info("Menjadwalkan pengiriman pertama STA 5 menit setelah startup...")
                    last_rekap_time_sta = now - timedelta(minutes=55) # offset agar run berikutnya tepat 5 menit lagi
                
                elif last_rekap_time_sta is None or (now - last_rekap_time_sta) >= timedelta(minutes=60):
                    logging.info(f"Waktu penjadwalan berkala STA (1 jam) tercapai: {now.strftime('%H:%M')} WIB.")
                    if GROUP_ID_STA:
                        try:
                            open_tickets_sta = get_open_tickets_data(sheet_name="TIKET URGENT STA")
                            if open_tickets_sta:
                                logging.info(f"Mengirim rekap berkala {len(open_tickets_sta)} tiket urgent open ke grup STA...")
                                report_sta = fetch_open_tickets_alert(client, MODEL_ID, sheet_name="TIKET URGENT STA", tickets=open_tickets_sta)
                                safe_send_message(GROUP_ID_STA, report_sta, parse_mode="MarkdownV2")
                            else:
                                logging.info("Tidak ada tiket urgent STA open, pengiriman berkala dilewati.")
                        except Exception as e:
                            logging.error(f"Gagal mengirim rekap berkala STA: {e}")
                    last_rekap_time_sta = now
                    
            else:
                # Di luar jam operasional, reset agar langsung mengirim rekap saat masuk jam operasional
                if not first_run_mpw or not first_run_sta:
                    logging.info("Di luar jam operasional. Resetting scheduler flags.")
                    first_run_mpw = True
                    first_run_sta = True
                    last_rekap_time_mpw = None
                    last_rekap_time_sta = None
                    
        except Exception as e:
            logging.error(f"Error pada background scheduler: {e}")
            
        time.sleep(30) # Cek setiap 30 detik


# ==================== MAIN PROGRAM ====================

if __name__ == "__main__":
    logging.info("🚀 Bot Monitoring Gangguan Mempawah Activated & Running...")
    
    # Jalankan background scheduler jika GROUP_ID atau GROUP_ID_STA tersedia
    if GROUP_ID or GROUP_ID_STA:
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logging.info("Scheduler thread for urgent tickets launched successfully.")
    else:
        logging.warning("GROUP_ID dan GROUP_ID_STA tidak terdeteksi di .env. Fitur kirim terjadwal urgent dinonaktifkan.")
        
    # Mulai bot polling
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
