import logging
import random
# pyrefly: ignore [missing-import]
import telebot
# pyrefly: ignore [missing-import]
from google import genai
import threading
import time
from datetime import datetime, timezone, timedelta

from config import BOT_TOKEN, GEMINI_KEY, GROUP_ID, GROUP_ID_STA, GROUP_ID_ABSEN, GROUP_ID_ABSEN_PROV, TECH_TEAMS, PROV_TEAMS
from sheets_handler import fetch_open_tickets_alert, fetch_rekap_data, fetch_psb_data, get_open_tickets_data

# Daftar pesan penolakan kocak untuk non-admin
FUNNY_REJECTIONS = [
    "*KAMU SIAPA SURUH SAYA???*",
    "*Eits, tidak semudah itu Ferguso\\! Hanya admin yang bisa\\.*",
    "*Ndak bisa, ndak bisa\\. Kamu bukan admin\\!*",
    "*Siapa lu? Kenal juga nggak, main perintah aja\\!*",
    "*Waduh, minimal admin dulu baru boleh perintah\\-perintah\\.*",
    "*Hayo, mau ngapain? Kamu bukan admin ya\\!*",
    "*Akses ditolak\\! Coba rayu admin dulu sana\\.*",
    "*Ngimpi apa semalam kok berani perintah saya? Kamu kan bukan admin\\!*"
]

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
        telebot.types.BotCommand("absen", "Mengirimkan pengingat absen TIM Assurance & TIM Provisioning"),
        telebot.types.BotCommand("id", "Melihat ID chat saat ini")
    ])
    
    # Hapus command list (menu perintah) di grup absen agar tidak membingungkan anggota grup
    if GROUP_ID_ABSEN:
        try:
            bot.set_my_commands([], scope=telebot.types.BotCommandScopeChat(chat_id=GROUP_ID_ABSEN))
            logging.info(f"Command menu untuk GROUP_ID_ABSEN ({GROUP_ID_ABSEN}) berhasil dihapus.")
        except Exception as e:
            logging.warning(f"Gagal menghapus command menu di GROUP_ID_ABSEN: {e}")
            
    if GROUP_ID_ABSEN_PROV:
        try:
            bot.set_my_commands([], scope=telebot.types.BotCommandScopeChat(chat_id=GROUP_ID_ABSEN_PROV))
            logging.info(f"Command menu untuk GROUP_ID_ABSEN_PROV ({GROUP_ID_ABSEN_PROV}) berhasil dihapus.")
        except Exception as e:
            logging.warning(f"Gagal menghapus command menu di GROUP_ID_ABSEN_PROV: {e}")
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
    markup.row(
        telebot.types.InlineKeyboardButton("🔔 Kirim Pengingat Absen", callback_data="btn_absen")
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

def get_attendance_reminder_text(type_absen="pagi", team_type="assurance"):
    # Kumpulkan semua tag teknisi berdasarkan team_type
    tags_list = []
    if team_type == "provisioning":
        source_teams = PROV_TEAMS
        team_display = "TIM PROVISIONING"
    else:
        source_teams = TECH_TEAMS
        team_display = "TIM ASSURANCE"
        
    for team in source_teams:
        if team.get("tags"):
            # Escape underscore agar kompatibel dengan MarkdownV2
            escaped_tag = team["tags"].replace('_', r'\_')
            tags_list.append(escaped_tag)
    
    tags_str = " ".join(tags_list)
    
    if type_absen == "pagi":
        header = f"🚨 *PENGINGAT ABSEN PAGI / MASUK \\- {team_display}* 🚨"
        body = f"Selamat pagi rekan\\-rekan {team_display}\\! Dimohon untuk segera melakukan absensi masuk pagi ini sebelum jam 07\\.00 WIB ya\\."
    elif type_absen == "malam":
        header = f"🚨 *PENGINGAT ABSEN BESOK SEBELUM JAM 07.00 WIB \\- {team_display}* 🚨"
        body = f"Selamat malam rekan\\-rekan {team_display}\\! Jangan lupa untuk melakukan absensi masuk besok pagi sebelum jam 07\\.00 WIB ya\\."
    else:
        header = f"🚨 *PENGINGAT ABSENSI \\- {team_display}* 🚨"
        body = f"Halo rekan\\-rekan {team_display}, dimohon untuk segera melakukan absensi ya\\!"
        
    msg = (
        f"{header}\n\n"
        f"{body}\n\n"
        f"{tags_str}"
    )
    return msg

def send_attendance_reminder(chat_id_to_notify=None, type_absen="pagi", team_type="assurance"):
    # Pilih target chat ID default
    if chat_id_to_notify is not None:
        target_chat_id = chat_id_to_notify
    else:
        if team_type == "provisioning":
            target_chat_id = GROUP_ID_ABSEN_PROV if GROUP_ID_ABSEN_PROV else GROUP_ID_ABSEN
        else:
            target_chat_id = GROUP_ID_ABSEN
            
    if not target_chat_id:
        if team_type == "provisioning":
            team_display = "TIM PROVISIONING"
        else:
            team_display = "TIM ASSURANCE"
        raise ValueError(f"Target Chat ID tidak ditentukan dan GROUP_ID_ABSEN untuk {team_display} tidak dikonfigurasi.")
        
    msg = get_attendance_reminder_text(type_absen, team_type)
    return safe_send_message(target_chat_id, msg, parse_mode="MarkdownV2")

def send_combined_attendance_reminder(chat_id_to_notify=None, type_absen="pagi", team_types=["assurance", "provisioning"]):
    # Tentukan target chat ID
    if chat_id_to_notify is not None:
        target_chat_id = chat_id_to_notify
    else:
        target_chat_id = GROUP_ID_ABSEN
        
    if not target_chat_id:
        raise ValueError("Target Chat ID tidak ditentukan untuk pengiriman gabungan.")
        
    msgs = []
    for team_type in team_types:
        msgs.append(get_attendance_reminder_text(type_absen, team_type))
        
    combined_msg = "\n\n\n".join(msgs)
    return safe_send_message(target_chat_id, combined_msg, parse_mode="MarkdownV2")

def send_all_attendance_reminders(chat_id_to_notify=None, type_absen="pagi"):
    # Tentukan target untuk masing-masing
    if chat_id_to_notify is not None:
        target_assurance = chat_id_to_notify
        target_provisioning = chat_id_to_notify
    else:
        target_assurance = GROUP_ID_ABSEN
        target_provisioning = GROUP_ID_ABSEN_PROV if GROUP_ID_ABSEN_PROV else GROUP_ID_ABSEN
        
    if target_assurance == target_provisioning:
        # Jika targetnya sama, kirim 1 pesan gabungan
        if target_assurance:
            return send_combined_attendance_reminder(target_assurance, type_absen, ["assurance", "provisioning"])
        else:
            raise ValueError("Target Chat ID tidak ditentukan.")
    else:
        # Jika targetnya berbeda, kirim ke masing-masing grup secara terpisah
        res_assurance = None
        res_provisioning = None
        if target_assurance:
            res_assurance = send_attendance_reminder(target_assurance, type_absen, "assurance")
        if target_provisioning:
            res_provisioning = send_attendance_reminder(target_provisioning, type_absen, "provisioning")
        return res_assurance or res_provisioning

def check_user_permission(chat_id, user_id, user_is_bot=False):
    """
    Memeriksa apakah user memiliki hak akses (admin/creator/bot)
    untuk menjalankan perintah absen.
    """
    if user_is_bot:
        return True
    if not user_id:
        return False

    # Jika di dalam grup/supergrup, cek status admin di grup tersebut
    if str(chat_id).startswith('-'):
        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status in ['creator', 'administrator']:
                return True
        except Exception as e:
            logging.error(f"Gagal mengecek status admin di grup {chat_id}: {e}")
            return False
        return False
    else:
        # Jika di private chat, cek status admin di GROUP_ID_ABSEN atau GROUP_ID_ABSEN_PROV (jika dikonfigurasi)
        allowed = False
        checked_any = False
        
        if GROUP_ID_ABSEN:
            checked_any = True
            try:
                member = bot.get_chat_member(GROUP_ID_ABSEN, user_id)
                if member.status in ['creator', 'administrator']:
                    allowed = True
            except Exception as e:
                logging.error(f"Gagal mengecek status admin di GROUP_ID_ABSEN ({GROUP_ID_ABSEN}): {e}")
                
        if not allowed and GROUP_ID_ABSEN_PROV:
            checked_any = True
            try:
                member = bot.get_chat_member(GROUP_ID_ABSEN_PROV, user_id)
                if member.status in ['creator', 'administrator']:
                    allowed = True
            except Exception as e:
                logging.error(f"Gagal mengecek status admin di GROUP_ID_ABSEN_PROV ({GROUP_ID_ABSEN_PROV}): {e}")
                
        if not checked_any:
            # Jika tidak ada grup absen yang dikonfigurasi, izinkan akses di private chat
            return True
            
        return allowed

# ==================== COMMAND HANDLERS ====================

# Handler untuk mengabaikan dan menghapus pesan command yang dikirimkan di grup absen
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/') and 
                    (message.chat.id == GROUP_ID_ABSEN or (GROUP_ID_ABSEN_PROV and message.chat.id == GROUP_ID_ABSEN_PROV)))
def handle_absen_group_commands(message):
    logging.info(f"Mengabaikan command '{message.text}' dari chat {message.chat.id} (grup absen)")
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        logging.warning(f"Gagal menghapus pesan command di grup absen: {e}")
    return

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

@bot.message_handler(commands=['absen'])
def handle_absen(message):
    user_id = message.from_user.id if message.from_user else None
    user_is_bot = message.from_user.is_bot if message.from_user else False
    
    if not check_user_permission(message.chat.id, user_id, user_is_bot):
        safe_reply_to(message, random.choice(FUNNY_REJECTIONS))
        return

    bot.send_chat_action(message.chat.id, 'typing')
    
    # Parse parameter pagi/malam jika ada
    parts = message.text.strip().split()
    type_absen = None
    if len(parts) > 1:
        param = parts[1].lower()
        if param in ["pagi", "malam"]:
            type_absen = param
            
    if not type_absen:
        # Default berdasarkan jam saat ini (WIB)
        tz_wib = timezone(timedelta(hours=7))
        now = datetime.now(tz_wib)
        type_absen = "pagi" if now.hour < 12 else "malam"
        
    try:
        chat_id_target = None if GROUP_ID_ABSEN else message.chat.id
        send_all_attendance_reminders(chat_id_to_notify=chat_id_target, type_absen=type_absen)
            
        # Beri laporan status sukses ke pengirim perintah
        safe_reply_to(message, f"✅ *Pesan pengingat absen {type_absen} untuk TIM Assurance & TIM Provisioning berhasil dikirim\\!*")
    except Exception as e:
        logging.error(f"Gagal mengirim pengingat absen gabungan: {e}")
        safe_reply_to(message, f"❌ *Gagal mengirim pengingat absen:* {str(e)}")

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

    elif call.data == "btn_absen":
        user_id = call.from_user.id if call.from_user else None
        user_is_bot = call.from_user.is_bot if call.from_user else False
        
        if not check_user_permission(call.message.chat.id, user_id, user_is_bot):
            first_name = call.from_user.first_name if call.from_user else "Pengguna"
            safe_send_message(call.message.chat.id, f"❌ *{first_name}*, Anda tidak memiliki akses untuk menggunakan tombol ini\\! Hanya Admin yang diizinkan\\.")
            return

        bot.send_chat_action(call.message.chat.id, 'typing')
        # Default berdasarkan jam saat ini (WIB)
        tz_wib = timezone(timedelta(hours=7))
        now = datetime.now(tz_wib)
        type_absen = "pagi" if now.hour < 12 else "malam"
        try:
            chat_id_target = None if GROUP_ID_ABSEN else call.message.chat.id
            send_all_attendance_reminders(chat_id_to_notify=chat_id_target, type_absen=type_absen)
                
            safe_send_message(call.message.chat.id, f"✅ *Pesan pengingat absen {type_absen} untuk TIM Assurance & TIM Provisioning berhasil dikirim\\!*")
        except Exception as e:
            logging.error(f"Gagal mengirim pengingat absen via button: {e}")
            safe_send_message(call.message.chat.id, f"❌ *Gagal mengirim pengingat absen:* {str(e)}")

def run_scheduler():
    logging.info("Background scheduler thread started...")
    last_rekap_time_mpw = None
    last_rekap_time_sta = None
    first_run_mpw = True
    first_run_sta = True
    last_absen_pagi_date = None
    last_absen_sore_date = None
    last_absen_pagi_prov_date = None
    last_absen_sore_prov_date = None
    
    while True:
        try:
            # Dapatkan waktu saat ini di WIB (UTC+7)
            tz_wib = timezone(timedelta(hours=7))
            now = datetime.now(tz_wib)
            today_str = now.strftime('%Y-%m-%d')
            
            current_hour = now.hour
            current_minute = now.minute
            
            # Rentang waktu operasional (09:00 - 19:00 WIB)
            if 9 <= current_hour <= 19:
                
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

            # --- JADWAL PENGINGAT ABSEN OTOMATIS (Di luar batas jam operasional tiket) ---
            # 1. Absen Pagi (06:00 WIB)
            if current_hour == 6 and 0 <= current_minute < 30:
                need_assurance = bool(GROUP_ID_ABSEN and last_absen_pagi_date != today_str)
                target_group_prov = GROUP_ID_ABSEN_PROV if GROUP_ID_ABSEN_PROV else GROUP_ID_ABSEN
                need_provisioning = bool(target_group_prov and last_absen_pagi_prov_date != today_str)
                
                if need_assurance or need_provisioning:
                    try:
                        if need_assurance and need_provisioning and GROUP_ID_ABSEN == target_group_prov:
                            logging.info("Mengirim pengingat absen pagi terjadwal gabungan...")
                            send_combined_attendance_reminder(GROUP_ID_ABSEN, type_absen="pagi", team_types=["assurance", "provisioning"])
                            last_absen_pagi_date = today_str
                            last_absen_pagi_prov_date = today_str
                        else:
                            if need_assurance:
                                logging.info("Mengirim pengingat absen pagi terjadwal (Assurance)...")
                                send_attendance_reminder(GROUP_ID_ABSEN, type_absen="pagi", team_type="assurance")
                                last_absen_pagi_date = today_str
                            if need_provisioning:
                                logging.info("Mengirim pengingat absen pagi terjadwal (Provisioning)...")
                                send_attendance_reminder(target_group_prov, type_absen="pagi", team_type="provisioning")
                                last_absen_pagi_prov_date = today_str
                    except Exception as e:
                        logging.error(f"Gagal mengirim pengingat absen pagi terjadwal: {e}")
            
            # 2. Absen Malam / Besok (23:00 WIB)
            if current_hour == 23 and 0 <= current_minute < 30:
                need_assurance = bool(GROUP_ID_ABSEN and last_absen_sore_date != today_str)
                target_group_prov = GROUP_ID_ABSEN_PROV if GROUP_ID_ABSEN_PROV else GROUP_ID_ABSEN
                need_provisioning = bool(target_group_prov and last_absen_sore_prov_date != today_str)
                
                if need_assurance or need_provisioning:
                    try:
                        if need_assurance and need_provisioning and GROUP_ID_ABSEN == target_group_prov:
                            logging.info("Mengirim pengingat absen malam terjadwal gabungan...")
                            send_combined_attendance_reminder(GROUP_ID_ABSEN, type_absen="malam", team_types=["assurance", "provisioning"])
                            last_absen_sore_date = today_str
                            last_absen_sore_prov_date = today_str
                        else:
                            if need_assurance:
                                logging.info("Mengirim pengingat absen malam terjadwal (Assurance)...")
                                send_attendance_reminder(GROUP_ID_ABSEN, type_absen="malam", team_type="assurance")
                                last_absen_sore_date = today_str
                            if need_provisioning:
                                logging.info("Mengirim pengingat absen malam terjadwal (Provisioning)...")
                                send_attendance_reminder(target_group_prov, type_absen="malam", team_type="provisioning")
                                last_absen_sore_prov_date = today_str
                    except Exception as e:
                        logging.error(f"Gagal mengirim pengingat absen malam terjadwal: {e}")
                    
        except Exception as e:
            logging.error(f"Error pada background scheduler: {e}")
            
        time.sleep(30) # Cek setiap 30 detik


# ==================== MAIN PROGRAM ====================

if __name__ == "__main__":
    logging.info("🚀 Bot Monitoring Gangguan Mempawah Activated & Running...")
    
    # Jalankan background scheduler jika ada GROUP_ID yang tersedia
    if GROUP_ID or GROUP_ID_STA or GROUP_ID_ABSEN or GROUP_ID_ABSEN_PROV:
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logging.info("Scheduler thread launched successfully.")
    else:
        logging.warning("Tidak ada GROUP_ID yang dikonfigurasi di .env. Fitur kirim terjadwal dinonaktifkan.")
        
    # Mulai bot polling
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
