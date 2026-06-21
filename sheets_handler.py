import re
import os
import json
import logging
import gspread
from gspread import Cell
from google.oauth2.service_account import Credentials
from telebot.formatting import escape_markdown

from config import (
    SHEET_NAME,
    KATEGORI_TERPASANG,
    KATEGORI_KENDALA_PELANGGAN,
    KATEGORI_KENDALA_TEKNIS,
    TECH_TEAMS,
    TEAM_LIST,
    TEKNISI_LIBUR
)

# Setup Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
ws_wo = None

try:
    google_creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if google_creds_json:
        info = json.loads(google_creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPE)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
    gc = gspread.authorize(creds)
    sh = gc.open(SHEET_NAME)
    ws_wo = sh.sheet1
except Exception as e:
    logging.error(f"Gagal inisialisasi Google Sheets: {e}")
    ws_wo = None

def escape_md(text):
    if not text:
        return ""
    # Menggunakan utility dari pyTelegramBotAPI untuk pembersihan karakter MarkdownV2 yang lebih andal
    return escape_markdown(str(text))

def get_team_tags(name_in_sheet):
    name_upper = str(name_in_sheet).upper().strip()
    if not name_upper or any(x in name_upper for x in ["UNASSIGNED", "BLM ASSIGN"]): 
        return ""
    for team in TECH_TEAMS:
        if any(member in name_upper for member in team["names"]):
            return team["tags"].replace('_', r'\_')
    return f"Teknisi {escape_md(name_in_sheet)}"

def get_short_name(full_name):
    name = str(full_name).upper()
    mapping = {
        "AKMAL": "Akml-Andre", "YOGI": "Yogi-Reja", "ANDRYANSYAH": "Andry-Rtno",
        "ARI FITRI": "Ari-Syekhl", "ARJULI": "Arjuli", "JIMIANSYAH": "Jimi",
        "FERRY": "Ferry", "RONALDO": "Ronaldo", "FIRDAN": "Firdan-Hdo",
        "NURDIN": "Nurd-Hdyat", "SUGIANTO": "Sigo-Aldi", "DIKY": "Diky-Dodi", "ABIL":"Abil-Apis"
    }
    for key, val in mapping.items():
        if key in name: return val
    return name[:10]

def get_target_tech_by_odp(odp_string):
    odp = str(odp_string).upper().strip()
    if "ODP-PMK-F" in odp: return "FIRDAN IRAWAN - HADO MUANTO"
    if any(x in odp for x in ["ODP-TBA-F", "ODP-SMB-FS"]): return "SUGIANTO - ALDIANSYAH"
    if "ODP-SMB-F" in odp: return "NURDIN ISMAIL - MUHAMMAD HIDAYAT"
    if any(x in odp for x in ["ODP-BKY-FD", "ODP-BKY-FE", "ODP-BKY-FF", "ODP-BKY-FG"]): return "DIKY FEBRIANSAH"
    if "ODP-BKY-F" in odp: return "YOGI RINALDI - REJA"
    return None

def perform_auto_assign():
    if not ws_wo: return
    try:
        rows = ws_wo.get_all_values()
        if not rows or len(rows) < 2: return
        header = [str(h).upper().strip() for h in rows[0]]
        
        idx_tech = header.index('TEKNISI')
        idx_status = header.index('STATUS')
        idx_alpro = header.index('ALPRO')
        
        available_teams = [t for t in TEAM_LIST if t not in TEKNISI_LIBUR]
        load_count = {name: 0 for name in available_teams}
        
        unassigned_indices = []
        for i, row in enumerate(rows[1:], start=2):
            tech = str(row[idx_tech]).strip()
            status = str(row[idx_status]).upper().strip()
            if not tech or any(x in tech.upper() for x in ["UNASSIGNED", "BLM ASSIGN"]):
                unassigned_indices.append((i, row))
            elif tech in load_count and status not in ['PS', 'COMPLETE PS']:
                load_count[tech] += 1

        if not unassigned_indices: return

        cells_to_update = []
        for row_idx, row in unassigned_indices:
            target_tech = get_target_tech_by_odp(row[idx_alpro])
            if not target_tech or target_tech in TEKNISI_LIBUR:
                # Load balancing
                restricted = ["FIRDAN IRAWAN - HADO MUANTO", "SUGIANTO - ALDIANSYAH", "NURDIN ISMAIL - MUHAMMAD HIDAYAT", "DIKY FEBRIANSAH", "YOGI RINALDI - REJA"]
                flex_teams = {k: v for k, v in load_count.items() if k not in restricted}
                target_tech = min(flex_teams, key=flex_teams.get) if flex_teams else min(load_count, key=load_count.get) if load_count else None

            if target_tech:
                cells_to_update.append(Cell(row=row_idx, col=idx_tech + 1, value=target_tech))
                load_count[target_tech] += 1
        
        if cells_to_update:
            ws_wo.update_cells(cells_to_update)
            logging.info(f"Auto-assign {len(cells_to_update)} WO.")
    except Exception as e:
        logging.error(f"Error Auto Assign: {e}")

def fetch_actcomp_data(client=None, model_id=None):
    if not ws_wo: return r"❌ Google Sheet tidak terhubung\."
    try:
        rows = ws_wo.get_all_values()
        header = [str(h).upper().strip() for h in rows[0]]
        idx_wonum, idx_status, idx_tech = header.index('WONUM'), header.index('STATUS'), header.index('TEKNISI')
        idx_ket = header.index('KETERANGAN') if 'KETERANGAN' in header else -1
        
        alerts = {}
        for row in rows[1:]:
            status = str(row[idx_status]).upper().strip()
            if 'ACTCOMP' in status:
                tech = str(row[idx_tech]).strip()
                tags = get_team_tags(tech)
                if not tags: continue
                ket_val = row[idx_ket] if idx_ket != -1 and len(row) > idx_ket else ""
                info = f"▫️ `{escape_md(row[idx_wonum])}` \\[{escape_md(status)}\\] {escape_md(ket_val) if ket_val else '_blm BAI_'}"
                if tags not in alerts: alerts[tags] = []
                alerts[tags].append(info)
        
        if not alerts: return "✅ *Semua status ACTCOMP sudah beres\\!*"
        
        ai_msg = "Ayo teman\\-teman, jangan lupa segera lengkapi BAI\\-nya ya\\!"
        if client and model_id:
            try:
                res = client.models.generate_content(
                    model=model_id, 
                    contents="Berikan satu kalimat singkat, santai namun tetap tegas dalam bahasa Indonesia untuk menagih berkas BAI ke teknisi lapangan. Maksimal 15 kata. Tanpa markdown."
                )
                ai_msg = escape_md(res.candidates[0].content.parts[0].text.strip())
            except Exception as e:
                logging.warning(f"Gagal generate AI message: {e}")
                pass

        msg = f"🔔 *{ai_msg}*\n\n"
        for tag, wos in alerts.items():
            msg += f"{tag}\n" + "\n".join(wos) + "\n\n"
        return msg
    except Exception as e:
        return f"❌ *Error ACTCOMP:* {escape_md(str(e))}"

def fetch_rekap_data():
    if not ws_wo: return r"❌ Google Sheet tidak terhubung\."
    try:
        rows = ws_wo.get_all_values()
        if not rows: return "Data Kosong"
        header = [str(h).upper().strip() for h in rows[0]]
        idx_status, idx_tech = header.index('STATUS'), header.index('TEKNISI')
        
        pivot = {}
        total = {'KP': 0, 'KT': 0, 'OGP': 0, 'PSG': 0, 'PS': 0}
        active_tags = set()

        for row in rows[1:]:
            if len(row) <= max(idx_status, idx_tech): continue
            tech = str(row[idx_tech]).strip()
            tags = get_team_tags(tech)
            if not tags: continue
            
            status = str(row[idx_status]).upper().strip()
            if tech not in pivot: pivot[tech] = {'KP': 0, 'KT': 0, 'OGP': 0, 'PSG': 0, 'PS': 0}
            
            cat = 'OGP'
            if status == 'COMPLETE PS': cat = 'PS'
            elif any(x in status for x in KATEGORI_TERPASANG): cat = 'PSG'
            elif any(x in status for x in KATEGORI_KENDALA_PELANGGAN): cat = 'KP'
            elif any(x in status for x in KATEGORI_KENDALA_TEKNIS): cat = 'KT'
            
            pivot[tech][cat] += 1
            total[cat] += 1
            active_tags.add(tags)

        # Bagian 1: Tabel Utama
        msg = "📊 *REKAP PRODUKTIVITAS BERKALA*\n"
        msg += "```\n"
        msg += "TEKNISI    |KP|KT|OGP|PSG|PS \n"
        msg += "-----------|--|--|---|---|---\n"
        for name, v in pivot.items():
            short_name = get_short_name(name).ljust(10)
            msg += f"{short_name} |{str(v['KP']).rjust(2)}|{str(v['KT']).rjust(2)}|{str(v['OGP']).rjust(3)}|{str(v['PSG']).rjust(3)}|{str(v['PS']).rjust(2)}\n"
        msg += "-----------|--|--|---|---|---\n"
        msg += f"{'TOTAL'.ljust(10)} |{str(total['KP']).rjust(2)}|{str(total['KT']).rjust(2)}|{str(total['OGP']).rjust(3)}|{str(total['PSG']).rjust(3)}|{str(total['PS']).rjust(2)}\n"
        msg += "```\n"
        
        msg += "📍 *Ringkasan:*\n"
        msg += f"🔵 *Total PS* : {total['PS']} WO\n"
        msg += f"🟢 *Total Terpasang* : {total['PSG']} WO\n"
        msg += f"⚠️ *Total Kendala* : {total['KP']+total['KT']} WO\n"
        msg += f"⏳ *Total OGP* : {total['OGP']} WO\n\n"
        
        # Bagian 2: KLASEMEN PS (Bar Chart)
        sorted_ps = sorted(pivot.items(), key=lambda x: x[1]['PS'], reverse=True)
        max_ps = max([v['PS'] for v in pivot.values()]) if pivot else 1
        bar_width = 10

        msg += "🏆 *KLASEMEN PS HARI INI:*\n"
        msg += "```\n"
        for name, v in sorted_ps:
            count = v['PS']
            short_name = get_short_name(name).ljust(10)
            fill = int((count / max_ps) * bar_width) if max_ps > 0 else 0
            bar = "█" * fill + "░" * (bar_width - fill)
            msg += f"{short_name} {bar} {str(count).zfill(2)}\n"
        msg += "```\n"
        
        msg += "👥 *On Duty:* " + " ".join(list(active_tags))
        return msg
    except Exception as e:
        return f"❌ *Error Rekap:* {escape_md(str(e))}"
