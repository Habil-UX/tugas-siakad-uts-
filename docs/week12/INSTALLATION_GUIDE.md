# PANDUAN INSTALASI & KONFIGURASI (`INSTALLATION_GUIDE.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 3–11  
**Versi Python Minimum:** Python 3.11+

---

## 1. Prasyarat Sistem

Pastikan perangkat Anda telah terinstal:
- **Python 3.11+** (disarankan Python 3.11.9)
- **pip** (Python Package Installer)
- **SQLite 3** (sudah terintegrasi secara bawaan di dalam library standar Python `sqlite3`)
- Opsional: **cURL** atau **Postman** untuk pengujian API manual via terminal, serta browser modern (Chrome/Edge/Firefox) untuk mengakses Swagger UI dan halaman Dashboard.

---

## 2. Langkah-Langkah Instalasi dari Lingkungan Baru (Clean Environment)

### Langkah 1 — Ekstrak Folder Proyek
Ekstrak paket `FINAL_SUBMISSION_SIAKAD.zip` atau masuk ke direktori `FINAL_SUBMISSION`:
```powershell
cd FINAL_SUBMISSION
```

### Langkah 2 — Buat dan Aktifkan Virtual Environment
**Pada Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
**Pada Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Langkah 3 — Instal Seluruh Dependency
```powershell
pip install -r requirements.txt
```
Daftar paket yang diinstal mencakup:
- `fastapi==0.109.0`, `uvicorn==0.27.0`
- `sqlalchemy==2.0.25`, `alembic==1.13.1`
- `pydantic==2.5.3`, `pydantic-settings==2.1.0`, `email-validator==2.1.0`
- `python-dotenv`
- `reportlab==4.2.5` (Generator PDF Transkrip)
- `APScheduler==3.11.3` (BackgroundScheduler & CronTrigger Keuangan)
- `pytest==7.4.4`, `pytest-cov==4.1.0`, `httpx==0.26.0`, `hypothesis==6.98.0`

### Langkah 4 — Konfigurasi File Environment (`.env`)
Salin file konfigurasi contoh `.env.example` menjadi `.env`:
```powershell
Copy-Item .env.example .env
```
Isi default `.env`:
```ini
DATABASE_URL=sqlite:///./pmb.db
SECRET_KEY=replace-with-your-hmac-secret-key
WEBHOOK_SECRET=replace-with-your-webhook-hmac-secret
```
> **Catatan:** Apabila file `.env` belum dibuat, aplikasi secara otomatis menggunakan nilai fallback yang aman (`sqlite:///./pmb.db`) untuk keperluan pengembangan dan pengujian lokal.

### Langkah 5 — Jalankan Migrasi Database & Seed Data Awal (Alembic)
Apabila menggunakan database kosong baru (atau memastikan database berada pada revisi terbaru `b7e4c1d9a204`):
```powershell
python -m alembic upgrade head
```
Perintah di atas secara otomatis:
1. Membangun seluruh **22 tabel domain** (+ tabel `alembic_version`), *foreign keys*, *unique constraints*, *composite indexes*, SQLite *Trigger* (`trg_grade_history_update`), dan *View* (`v_grade_history`).
2. Menjalankan *seed data* referensi secara idempotent (`INSERT OR IGNORE`) untuk:
   - `skala_nilai`: `A (4.0)`, `B (3.0)`, `C (2.0)`, `D (1.0)`, `E (0.0)`
   - `program_studi`: `TIF - Teknik Informatika (Rp5.000.000)` & `EKO - Manajemen (Rp4.000.000)`
   - `jalur_masuk`: `SNBP`, `SNBT`, `MANDIRI`
   - `payment_method`: `BANK_TRANSFER`, `CASH`, `VIRTUAL_ACCOUNT`, `EWALLET`
   - `app_user` (akun demo RBAC): `admin` (`admin123`), `dosen_pa` (`dosen123`), `mahasiswa1` (`mhs123`)

Untuk memverifikasi status revisi migrasi saat ini:
```powershell
python -m alembic current
python -m alembic heads
```

---

## 3. Menjalankan Server Aplikasi (FastAPI + APScheduler)

Jalankan server Uvicorn:
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Atau dalam mode pengembangan (*auto-reload*):
```powershell
python -m uvicorn app.main:app --reload
```
> Saat FastAPI mengalami *startup*, `lifespan` manager secara otomatis menyalakan `BillingScheduler` (`BackgroundScheduler` + `CronTrigger`) dan mematikannya secara bersih saat *shutdown*.

Akses layanan melalui browser:
- **Root API Status:** `http://127.0.0.1:8000/`
- **Swagger UI (Dokumentasi Interaktif):** `http://127.0.0.1:8000/docs`
- **OpenAPI JSON Schema:** `http://127.0.0.1:8000/openapi.json`
- **Dashboard Penjadwalan & Konflik (Minggu 7–8):** `http://127.0.0.1:8000/dashboard`
- **Halaman Input & Edit Nilai + Unduh PDF Transkrip (Minggu 9–10):** `http://127.0.0.1:8000/grades-ui`
- **Dashboard Keuangan SPP & AI Report (Minggu 11):** `http://127.0.0.1:8000/finance-dashboard`

---

## 4. Menjalankan Suite Pengujian Otomatis (`pytest`)

Untuk menjalankan seluruh **357 unit, integration, concurrency, dan property-based tests** beserta laporan *code coverage*:
```powershell
python -m pytest -v --cov=app --cov-report=term-missing --cov-report=html
```
Hasil yang diharapkan:
- **`357 passed, 0 failed`**
- **Total Coverage: `99%`**
