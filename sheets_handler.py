import re
import os
import json
import logging
# pyrefly: ignore [missing-import]
import gspread
from gspread import Cell
from google.oauth2.service_account import Credentials
from telebot.formatting import escape_markdown

from config import (
    SHEET_NAME,
    KATEGORI_CLOSED,
    KATEGORI_OPEN,
    TECH_TEAMS,
    TEAM_LIST,
    TEKNISI_LIBUR
)

import time

# Setup Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
ws_cache = {}

def get_worksheet(sheet_name=None):
    global ws_cache
    cache_key = sheet_name or "default"
    if ws_cache.get(cache_key) is not None:
        return ws_cache[cache_key]
    try:
        logging.info(f"Mencoba menghubungkan kembali ke Google Sheets ({cache_key})...")
        google_creds_json = os.getenv("GOOGLE_CREDENTIALS")
        if google_creds_json:
            info = json.loads(google_creds_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPE)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
        gc = gspread.authorize(creds)
        sh = gc.open(SHEET_NAME)
        if sheet_name:
            ws = sh.worksheet(sheet_name)
        else:
            ws = sh.sheet1
        ws_cache[cache_key] = ws
        return ws
    except Exception as e:
        logging.error(f"Gagal inisialisasi Google Sheets ({cache_key}): {e}")
        ws_cache[cache_key] = None
        return None

# Coba inisialisasi pertama kali saat import
get_worksheet()

# Caching Google Sheets
_cached_rows_dict = {}
_cache_time_dict = {}
CACHE_TTL = 15 # cache duration in seconds

def get_sheet_rows(sheet_name=None):
    global _cached_rows_dict, _cache_time_dict
    current_time = time.time()
    cache_key = sheet_name or "default"
    
    # Gunakan cache jika masih valid
    if cache_key in _cached_rows_dict and (current_time - _cache_time_dict.get(cache_key, 0)) < CACHE_TTL:
        logging.info(f"Menggunakan data Google Sheets ({cache_key}) dari cache.")
        return _cached_rows_dict[cache_key]
        
    ws = get_worksheet(sheet_name)
    if not ws:
        # Fallback ke cache kadaluarsa jika ada
        if cache_key in _cached_rows_dict:
            logging.warning(f"Gagal koneksi Sheets, menggunakan data cache kadaluarsa untuk {cache_key}.")
            return _cached_rows_dict[cache_key]
        raise Exception(f"Gagal terhubung ke Google Sheets ({cache_key}) dan tidak ada data cache.")
        
    try:
        logging.info(f"Mengambil data segar dari Google Sheets ({cache_key})...")
        rows = ws.get_all_values()
        _cached_rows_dict[cache_key] = rows
        _cache_time_dict[cache_key] = current_time
        return rows
    except Exception as e:
        logging.warning(f"Error mengambil data Sheets ({cache_key}): {e}. Mencoba re-inisialisasi...")
        global ws_cache
        if cache_key in ws_cache:
            ws_cache[cache_key] = None # force re-init
        ws = get_worksheet(sheet_name)
        if ws:
            try:
                rows = ws.get_all_values()
                _cached_rows_dict[cache_key] = rows
                _cache_time_dict[cache_key] = current_time
                return rows
            except Exception as retry_e:
                logging.error(f"Gagal coba ulang ambil data Sheets ({cache_key}): {retry_e}")
                
        # Jika re-init gagal, fallback ke cache lama jika ada
        if cache_key in _cached_rows_dict:
            logging.warning(f"Mencoba ulang gagal, menggunakan data cache kadaluarsa untuk {cache_key}.")
            return _cached_rows_dict[cache_key]
        raise e

# Caching Gemini AI Message
_cached_ai_msg = None
_cached_ai_time = 0
AI_CACHE_TTL = 300 # cache duration in seconds (5 minutes)

def get_ai_reminder_message(client, model_id):
    global _cached_ai_msg, _cached_ai_time
    current_time = time.time()
    
    # Gunakan cache jika masih valid
    if _cached_ai_msg is not None and (current_time - _cached_ai_time) < AI_CACHE_TTL:
        logging.info("Menggunakan pesan AI dari cache.")
        return _cached_ai_msg
        
    default_msg = "Ayo teman\\-teman, segera selesaikan tiket gangguan yang masih open ya\\!"
    if not client or not model_id:
        return default_msg
        
    try:
        logging.info("Membuat pesan AI baru via Gemini API...")
        res = client.models.generate_content(
            model=model_id, 
            contents="Berikan satu kalimat singkat, santai namun tetap tegas dalam bahasa Indonesia untuk mengingatkan teknisi agar segera menyelesaikan tiket gangguan (trouble ticket) yang masih OPEN. Maksimal 15 kata. Tanpa markdown."
        )
        raw_msg = res.candidates[0].content.parts[0].text.strip()
        escaped = escape_md(raw_msg)
        _cached_ai_msg = escaped
        _cached_ai_time = current_time
        return escaped
    except Exception as e:
        logging.warning(f"Gagal generate AI message: {e}. Menggunakan default/cache.")
        if _cached_ai_msg is not None:
            return _cached_ai_msg
        return default_msg


def escape_md(text):
    if not text:
        return ""
    return escape_markdown(str(text))

def get_team_tags(name_in_sheet):
    name_upper = str(name_in_sheet).upper().strip()
    if not name_upper or any(x in name_upper for x in ["UNASSIGNED", "BLM ASSIGN"]): 
        return ""
    for team in TECH_TEAMS:
        if any(member in name_upper for member in team["names"]):
            return team["tags"].replace('_', r'\_')
    return f"Teknisi {escape_md(name_in_sheet)}"

def resolve_canonical_team(name_in_sheet):
    name_upper = str(name_in_sheet).upper().strip()
    if not name_upper or any(x in name_upper for x in ["UNASSIGNED", "BLM ASSIGN"]):
        return None
    for i, team in enumerate(TECH_TEAMS):
        if any(member in name_upper for member in team["names"]):
            if i < len(TEAM_LIST):
                return TEAM_LIST[i]
    return name_in_sheet

def get_short_name(full_name):
    name = str(full_name).upper()
    mapping = {
        "ADE": "Ade-Andre", "ASEP": "Asep-Roni", "CHAIRUL": "Chrl-Yuda",
        "DEDI": "Dedi", "DESTA": "Dst-Jefri", "YOGI": "Yogi"
    }
    for key, val in mapping.items():
        if key in name: return val
    return name[:10]

def resolve_headers(header):
    idx_status = -1
    for s_col in ['STATUS', 'STATE']:
        if s_col in header:
            idx_status = header.index(s_col)
            break
            
    idx_team = -1
    for t_col in ['TEAM', 'TEKNISI', 'PETUGAS']:
        if t_col in header:
            idx_team = header.index(t_col)
            break
            
    idx_incident = -1
    for i_col in ['INCIDENT', 'WONUM', 'TICKET ID', 'NO TIKET']:
        if i_col in header:
            idx_incident = header.index(i_col)
            break
            
    idx_device = -1
    for d_col in ['DEVICE NAME', 'ALPRO', 'ODP']:
        if d_col in header:
            idx_device = header.index(d_col)
            break
            
    idx_cust_type = -1
    for c_col in ['CUSTOMER TYPE', 'TIPE PELANGGAN', 'PRIORITAS', 'CLASS']:
        if c_col in header:
            idx_cust_type = header.index(c_col)
            break
            
    return idx_status, idx_team, idx_incident, idx_device, idx_cust_type

def get_priority_rank(cust_type):
    ct = str(cust_type).upper().strip()
    if 'MANJA' in ct:
        return 1
    elif 'REGULER' in ct:
        return 2
    elif 'HVC' in ct or 'GOLD' in ct:
        return 3
    else:
        return 4

def fetch_open_tickets_alert(client=None, model_id=None, sheet_name=None):
    try:
        rows = get_sheet_rows(sheet_name)
        if not rows or len(rows) < 2: return "Data Sheet Kosong"
        
        header = [str(h).upper().strip() for h in rows[0]]
        idx_status, idx_team, idx_incident, idx_device, idx_cust_type = resolve_headers(header)
        
        if idx_status == -1 or idx_team == -1 or idx_incident == -1:
            return r"❌ Struktur kolom Sheet tidak sesuai\. Pastikan terdapat kolom STATUS, TEAM/TEKNISI, dan INCIDENT/WONUM\."
            
        alerts = {}
        for row in rows[1:]:
            if len(row) <= max(idx_status, idx_team, idx_incident):
                continue
            incident = str(row[idx_incident]).strip()
            if not incident:
                continue
            status_raw = str(row[idx_status]).upper().strip()
            team_raw = str(row[idx_team]).strip()
            
            # Jika status tidak closed
            if not any(x in status_raw for x in KATEGORI_CLOSED):
                tags = get_team_tags(team_raw)
                if not tags: continue
                
                device_val = row[idx_device] if idx_device != -1 and len(row) > idx_device else ""
                cust_type = row[idx_cust_type].strip() if idx_cust_type != -1 and len(row) > idx_cust_type else ""
                
                if tags not in alerts: alerts[tags] = []
                alerts[tags].append({
                    'incident': incident,
                    'status': status_raw,
                    'device': device_val,
                    'cust_type': cust_type
                })
                
        if not alerts:
            if sheet_name:
                return f"✅ *Semua tiket gangguan {escape_md(sheet_name)} sudah CLOSED\\!*"
            return "✅ *Semua tiket gangguan sudah CLOSED\\!*"
        
        ai_msg = get_ai_reminder_message(client, model_id)

        prefix = "*(STA)* " if sheet_name else ""
        msg = f"🔔 {prefix}*{ai_msg}*\n\n"
        for tag, tickets in alerts.items():
            # Urutkan berdasarkan prioritas customer type (1. MANJA, 2. REGULER, 3. HVC_GOLD)
            tickets.sort(key=lambda x: get_priority_rank(x['cust_type']))
            
            wos_formatted = []
            for t in tickets:
                device_str = f" \\- {escape_md(t['device'])}" if t['device'] else ""
                type_str = f" \\({escape_md(t['cust_type'])}\\)" if t['cust_type'] else ""
                wos_formatted.append(f"▫️ `{escape_md(t['incident'])}` \\[{escape_md(t['status'])}\\]{type_str}{device_str}")
                
            msg += f"{tag}\n" + "\n".join(wos_formatted) + "\n\n"
        return msg
    except Exception as e:
        return f"❌ *Error Cek Open:* {escape_md(str(e))}"

def fetch_rekap_data(sheet_name=None):
    try:
        rows = get_sheet_rows(sheet_name)
        if not rows or len(rows) < 2: return "Data Sheet Kosong"
        
        header = [str(h).upper().strip() for h in rows[0]]
        idx_status, idx_team, idx_incident, _, idx_cust_type = resolve_headers(header)
        
        if idx_status == -1 or idx_team == -1 or idx_incident == -1:
            return r"❌ Struktur kolom Sheet tidak sesuai\. Pastikan terdapat kolom STATUS, TEAM/TEKNISI, dan INCIDENT/WONUM\."
            
        pivot = {}
        total = {'OPEN': 0, 'CLOSED': 0}
        
        for team in TEAM_LIST:
            pivot[team] = {'OPEN': 0, 'CLOSED': 0}
            
        unmapped_teams = {}
 
        for row in rows[1:]:
            if len(row) <= max(idx_status, idx_team, idx_incident):
                continue
            
            incident = str(row[idx_incident]).strip()
            if not incident:
                continue
                
            status_raw = str(row[idx_status]).upper().strip()
            team_raw = str(row[idx_team]).strip()
            
            is_closed = any(x in status_raw for x in KATEGORI_CLOSED)
            cat = 'CLOSED' if is_closed else 'OPEN'
            
            canonical_team = resolve_canonical_team(team_raw)
            if canonical_team:
                if canonical_team not in pivot:
                    pivot[canonical_team] = {'OPEN': 0, 'CLOSED': 0}
                pivot[canonical_team][cat] += 1
            else:
                if team_raw:
                    if team_raw not in unmapped_teams:
                        unmapped_teams[team_raw] = {'OPEN': 0, 'CLOSED': 0}
                    unmapped_teams[team_raw][cat] += 1
            
            total[cat] += 1
 
        for ut, vals in unmapped_teams.items():
            pivot[ut] = vals
 
        sorted_teams = sorted(pivot.items(), key=lambda x: x[0])
 
        title_tag = " STA" if sheet_name else ""
        msg = f"📊 *REKAP GANGGUAN MPW{title_tag} \\(OPEN & CLOSED\\)*\n"
        msg += "```\n"
        msg += "TEKNISI    | OPEN | CLOSED | TOTAL\n"
        msg += "-----------|------|--------|------\n"
        
        for name, v in sorted_teams:
            t_total = v['OPEN'] + v['CLOSED']
            if t_total == 0:
                continue
            short_name = get_short_name(name).ljust(10)
            msg += f"{short_name} | {str(v['OPEN']).rjust(4)} | {str(v['CLOSED']).rjust(6)} | {str(t_total).rjust(5)}\n"
            
        msg += "-----------|------|--------|------\n"
        grand_total = total['OPEN'] + total['CLOSED']
        msg += f"{'TOTAL'.ljust(10)} | {str(total['OPEN']).rjust(4)} | {str(total['CLOSED']).rjust(6)} | {str(grand_total).rjust(5)}\n"
        msg += "```\n"
        
        pct_resolved = (total['CLOSED'] / grand_total * 100) if grand_total > 0 else 0
        
        msg += "📍 *Ringkasan Gangguan:*\n"
        msg += f"🔴 *Total Open* : {total['OPEN']} Tiket\n"
        msg += f"🟢 *Total Closed* : {total['CLOSED']} Tiket\n"
        pct_str = f"{pct_resolved:.1f}".replace('.', '\\.')
        msg += f"📈 *Resolution Rate* : {pct_str}%\n\n"
        
        open_tickets = []
        for row in rows[1:]:
            if len(row) <= max(idx_status, idx_team, idx_incident):
                continue
            incident = str(row[idx_incident]).strip()
            status_raw = str(row[idx_status]).upper().strip()
            team_raw = str(row[idx_team]).strip()
            cust_type = row[idx_cust_type].strip() if idx_cust_type != -1 and len(row) > idx_cust_type else ""
            
            if incident and not any(x in status_raw for x in KATEGORI_CLOSED):
                open_tickets.append((incident, team_raw, status_raw, cust_type))
                
        if open_tickets:
            # Urutkan berdasarkan prioritas customer type (1. MANJA, 2. REGULER, 3. HVC_GOLD)
            open_tickets.sort(key=lambda x: (get_priority_rank(x[3]), x[0]))
            
            msg += "⚠️ *Daftar Tiket PENDING / OPEN:*\n"
            for inc, t, st, ct in open_tickets[:15]:
                ct_str = f" \\({escape_md(ct)}\\)" if ct else ""
                msg += f"• `{escape_md(inc)}` \\[{escape_md(st)}\\]{ct_str} \\- {escape_md(t)}\n"
            if len(open_tickets) > 15:
                msg += f"_\\+{len(open_tickets) - 15} tiket open lainnya\\.\\.\\._\n"
        else:
            msg += "✅ *Semua gangguan telah CLOSED\\!*\n"
            
        return msg
    except Exception as e:
        return f"❌ *Error Rekap:* {escape_md(str(e))}"
