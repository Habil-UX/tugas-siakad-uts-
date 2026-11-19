# CHECKLIST PENGUMPULAN AKHIR PROYEK (`PROJECT_SUBMISSION_CHECKLIST.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 3–11  
**Tanggal Rilis & Pengemasan:** 17 November 2026  
**Status Rilis:** **VERIFIED & READY FOR SUBMISSION**

---

## 1. Kelengkapan Source Code (`FINAL_SUBMISSION/`)

- [x] **Source Code Utama (`app/` — 29 file `.py`):**
  - `app/main.py` (FastAPI Entrypoint, `lifespan` APScheduler, Exception Handler Validasi HTTP 400)
  - `app/database.py` (SQLAlchemy Engine, `PRAGMA foreign_keys = ON`, `PRAGMA busy_timeout = 30000`)
  - `app/models/` (11 file model SQLAlchemy untuk 22 tabel domain aplikasi)
  - `app/routers/` (`auth.py`, `pmb.py`, `krs.py`, `schedules.py`, `grades.py`, `billing.py`, `payment.py`, `dashboard.py`)
  - `app/services/` (`pmb_service.py`, `krs_manager.py`, `krs_state_machine.py`, `krs_recommender.py`, `krs/validators.py`, `conflict_detector.py`, `scheduling_service.py`, `rescheduling_service.py`, `grade_service.py`, `gpa_calculator.py`, `transcript_service.py`, `billing_service.py`, `payment_service.py`, `scheduler_service.py`)
  - `app/observers/` (`schedule_subject.py`, `concrete_observers.py`, `notification_manager.py`)
  - `app/schemas/` (`auth.py`, `pmb.py`, `krs.py`, `grade.py`, `finance.py`)
  - `app/utils/` (`pdf_generator.py`, `security.py`)
- [x] **Migrasi Database & Seed Data (`alembic/` & `alembic.ini`):**
  - 8 file revisi berurutan di `alembic/versions/` (`c0b4e3a8c963` $\rightarrow$ `b7e4c1d9a204`), termasuk seed data non-destruktif (`INSERT OR IGNORE`) untuk `skala_nilai`, `program_studi`, `jalur_masuk`, `payment_method`, dan `app_user`.
- [x] **Suite Pengujian Otomatis (`tests/` & `pytest.ini`):**
  - 27 file `test_*.py` + `conftest.py` (mencakup **357 test cases**).
- [x] **Konfigurasi & Dependency:**
  - `requirements.txt` (14 paket terverifikasi)
  - `.env.example` (konfigurasi contoh tanpa *secret* sensitif)
  - `pmb.db` (database demonstrasi berisi data sintetis non-sensitif pada revisi `head` `b7e4c1d9a204`)
- [x] **Bebas dari File Sampah / Rahasia:**
  - Tidak menyertakan `venv/`, `__pycache__/`, `.pytest_cache/`, `.hypothesis/`, `.coverage`, `.env`, maupun backup database lama.

---

## 2. Kelengkapan Dokumentasi

Seluruh dokumen wajib telah tersedia baik di direktori root maupun di dalam paket `FINAL_SUBMISSION/` dan `FINAL_SUBMISSION_SIAKAD.zip`:

- [x] `README.md` — Ikhtisar arsitektur, format NIM, daftar 47 endpoint, cara instalasi & eksekusi.
- [x] `INSTALLATION_GUIDE.md` — Panduan instalasi langkah demi langkah dari lingkungan kosong (`venv`, `pip`, `.env`, `alembic`, `uvicorn`, `pytest`).
- [x] `USER_GUIDE.md` — Panduan penggunaan untuk Admin, Dosen/Dosen PA, dan Mahasiswa beserta alur UI Dashboard (`/dashboard`, `/grades-ui`, `/finance-dashboard`).
- [x] `API_DOCUMENTATION.md` — Spesifikasi lengkap 47 endpoint REST API & UI, skema JSON, HTTP status code, dan verifikasi webhook HMAC-SHA256.
- [x] `DATABASE_DOCUMENTATION.md` — Spesifikasi 23 tabel, PK/FK, unique/check constraint, composite index, SQLite trigger/view, dan rantai 8 revisi Alembic.
- [x] `AI_USAGE_LOG.md` — Catatan transparan penggunaan AI, koleksi prompt terbaik Minggu 3–11, dan verifikasi manual.
- [x] `OPAR.md` — Dokumentasi Observation, Problem, Action, Result (OPAR 1 s/d OPAR 6).
- [x] `docs/adr/` & `docs/week9-10/ADR-001-Audit-Trail.md` — 12 dokumen Architecture Decision Records (ADR) yang telah dikonsolidasikan tanpa duplikasi.
- [x] `FINAL_TEST_REPORT.md` — Laporan eksekusi 357 test dan rincian code coverage 99% per modul.
- [x] `FINAL_CLEANUP_REPORT.md` (`+ CLEANUP_AUDIT.md`, `CLEANUP_REPORT.md`) — Laporan audit dan pembersihan repository.
- [x] `PROJECT_SUBMISSION_CHECKLIST.md` — Dokumen verifikasi akhir kesiapan pengumpulan ini.

---

## 3. Hasil Pengujian & Code Coverage

- **Total Test Dijalankan:** `357 collected`
- **Hasil Eksekusi:** **`357 passed, 0 failed, 0 errors`**
- **Code Coverage (`--cov=app`):** **`99%`** (`2.374` statements, `33` missed; 40 dari 47 file modul mencapai `100%` coverage).
- **Cakupan Pengujian Khusus:**
  - *Property-Based Testing* (`Hypothesis` 1.000 kombinasi SKS KRS): **PASSED**
  - *State Machine* (12 kombinasi transisi ilegal KRS): **PASSED**
  - *True Multi-Thread Concurrency NIM* (`ThreadPoolExecutor(max_workers=8)` + `Barrier(8)`): **PASSED**
  - *Perhitungan IPK & Transkrip* (14 skenario uji parametrik mencakup nilai A/B/C/D/E & pengulangan MK): **PASSED**
  - *Siklus Migrasi Alembic* (`upgrade head` $\rightarrow$ `downgrade base` $\rightarrow$ `upgrade head`): **PASSED**

---

## 4. Hasil Uji Instalasi Lingkungan Baru (Clean Virtual Environment)

Pengujian dilakukan dengan mengekstrak `FINAL_SUBMISSION_SIAKAD.zip` ke direktori terisolasi dan membuat *virtual environment* sementara (`temp_venv`) tanpa menyentuh environment development utama:

| Tahap Uji Instalasi | Perintah / Metode Uji | Hasil Aktual | Status |
|---|---|---|---|
| **1. Ekstraksi Paket ZIP** | Ekstrak `FINAL_SUBMISSION_SIAKAD.zip` (`235 KB`) ke folder bersih | Seluruh **134 file & 16 folder** terekstrak utuh (`zipfile.testzip() == None`) | **PASS** |
| **2. Pembuatan `temp_venv` & Instalasi Dependency** | `python -m venv temp_venv` & `pip install -r requirements.txt` | Seluruh 14 dependency terinstal tanpa error | **PASS** |
| **3. Konfigurasi `.env`** | Salin `.env.example` $\rightarrow$ `.env` | Konfigurasi `DATABASE_URL`, `SECRET_KEY`, `WEBHOOK_SECRET` terbaca | **PASS** |
| **4. Migrasi Alembic pada DB Baru Kosong** | `python -m alembic upgrade head` (`fresh_install.db`) | 8 revisi berjalan berurutan (`c0b4e3a8c963` $\rightarrow$ `b7e4c1d9a204`), membentuk **23 tabel** | **PASS** |
| **5. Verifikasi Seed Data Otomatis** | Query tabel referensi pada `fresh_install.db` | `skala_nilai=5`, `program_studi=2`, `jalur_masuk=3`, `payment_method=4`, `app_user=3` | **PASS** |
| **6. Menjalankan FastAPI, Swagger, & Dashboard** | Probe HTTP ke `/`, `/docs`, `/openapi.json`, `/dashboard`, `/grades-ui`, `/finance-dashboard`, `/api/billing/scheduler/status` | Seluruh endpoint merespons `200 OK`, `APScheduler` berstatus `is_running: True` (2 cron jobs aktif) | **PASS** |
| **7. Menjalankan Test Suite di `temp_venv`** | `temp_venv\Scripts\python.exe -B -m pytest -q` | **`357 passed in 15.49s`** | **PASS** |

---

## 5. Struktur Paket `FINAL_SUBMISSION_SIAKAD.zip`

```text
FINAL_SUBMISSION_SIAKAD.zip
└── FINAL_SUBMISSION/
    ├── alembic/
    │   ├── versions/                  # 8 file revisi migrasi Alembic (Minggu 3–11)
    │   ├── README
    │   ├── env.py
    │   └── script.py.mako
    ├── app/
    │   ├── models/                    # 11 file model SQLAlchemy
    │   ├── observers/                 # 3 file implementasi Observer Pattern
    │   ├── routers/                   # 9 file router FastAPI (47 endpoint REST & UI)
    │   ├── schemas/                   # 5 file Pydantic schema
    │   ├── services/                  # 12 file service + krs/validators.py
    │   │   └── krs/
    │   ├── utils/                     # 3 file utilitas (PDF generator & security)
    │   ├── database.py
    │   └── main.py
    ├── docs/
    │   ├── adr/                       # 11 dokumen ADR (ADR-001 s/d ADR-013)
    │   ├── diagram/                   # Sequence diagram & dokumentasi visual
    │   ├── week11/                    # Dokumentasi Keuangan & Webhook Minggu 11
    │   └── week9-10/                  # Dokumentasi Nilai, GPA, & PDF Transkrip Minggu 9–10
    ├── tests/                         # 27 file test otomatis + conftest.py (357 test cases)
    ├── .env.example
    ├── AI_USAGE_LOG.md
    ├── API_DOCUMENTATION.md
    ├── CLEANUP_AUDIT.md
    ├── CLEANUP_REPORT.md
    ├── DATABASE_DOCUMENTATION.md
    ├── FINAL_CLEANUP_REPORT.md
    ├── FINAL_SUBMISSION.md
    ├── FINAL_TEST_REPORT.md
    ├── INSTALLATION_GUIDE.md
    ├── OPAR.md
    ├── PROJECT_SUBMISSION_CHECKLIST.md
    ├── PR_TEMPLATE.md
    ├── README.md
    ├── STRUKTUR_PROJECT.txt
    ├── USER_GUIDE.md
    ├── alembic.ini
    ├── pmb.db
    ├── pytest.ini
    └── requirements.txt
```

---

## 6. Matriks Pemenuhan Requirement Dosen Minggu 3–11 & P1–P5

| Minggu / Prioritas | Kriteria Utama Dosen | Bukti Implementasi & Pengujian | Status |
|---|---|---|---|
| **Minggu 3** | Skema 3 tabel PMB + constraint SQLAlchemy 2.0, migrasi Alembic upgrade & downgrade, `POST /api/pmb/register`, tolak email ganda (`409`), AI Usage Log. | `app/models/calon_mahasiswa.py`, `app/routers/pmb.py`, `tests/test_pmb_register.py`, `AI_USAGE_LOG.md` | **VERIFIED PASS** |
| **Minggu 4** | `PUT approve/reject`, format NIM terdokumentasi, `generate_nim` aman *race condition* & *idempotent*, `GET status & stats (GROUP BY)`, coverage $\ge 80\%$, OPAR & PR Template. | `app/services/pmb_service.py`, `tests/test_pmb_week4.py`, `README.md`, `OPAR.md`, `PR_TEMPLATE.md` | **VERIFIED PASS** |
| **Minggu 5** | Model + migrasi KRS (`krs`, `krs_detail`, `prerequisite`, `skala_nilai`), `KRSManager` (`add_course`, `remove_course`, `validate_krs`), 4 validator *Chain of Responsibility*, query prasyarat `NOT EXISTS` + `EXPLAIN QUERY PLAN`, ADR. | `app/services/krs/validators.py`, `app/services/krs_manager.py`, `docs/adr/ADR-001*.md`, `docs/adr/ADR-002*.md` | **VERIFIED PASS** |
| **Minggu 6** | `KRSStatus` State Machine (`DRAFT`, `SUBMITTED`, `APPROVED`, `REVISION`), tabel `krs_transition`, validasi kepemilikan Dosen PA (`403`/`409`) dalam satu transaksi, `Hypothesis` 1.000x, 12 transisi ilegal, CSP `KRSRecommender`. | `app/services/krs_state_machine.py`, `app/services/krs_recommender.py`, `tests/test_krs_property.py`, `tests/test_state_machine.py` | **VERIFIED PASS** |
| **Minggu 7–8** | Deteksi konflik 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`) dengan interval `[start, end)`, cek kapasitas ruangan, *Observer Pattern* (`Student`, `Lecturer`, `Admin`), 3 alternatif jadwal CSP, integrasi `needs_review` KRS, Conflict Resolver UI (`/dashboard`). | `app/services/conflict_detector.py`, `app/services/scheduling_service.py`, `app/services/rescheduling_service.py`, `app/observers/`, `tests/test_scheduling.py` | **VERIFIED PASS** |
| **Minggu 9–10** | Konversi nilai A/B/C/D/E, validasi presensi $\ge 75\%$, perhitungan IPS & IPK (pengulangan MK ambil nilai tertinggi), Audit Trail otomatis (Trigger `trg_grade_history_update` & View `v_grade_history`), PDF Transkrip Resmi (`ReportLab` + Logo + TTD Dekan), $\ge 10$ kasus uji IPK, UI `/grades-ui`. | `app/services/grade_service.py`, `app/services/gpa_calculator.py`, `app/utils/pdf_generator.py`, `tests/test_transcript_service.py` (14 kasus uji) | **VERIFIED PASS** |
| **Minggu 11** | Generate billing semester otomatis berdasarkan tarif prodi, jatuh tempo 14 hari, denda keterlambatan, scheduled job, `process_payment` atomic, Webhook HMAC-SHA256 & idempotency, blokir KRS bagi mahasiswa `overdue`, Dashboard Keuangan (`/finance-dashboard`) & AI Financial Report JSON. | `app/services/billing_service.py`, `app/services/payment_service.py`, `app/services/scheduler_service.py`, `tests/test_payment_webhook.py`, `tests/test_krs_finance_integration.py` | **VERIFIED PASS** |
| **Perbaikan P1–P5** | **P1:** `APScheduler` (`BackgroundScheduler` + `CronTrigger` + FastAPI `lifespan`)<br>**P2:** Konsistensi nilai `D (1.0)` lulus di IPK vs minimal `C (2.0)` di prasyarat<br>**P3:** `JadwalKuliah` sebagai sumber aktual validasi & invalidasi KRS<br>**P4:** *True multi-thread concurrency* NIM (`BEGIN IMMEDIATE` + `ThreadPoolExecutor` 8 worker)<br>**P5:** Form Edit Nilai (`PUT /api/grades/update/{grade_id}` + alasan wajib) di `/grades-ui`. | `tests/test_audit_week3_to_11.py` (seluruh 9 pengujian integrasi P1–P5 **PASSED**) | **VERIFIED PASS** |
