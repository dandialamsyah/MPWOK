# Bot WOTRAX - Asisten Operasional Korlap & Teknisi (Google Sheets & Gemini AI)

Bot WOTRAX adalah bot Telegram operasional berbasis Python yang dirancang untuk memantau produktivitas tim teknisi lapangan secara real-time langsung dari data Google Sheets Anda. Bot ini juga terintegrasi dengan **Gemini AI** untuk merumuskan pesan penagihan berkas penunjang (BAI) secara otomatis ke teknisi.

---

## 🚀 Fitur Utama

1. **Rekap Produktivitas Berkala**:
   - Menghasilkan tabel pivot teks sederhana antara nama teknisi dan status pekerjaan (`KP` = Kendala Pelanggan, `KT` = Kendala Teknis, `OGP` = Ongoing Process, `PSG` = Terpasang, `PS` = Complete PS).
   - Menampilkan klasemen visual prestasi PS hari ini menggunakan grafik balok (`████░░░░░░ 04`).
   - Dikirimkan secara otomatis ke grup koordinasi setiap **1 jam sekali** pada jam kerja (08:00 - 00:00).

2. **Cek ACTCOMP (Tagihan BAI Otomatis)**:
   - Mendeteksi pekerjaan berstatus `ACTCOMP` yang belum mengumpulkan berkas BAI.
   - Menggunakan **Gemini AI (Google GenAI SDK)** untuk membuat draf pesan penagihan berkas BAI secara variatif, tegas, namun tetap santai.
   - Mentag (@mention) username Telegram teknisi yang bersangkutan secara otomatis.
   - Berjalan otomatis setiap **30 menit sekali** (08:00 - 00:00), dengan sistem penyaringan cerdas: **jika tidak ada antrean pending ACTCOMP, bot tidak akan mengirim pesan apa pun ke grup** agar tidak mengganggu.

3. **Cerdas & Tahan Eror (Name Resolution & Row Filter)**:
   - **Resolusi Nama Teknisi**: Secara cerdas mencocokkan variasi penulisan nama di Google Sheet (misal: `"DIKY FEBRIANSAH - SAMSUL"` atau `"ABIL- HAFIZ"`) ke nama resmi di konfigurasi (`"DIKY FEBRIANSAH"` atau `"ABIL - APIS"`), sehingga statistik load balancing dan klasemen terhitung akurat tanpa baris ganda.
   - **Filter Baris Kosong**: Menyaring data berdasarkan kolom `WONUM` agar baris kosong di bawah sheet tidak merusak statistik rekap.
   - **Pembersih Tanda Kutip**: Otomatis membersihkan tanda kutip (`"` atau `'`) dari isian variabel di cloud/Railway untuk menghindari eror parser token.

---

## 📂 Struktur Repositori

* **`main.py`**: Berkas utama logika bot Telegram (`telebot`) beserta pengaturan *background worker threads* (penjadwal laporan otomatis).
* **`sheets_handler.py`**: Berkas backend pengolahan Google Sheets API (`gspread`) dan pemanggilan model Gemini AI.
* **`config.py`**: Konfigurasi terpusat berisi token, kategori status pekerjaan, dan daftar resmi tim teknisi lapangan beserta username Telegram mereka.
* **`prompt_belajar_bot.md`**: Prompt panduan belajar terperinci untuk membuat bot ini dari nol menggunakan AI coding assistant.
* **`.gitignore`**: Mengamankan berkas kredensial sensitif agar tidak terunggah ke repositori GitHub.

---

## 🛠️ Panduan Instalasi & Menjalankan Lokal

### 1. Prasyarat
Pastikan komputer Anda sudah terinstal Python 3.10+ dan Anda memiliki:
- `credentials.json` (Google Service Account Credentials)
- Token Bot Telegram (dari @BotFather)
- API Key Gemini (dari Google AI Studio)

### 2. Instalasi Modul
Buka terminal pada direktori proyek, lalu instal modul yang dibutuhkan:
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Lingkungan (`.env`)
Buat berkas `.env` pada direktori utama proyek, lalu isi:
```env
BOT_TOKEN=TOKEN_BOT_TELEGRAM_ANDA
GEMINI_KEY=API_KEY_GEMINI_ANDA
SHEET_NAME=Produktivitas_BOT
GROUP_ID=ID_CHAT_GRUP_TELEGRAM_ANDA
```

### 4. Menjalankan Bot
Jalankan bot melalui terminal lokal Anda:
```bash
python main.py
```

---

## ☁️ Panduan Deployment (24/7 Online) di Railway.app

Untuk menjaga bot Anda tetap menyala tanpa perlu menghidupkan komputer lokal:

1. Buat **Private Repository** di GitHub Anda, lalu unggah proyek ini ke repositori tersebut (`.env` dan `credentials.json` otomatis tidak ikut terunggah).
2. Masuk ke **[Railway.app](https://railway.app/)** menggunakan akun GitHub Anda.
3. Buat **New Project** dan pilih **Deploy from GitHub repo**, lalu arahkan ke repositori proyek ini.
4. Masuk ke tab **Variables** di panel Railway Anda, lalu tambahkan variabel-variabel berikut:
   - `BOT_TOKEN` = *(Token bot Telegram)*
   - `GEMINI_KEY` = *(API Key Gemini)*
   - `SHEET_NAME` = `Produktivitas_BOT`
   - `GROUP_ID` = *(ID Grup Telegram Anda)*
   - `GOOGLE_CREDENTIALS` = *(Buka berkas `credentials.json` Anda, salin seluruh isi teks di dalamnya, dan tempel/paste di kolom Value variabel ini)*
5. Klik **Save**. Railway akan mendeteksi pembaruan dan secara otomatis mendeploy bot Anda.
