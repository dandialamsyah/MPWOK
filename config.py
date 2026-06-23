import os
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_dotenv():
    # Mengambil path file .env relatif terhadap file script ini
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    # Menghapus tanda kutip jika ada
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    if key not in os.environ:
                        os.environ[key] = val

# Pemuatan Variabel Lingkungan
load_dotenv()

def strip_quotes(val):
    if not val:
        return val
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    return val

# Konfigurasi Utama
BOT_TOKEN = strip_quotes(os.getenv("BOT_TOKEN"))
GEMINI_KEY = strip_quotes(os.getenv("GEMINI_KEY"))
SHEET_NAME = strip_quotes(os.getenv("SHEET_NAME", "Produktivitas_BOT"))

# Parse GROUP_ID secara aman
group_id_env = strip_quotes(os.getenv("GROUP_ID"))
if group_id_env:
    try:
        GROUP_ID = int(group_id_env)
    except ValueError:
        logging.warning("Format GROUP_ID tidak valid (harus berupa angka/integer).")
        GROUP_ID = None
else:
    GROUP_ID = None

# ==================== KATEGORI STATUS ====================
KATEGORI_CLOSED = ['CLOSE', 'CLOSED']
# Jika ada status selain closed, akan dikategorikan sebagai OPEN secara fallback.
KATEGORI_OPEN = ['OPEN', 'TANAM UBI']

# ==================== MAPPING TEKNISI ASSURANCE MEMPAWAH ====================
TECH_TEAMS = [
    {"names": ["ADE-ANDRE", "ADE", "ANDRE"], "tags": "@ade_faisal12 @AndreKurniawan06"},
    {"names": ["ASEP-RONI", "ASEP", "RONI"], "tags": "@Asep_oriyanto96 @Merona_merah"},
    {"names": ["CHAIRUL-YUDA", "CHAIRUL", "YUDA"], "tags": "@ChairulGunawan @yuda1234567890"},
    {"names": ["DEDI"], "tags": "@Dandelion_dedy"},
    {"names": ["DESTA-JEFRI", "DESTA", "JEFRI"], "tags": "@DestA_GigeL @makenioranggg"},
    {"names": ["YOGI"], "tags": "@yoimkumiss"},
    {"names": ["BOBY-BAHRI"], "tags": "@Bobystwn0 @bahri1206"},
]

TEAM_LIST = [
    "ADE-ANDRE",
    "ASEP-RONI",
    "CHAIRUL-YUDA",
    "DEDI",
    "DESTA-JEFRI",
    "YOGI"
    "BOBY-BAHRI"
]

TEKNISI_LIBUR = []
