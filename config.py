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
                    os.environ[key] = val

# Pemuatan Variabel Lingkungan
load_dotenv()

# Konfigurasi Utama
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
SHEET_NAME = os.getenv("SHEET_NAME", "Produktivitas_BOT")

# Parse GROUP_ID secara aman
group_id_env = os.getenv("GROUP_ID")
if group_id_env:
    try:
        GROUP_ID = int(group_id_env)
    except ValueError:
        logging.warning("Format GROUP_ID tidak valid (harus berupa angka/integer).")
        GROUP_ID = None
else:
    GROUP_ID = None

# ==================== KATEGORI STATUS ====================
KATEGORI_TERPASANG = [
    'REVOKE', 'LIMITASI ONU', 'REVOKE MIA', 'SURVEY MIA', 'ACTCOMP', 
    'OKE TARIK', 'COMPLETE PS', 'LANJUT LENSA', 'VALCOMP', 'PROSES PELURUSAN', 
    'VALINS ULANG', 'INPUL', 'TARIKAN > JAM 18', 'LANJUT MYTECH', 
    'OK TARIK KENDALA KARTU', 'ONT TDK DETEK', 'ASSIGN ULANG'
]

KATEGORI_KENDALA_PELANGGAN = [
    'BATAL', 'ATK', 'INDIKASI CABUT PASANG', 'DOUBLE INPUT', 'GANTI PAKET', 
    'RUMAH KOSONG', 'BEDA SEGMENT', 'PENDING PELANGGAN', 'KENDALA MATERIAL/NTE', 
    'PENDING HI', 'KENDALA HOMEPASS'
]

KATEGORI_KENDALA_TEKNIS = [
    'TANAM TIANG', 'ODP FULL', 'ODP JAUH', 'KENDALA JALUR/RUTE TARIKAN', 
    'ODP LOSS', 'ODP RETI', 'SALAH TAGGING', 'CROSSING JALAN', 'NO ODP', 
    'REVOKE DONE', 'ODP RUSAK'
]

# ==================== MAPPING TEKNISI ====================
TECH_TEAMS = [
    {"names": ["AKMAL AZAMI", "ANDRE"], "tags": "@Guruku_Sayang @ANDRE16011954"},
    {"names": ["YOGI RINALDI", "REJA"], "tags": "@Yogirinaldi @rjaaanihhh"},
    {"names": ["ANDRYANSYAH SAPUTRA", "RATNO"], "tags": "@Andryansyahsaputra @Ratno_Aje"},
    {"names": ["ARI FITRIANSYAH", "SYEKHUL AKHYAR"], "tags": "@Ari_fitriansyah29 @Syekhulakhyar"},
    {"names": ["ARJULI", "REVALDO"], "tags": "@arjuli @rvllldoo"},
    {"names": ["JIMIANSYAH"], "tags": "@Jimiansyah"},
    {"names": ["FERRY SEPTIAN"], "tags": "@Pericay"},
    {"names": ["RONALDO APRILINI"], "tags": "@Ronalduhh"},
    {"names": ["FIRDAN IRAWAN", "HADO MUANTO"], "tags": "@Firdanirawn @Budak_Gang"},
    {"names": ["NURDIN ISMAIL", "MUHAMMAD HIDAYAT"], "tags": "@nurdin_1919 @Hidayat_SKY"},
    {"names": ["SUGIANTO", "ALDIANSYAH"], "tags": "@SihoooJS50 @aldinsh"},
    {"names": ["DIKY FEBRIANSAH"], "tags": "@Dikyfebriansah46"},
    {"names": ["DWI FIRMANSYAH"], "tags": "@Muridku_Sayang"},
    {"names": ["ABIL", "APIS"], "tags": "@abillll11 @Hafidz_ang"},
]

TEAM_LIST = [
    "AKMAL AZAMI - ANDRE",
    "YOGI RINALDI - REJA",
    "ANDRYANSYAH SAPUTRA - RATNO",
    "ARI FITRIANSYAH - SYEKHUL AKHYAR",
    "ARJULI - REVALDO",
    "JIMIANSYAH - SOLO",
    "FERRY SEPTIAN - SOLO",
    "RONALDO APRILINI - SOLO",
    "FIRDAN IRAWAN - HADO MUANTO",
    "NURDIN ISMAIL - MUHAMMAD HIDAYAT",
    "SUGIANTO - ALDIANSYAH",
    "DIKY FEBRIANSAH",
    "DWI FIRMANSYAH",
    "ABIL - APIS"
]

TEKNISI_LIBUR = ["AKMAL AZAMI - DWI FIRMANSYAH"]
