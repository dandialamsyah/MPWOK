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

def parse_group_id(env_name):
    env_val = strip_quotes(os.getenv(env_name))
    if not env_val:
        return None
    try:
        env_val = env_val.strip()
        # Jika user memasukkan format group ID biasa (misal -3945408033)
        # tapi tipenya adalah supergrup, tambahkan awalan -100 secara otomatis
        if env_val.startswith('-') and not env_val.startswith('-100'):
            env_val = '-100' + env_val[1:]
        return int(env_val)
    except ValueError:
        logging.warning(f"Format {env_name} tidak valid (harus berupa angka/integer).")
        return None

# Parse GROUP_ID secara aman
GROUP_ID = parse_group_id("GROUP_ID")
GROUP_ID_STA = parse_group_id("GROUP_ID_STA")
GROUP_ID_ABSEN = parse_group_id("GROUP_ID_ABSEN")
GROUP_ID_ABSEN_PROV = parse_group_id("GROUP_ID_ABSEN_PROV")

# ==================== KATEGORI STATUS ====================
KATEGORI_CLOSED = ['CLOSE', 'CLOSED']
# Jika ada status selain closed, akan dikategorikan sebagai OPEN secara fallback.
KATEGORI_OPEN = ['OPEN', 'TANAM UBI']

# ==================== MAPPING TEKNISI ASSURANCE MEMPAWAH ====================
TECH_TEAMS = [
    {"canonical": "ADE-ANDRE", "names": ["ADE-ANDRE", "ADE", "ANDRE"], "tags": "@ade_faisal12 @AndreKurniawan06"},
    {"canonical": "ASEP-RONI", "names": ["ASEP-RONI", "ASEP", "RONI"], "tags": "@Asep_oriyanto96 @Merona_merah"},
    {"canonical": "CHAIRUL-YUDA", "names": ["CHAIRUL-YUDA", "CHAIRUL", "YUDA"], "tags": "@ChairulGunawan @yuda1234567890"},
    {"canonical": "DEDI-HENDRA", "names": ["DEDI-HENDRA"], "tags": "@Dandelion_dedy @HendraNurFauzan"},
    {"canonical": "DESTA-JEFRI", "names": ["DESTA-JEFRI", "DESTA", "JEFRI"], "tags": "@DestA_GigeL @makenioranggg"},
    {"canonical": "YOGI", "names": ["YOGI"], "tags": "@yoimkumiss"},
    {"canonical": "BOBY-BAHRI", "names": ["BOBY-BAHRI", "BAHRI-BOBY", "BAHRI", "BOBY"], "tags": "@Bobystwn0 @bahri1206"},
    {"canonical": "DICKY-NAUFAL", "names": ["DICKY-NAUFAL"], "tags": "@Dicky_Gunawan @nplafrisi"},
    {"canonical": "ARIF-JULIANDRI", "names": ["ARIF-JULIANDRI"], "tags": "@arifmaulana_10 @saputrajuliandri94"},
    {"canonical": "DEDY-DIKA", "names": ["DEDY-DIKA"], "tags": "@dedy_nurwanda @dikaasii"},
    {"canonical": "MAMAN", "names": ["MAMAN"], "tags": "@maman_3070"},
    {"canonical": "TINO-NIZAR", "names": ["TINO-NIZAR"], "tags": "@Tinoeeee @Nizar_Qadrie"},
    {"canonical": "DEDI", "names": ["DEDI"], "tags": "@Dandelion_dedy"},
    {"canonical": "RUDI-RANDA", "names": ["RUDI-RANDA"], "tags": "@Randa_z @Rudi_hartono21"},
    {"canonical": "MERI", "names": ["MERI"], "tags": "@PAPA_MUDA05"},
]

TEAM_LIST = [t["canonical"] for t in TECH_TEAMS]

TEKNISI_LIBUR = []

# ==================== MAPPING TEKNISI PROVISIONING MEMPAWAH ====================
PROV_TEAMS = [
    {"tags": "@AR_IISSS @TEKNISI_EXPRESSSS001 @TeknisiLokal @Riyan_25030224 @suparj0 @Ginting_01 @Vann113 @Maz_amzi09 @KacongTamvan @INTEL_0001 @Ovanhafizan @Drmawwn @fnano12 @Yekinnino @MasihNego @Suhardy92 @adearkhm16 @AhmadHafizyee @asmoking1 @IM_AAMMM @kyy37 @rickyfahrudillah"}
]
