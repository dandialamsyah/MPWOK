# Bot Monitoring Gangguan Assurance Mempawah (Google Sheets & Gemini AI)

Bot Telegram ini dirancang khusus untuk memantau status gangguan (Open & Closed) secara real-time langsung dari data Google Sheets Anda untuk tim teknisi assurance Mempawah. Bot ini juga terintegrasi dengan **Gemini AI** untuk merumuskan pesan pengingat penyelesaian tiket yang masih Open ke teknisi.

---

## 🚀 Fitur Utama

1. **Rekap Gangguan Berkala (`/rekap`)**:
   * Menampilkan tabel pivot teks antara nama teknisi dan status gangguan (**OPEN** dan **CLOSED**).
   * Menampilkan ringkasan jumlah total gangguan, total open, total closed, dan persentase penyelesaian (*Resolution Rate*).
   * Menampilkan daftar tiket yang masih pending/open yang diurutkan berdasarkan prioritas jenis customer:
     1. **MANJA**
     2. **REGULER**
     3. **HVC_GOLD**
   * Dikirim otomatis ke grup koordinasi setiap **1 jam sekali** pada jam kerja (08:00 - 00:00).

2. **Pengingat Tiket Open (`/cek_open`)**:
   * Mendeteksi tiket gangguan berstatus Open/Pending.
   * Menggunakan **Gemini AI (Google GenAI SDK)** untuk membuat draf pesan pengingat penyelesaian tiket secara santai namun tegas.
   * Mengelompokkan tiket open per teknisi, mengurutkannya berdasarkan prioritas jenis customer, dan mentag (@mention) username Telegram teknisi yang bersangkutan secara otomatis.
   * Berjalan otomatis setiap **30 menit sekali** (08:00 - 00:00). Jika tidak ada antrean tiket open, bot tidak akan mengirim pesan apa pun agar tidak mengganggu grup.

3. **Struktur Fleksibel & Cerdas (Dynamic Headers & Name Resolution)**:
   * **Pencarian Kolom Dinamis**: Bot secara otomatis mendeteksi kolom meskipun letaknya bergeser. Mendukung header kolom seperti `STATUS`/`STATE`, `TEAM`/`TEKNISI`/`PETUGAS`, `INCIDENT`/`WONUM`/`TICKET ID`, `DEVICE NAME`/`ALPRO`/`ODP`, serta `CUSTOMER TYPE`/`PRIORITAS`.
   * **Resolusi Nama Teknisi**: Secara cerdas mencocokkan variasi penulisan nama di Google Sheet ke nama resmi di konfigurasi (`config.py`).

---

## 🛠️ Panduan Instalasi & Menjalankan Lokal

### 1. Prasyarat
Pastikan komputer Anda sudah terinstal Python 3.10+ dan Anda memiliki:
* File `credentials.json` (Google Service Account Credentials)
* Token Bot Telegram (dari @BotFather)
* API Key Gemini (dari Google AI Studio)

### 2. Bagikan Akses Google Sheet
Bagikan akses edit (Share as Editor) spreadsheet Google Sheet Anda ke email service account bot berikut:
`korlapsnw@bot-korlap-ai.iam.gserviceaccount.com`

### 3. Instalasi Modul
Buka terminal pada direktori proyek, lalu buat virtual environment dan instal modul yang dibutuhkan:
```bash
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 4. Konfigurasi Lingkungan (`.env`)
Buat berkas `.env` pada direktori utama proyek, lalu isi:
```env
BOT_TOKEN=TOKEN_BOT_TELEGRAM_ANDA
GEMINI_KEY=API_KEY_GEMINI_ANDA
SHEET_NAME=NAMA_SPREADSHEET_GOOGLE_SHEET_ANDA
GROUP_ID=ID_CHAT_GRUP_TELEGRAM_ANDA
```

### 5. Menjalankan Bot
Jalankan bot melalui terminal lokal Anda:
```bash
.\.venv\Scripts\python main.py
```

---

## ☁️ Panduan Deployment (24/7 Online) di Railway.app

Untuk menjaga bot Anda tetap menyala tanpa perlu menghidupkan komputer lokal:

1. Buat **Private Repository** di GitHub Anda, lalu unggah proyek ini menggunakan **GitHub Desktop** (pastikan opsi *Keep this code private* tercentang). File `.env`, folder `.venv`, dan `credentials.json` otomatis tidak akan ikut terunggah karena dilindungi oleh `.gitignore`.
2. Masuk ke **[Railway.app](https://railway.app/)** menggunakan akun GitHub Anda.
3. Buat **New Project** dan pilih **Deploy from GitHub repo**, lalu arahkan ke repositori proyek ini.
4. Masuk ke tab **Variables** di panel Railway Anda, lalu tambahkan variabel-variabel berikut:
   * `BOT_TOKEN` = *(Token bot Telegram)*
   * `GEMINI_KEY` = *(API Key Gemini)*
   * `SHEET_NAME` = *(Nama Google Sheet Anda)*
   * `GROUP_ID` = *(ID Grup Telegram Anda)*
   * `GOOGLE_CREDENTIALS` = *(Buka berkas `credentials.json` Anda, salin seluruh isi teks JSON di dalamnya, dan tempel/paste di kolom Value variabel ini)*
5. Klik **Save**. Railway akan memuat ulang dan mendeploy bot Anda secara otomatis.
