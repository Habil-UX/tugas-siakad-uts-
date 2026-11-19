# LAPORAN AKHIR PEMBERSIHAN REPOSITORY (`CLEANUP_REPORT.md`)
**Project:** Sistem Informasi Akademik (SIAKAD) — Minggu 3–11  
**Tanggal Pembersihan:** 16 November 2026  
**Auditor:** Senior Software Engineer & Software Repository Auditor  
**Referensi Audit Awal:** `CLEANUP_AUDIT.md`

---

## 1. Total Jumlah File Sebelum Pembersihan

Berdasarkan audit rekursif awal pada repository (di luar direktori virtual environment `venv/` yang berisi 4.000 file internal paket Python):
- **Total File Project (Sebelum Cleanup):** **725 file**
- **Total Folder Project (Sebelum Cleanup):** **58 folder**

Rincian distribusi 725 file sebelum pembersihan:
- **535 file (`73,79%`)** teridentifikasi sebagai `SAFE TO DELETE` (cache bytecode, cache pytest/hypothesis, report pengujian usang, dan snapshot sementara sesi audit).
- **9 file (`1,24%`)** teridentifikasi sebagai `NEEDS CONFIRMATION` (file backup database `.db` lama, file `pmb_final.db` berukuran 0 byte, dan draft ADR sekunder).
- **181 file (`24,97%`)** teridentifikasi sebagai `MUST KEEP` (seluruh source code aktif `app/`, migrasi `alembic/`, test suite `tests/`, database utama `pmb.db`, konfigurasi, dokumentasi utama & ADR, serta laporan coverage terbaru `htmlcov/`).

---

## 2. Total Jumlah File Setelah Pembersihan

Setelah penghapusan seluruh item pada kategori `SAFE TO DELETE` (535 file dan 40 folder) serta penambahan 2 dokumen laporan audit/cleanup (`CLEANUP_AUDIT.md` dan `CLEANUP_REPORT.md`):
- **Total File Dihapus:** **535 file** (beserta **40 folder** sementara/cache)
- **Total File Project Tersisa (Sebelum Penambahan Dokumen Audit):** **190 file** (`181 MUST KEEP` + `9 NEEDS CONFIRMATION`)
- **Total File Project Akhir (Termasuk `CLEANUP_AUDIT.md` & `CLEANUP_REPORT.md`):** **192 file**
- **Total Folder Project Akhir (Di Luar `venv/`):** **18 folder** (turun dari 58 folder, pengurangan **68,97%** direktori)

---

## 3. Daftar Lengkap File & Folder yang Dihapus

Seluruh **535 file** dan **40 folder** yang dihapus berasal **100% dari kategori `SAFE TO DELETE`** (dan telah diarsipkan terlebih dahulu ke direktori scratch sistem sebelum dihapus):

| No | Path File / Direktori yang Dihapus | Jumlah File | Jumlah Folder | Kategori Audit |
|---:|---|---:|---:|---|
| 1 | `backup_pra_audit_20261116/` *(seluruh isi rekursif)* | 186 | 15 | Snapshot sementara sesi kerja sebelum audit |
| 2 | `backup_pra_p1_p5_20261116/` *(seluruh isi rekursif)* | 189 | 15 | Snapshot sementara sesi kerja sebelum perbaikan P1–P5 |
| 3 | `reports/` (`reports/htmlcov/*` & `reports/junit.xml`) | 51 | 2 | Laporan coverage & JUnit usang dari tahap Minggu 4 |
| 4 | `.pytest_cache/` (`CACHEDIR.TAG`, `README.md`, `v/cache/*`) | 5 | 3 | Cache internal eksekusi `pytest` |
| 5 | `.hypothesis/` (`examples/*`) | 10 | 2 | Database cache contoh properti `Hypothesis` |
| 6 | `__pycache__/` *(di `app/`, `app/models/`, `app/observers/`, `app/routers/`, `app/schemas/`, `app/services/`, `app/services/krs/`, `app/utils/`, `alembic/`, `alembic/versions/`, `tests/`)* | 94 | 11 | Bytecode cache Python (`.pyc`) yang otomatis dibuat ulang oleh interpreter |
| **TOTAL** | **Seluruh Item `SAFE TO DELETE`** | **535** | **40** *(termasuk subfolder)* | **`SAFE TO DELETE`** |

> **Catatan Keamanan:** Tidak ada satu pun file dari kategori `MUST KEEP` (181 file) maupun `NEEDS CONFIRMATION` (9 file) yang dihapus.

---

## 4. Alasan Penghapusan Setiap File

1. **`backup_pra_audit_20261116/` (186 file) & `backup_pra_p1_p5_20261116/` (189 file)**
   - **Alasan:** Kedua folder ini merupakan salinan sementara (*working snapshot*) yang dibuat pada sesi pengerjaan 16 November 2026 sebelum audit dan sebelum implementasi P1–P5. Karena seluruh perbaikan P1–P5 kini telah terverifikasi lulus 100% (357/357 test passed, 99% coverage) dan menjadi *baseline* utama project, kedua salinan lama yang berisi kode sebelum perbaikan tersebut menjadi redundan dan membebani ukuran repository.
2. **`reports/htmlcov/*` & `reports/junit.xml` (51 file)**
   - **Alasan:** Berisi hasil laporan *code coverage* dan *JUnit XML* lama dari tahap awal (Minggu 4, hanya mencakup sebagian kecil modul). Laporan *coverage* resmi dan lengkap untuk Minggu 3–11 telah tersedia di direktori root `htmlcov/` (mencakup seluruh 47 file modul aplikasi dengan 99% coverage).
3. **`.pytest_cache/` (5 file) & `.hypothesis/` (10 file)**
   - **Alasan:** Merupakan direktori cache runtime yang dibuat otomatis oleh `pytest` dan `hypothesis` saat pengujian dijalankan. Tidak diimpor oleh kode mana pun dan aman dibersihkan.
4. **Seluruh direktori `__pycache__/*.pyc` di luar `venv/` (94 file)**
   - **Alasan:** Merupakan kompilasi bytecode Python sementara (`.cpython-311.pyc` dan `.pytest-8.3.5.pyc`), termasuk sisa bytecode dari script verifikasi sementara yang sudah tidak ada.

---

## 5. Daftar Dependency yang Dihapus atau Dipertahankan

Berdasarkan pemeriksaan silang antara `requirements.txt` dengan seluruh *import statement*, konfigurasi runtime, migrasi database, dan *test runner*:
- **Dependency yang Dihapus:** **Tidak ada (0 dependency dihapus)** karena seluruh paket terbukti aktif digunakan.
- **Dependency yang Dipertahankan (`requirements.txt` — 14 paket):**

| No | Nama Paket & Versi | Status | Bukti Penggunaan Aktual dalam Project |
|---:|---|---|---|
| 1 | `fastapi==0.115.11` | **DIPERTAHANKAN** | Framework utama REST API (`app/main.py`, seluruh router `app/routers/*.py`) |
| 2 | `uvicorn==0.34.0` | **DIPERTAHANKAN** | ASGI server untuk menjalankan aplikasi FastAPI |
| 3 | `sqlalchemy==2.0.39` | **DIPERTAHANKAN** | ORM, engine database, transaksi, dan model (`app/database.py`, `app/models/*.py`) |
| 4 | `alembic==1.15.1` | **DIPERTAHANKAN** | Migrasi skema database (`alembic/env.py`, `alembic/versions/*.py`) |
| 5 | `pydantic==2.10.6` | **DIPERTAHANKAN** | Validasi request/response schema (`app/schemas/*.py`) |
| 6 | `pydantic[email]==2.10.6` | **DIPERTAHANKAN** | Validasi tipe `EmailStr` pada `app/schemas/pmb.py` |
| 7 | `email-validator==2.2.0` | **DIPERTAHANKAN** | Backend validator yang dibutuhkan oleh `pydantic.EmailStr` |
| 8 | `python-dotenv==1.0.1` | **DIPERTAHANKAN** | Memuat variabel environment `.env` pada `app/database.py` |
| 9 | `pytest==8.3.5` | **DIPERTAHANKAN** | Test runner utama untuk 357 unit, integration, concurrency, dan property tests |
| 10 | `pytest-cov==6.0.0` | **DIPERTAHANKAN** | Plugin kalkulasi code coverage (`--cov=app`) |
| 11 | `httpx==0.28.1` | **DIPERTAHANKAN** | Dependency wajib `fastapi.testclient.TestClient` pada pengujian endpoint |
| 12 | `hypothesis==6.130.5` | **DIPERTAHANKAN** | Property-based testing (1.000+ skenario otomatis) di `tests/test_krs_property.py` & `tests/test_week5_6_Anchor.py` |
| 13 | `reportlab==4.4.10` | **DIPERTAHANKAN** | Engine pembuat dokumen PDF Transkrip Akademik (`app/utils/pdf_generator.py`) |
| 14 | `APScheduler==3.11.3` | **DIPERTAHANKAN** | Penjadwalan otomatis `BackgroundScheduler` + `CronTrigger` untuk tagihan semester & reminder tunggakan (`app/services/scheduler_service.py`) |

---

## 6. Perubahan Struktur Folder

Struktur direktori project menjadi jauh lebih bersih, terorganisir, dan bebas dari direktori duplikat/cache (berkurang dari **58 folder** menjadi **18 folder** di luar `venv/`):

```text
TUGAS PMB/
├── alembic/
│   ├── versions/                  # 9 file revisi migrasi Alembic berurutan (Minggu 3–11)
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── models/                    # 11 file model SQLAlchemy (22 tabel aplikasi)
│   ├── observers/                 # 3 file implementasi Observer Pattern jadwal
│   ├── routers/                   # 9 file router FastAPI (47 endpoint REST & UI)
│   ├── schemas/                   # 5 file Pydantic schema
│   ├── services/                  # 12 file business logic service + krs/validators.py
│   │   └── krs/
│   ├── utils/                     # 3 file utilitas (PDF generator & JWT/HMAC/PBKDF2 security)
│   ├── database.py
│   └── main.py
├── database_backup/               # Disimpan sementara (NEEDS CONFIRMATION)
├── docs/
│   ├── adr/                       # Architecture Decision Records (ADR-001 s/d ADR-011)
│   ├── diagram/                   # Sequence diagram & dokumentasi visual
│   ├── week11/                    # Dokumentasi Keuangan & Webhook Minggu 11
│   └── week9-10/                  # Dokumentasi Nilai, GPA, & PDF Transkrip Minggu 9–10
├── htmlcov/                       # Laporan HTML Code Coverage terbaru (99%)
├── tests/                         # 27 file pengujian otomatis (357 test cases)
├── .coverage
├── .env
├── .env.example
├── AI_USAGE_LOG.md
├── CLEANUP_AUDIT.md
├── CLEANUP_REPORT.md
├── FINAL_SUBMISSION.md
├── PR_TEMPLATE.md
├── README.md
├── STRUKTUR_PROJECT.txt           # Diperbarui sesuai struktur bersih pasca-cleanup
├── alembic.ini
├── pmb.db                         # Database SQLite utama (aktif)
├── pmb_backup_*.db / pmb_final.db # Disimpan sementara (NEEDS CONFIRMATION)
├── pytest.ini
└── requirements.txt
```

---

## 7. Hasil Regression Test Setelah Pembersihan

Seluruh pengujian regresi dijalankan kembali setelah pembersihan selesai dengan hasil **100% LULUS tanpa error**:

1. **Unit, Integration, Concurrency & Property-Based Tests (`pytest`):**
   - **Total Test Dijalankan:** `357 items`
   - **Passed:** `357 passed` (`100%`)
   - **Failed / Error:** `0 failed`, `0 error`
   - **Waktu Eksekusi:** `33.81s`
2. **Verifikasi Import Seluruh Modul Python (`pkgutil.walk_packages`):**
   - Seluruh **25 paket/modul** di bawah `app.*` berhasil diimpor tanpa `ImportError` atau `ModuleNotFoundError`.
3. **Verifikasi Koneksi Database & Migrasi Alembic:**
   - Koneksi ke `pmb.db` berhasil (`23 tabel` termasuk `alembic_version`).
   - Revisi aktif database (`b7e4c1d9a204`) sama persis dengan `alembic heads` (`b7e4c1d9a204`).
4. **Verifikasi Endpoint API, Swagger, & Halaman Frontend:**
   - `GET /docs` (Swagger UI) $\rightarrow$ `200 OK`
   - `GET /openapi.json` (47 terdaftar paths) $\rightarrow$ `200 OK`
   - `GET /dashboard` (UI Penjadwalan & Monitoring Akademik) $\rightarrow$ `200 OK`
   - `GET /grades-ui` (UI Manajemen Nilai + Form Edit Nilai Mahasiswa & Transkrip PDF) $\rightarrow$ `200 OK`
   - `GET /finance-dashboard` (UI Dashboard Keuangan SPP & Webhook) $\rightarrow$ `200 OK`
   - `GET /api/pmb/stats` (Modul PMB) $\rightarrow$ `200 OK`
   - `GET /api/schedules`, `GET /api/schedules/conflicts`, `GET /api/admin/scheduling/dashboard` (Modul Jadwal & Observer) $\rightarrow$ `200 OK`
   - `GET /api/billing/dashboard?semester=2025-1`, `GET /api/billing/ai-report?semester=2025-1`, `GET /api/billing/scheduler/status` (`running: True`) $\rightarrow$ `200 OK`

---

## 8. Coverage Setelah Pembersihan

Hasil pengukuran `pytest --cov=app --cov-report=term-missing --cov-report=html` setelah pembersihan:

- **Total Statements:** `2.374`
- **Missed Statements:** `33`
- **Total Code Coverage:** **`99%`** (sama persis dengan baseline sebelum pembersihan)
- **40 dari 47 file modul** mencapai **`100%` coverage**, dan seluruh modul lainnya berada di rentang **`94%–99%` coverage**.

---

## 9. Daftar File `NEEDS CONFIRMATION` (Menunggu Persetujuan User)

Sesuai aturan keselamatan kerja, **9 file berikut TIDAK DIHAPUS** dan tetap dipertahankan di tempatnya hingga Anda memberikan instruksi eksplisit apabila ingin menghapusnya:

| No | Path File | Ukuran | Alasan Masuk Kategori `NEEDS CONFIRMATION` | Rekomendasi |
|---:|---|---:|---|---|
| 1 | `pmb_final.db` | 0 B | File database kosong (0 byte) yang tidak direferensikan oleh `.env`, `app/`, maupun `tests/`. | Aman dihapus jika tidak diperlukan. |
| 2 | `pmb_backup_before_migration.db` | 40.960 B | Backup database lama sebelum migrasi awal. | Opsional dihapus / dipindahkan ke arsip luar. |
| 3 | `pmb_backup_before_dosen_pa.db` | 45.056 B | Backup database sebelum penambahan kolom `dosen_pa_id`. | Opsional dihapus / dipindahkan ke arsip luar. |
| 4 | `pmb_backup_before_week11_20261115_100248.db` | 155.648 B | Backup database sebelum implementasi modul Keuangan Minggu 11. | Opsional dihapus / dipindahkan ke arsip luar. |
| 5 | `pmb_backup_20261115_153131.db` | 204.800 B | Backup database tanggal 15 November 2026. | Opsional dihapus / dipindahkan ke arsip luar. |
| 6 | `pmb_backup_before_audit_20261116.db` | 204.800 B | Backup database sebelum audit final 16 November 2026 (identik SHA-256 dengan `pmb_backup_20261115_153131.db`). | Simpan 1 backup terbaru atau pindahkan ke luar repo. |
| 7 | `database_backup/pmb_20261115_095651.db` | 155.648 B | Backup database di dalam subfolder `database_backup/`. | Opsional dihapus / dipindahkan ke arsip luar. |
| 8 | `database_backup/pmb_before_week7_8_clean.db` | 45.056 B | Backup database sebelum Minggu 7–8 (identik SHA-256 dengan `pmb_backup_before_dosen_pa.db`). | Opsional dihapus / dipindahkan ke arsip luar. |
| 9 | `docs/adr/ADR-011-Observer-Pattern.md` | 1.662 B | Dokumen ADR tambahan mengenai Observer Pattern (topik serupa juga dibahas lebih lengkap di `docs/adr/ADR-002-observer-pattern-schedule-notification.md`). | Disarankan tetap disimpan sebagai pelengkap dokumentasi arsitektur, atau dihapus jika hanya ingin satu ADR Observer Pattern. |

---

## 10. Kesimpulan Kondisi Akhir Project

1. **Kondisi Repository Bersih & Rapi:** Sebanyak **535 file sementara/cache/snapshot usang** dan **40 folder** telah dibersihkan secara aman, memangkas jumlah file non-venv sebesar **73,79%** tanpa menyentuh satu pun file penting.
2. **Integritas Aplikasi 100% Terjaga:** Seluruh fitur Minggu 3–11 beserta hasil perbaikan P1–P5 berjalan normal tanpa regresi (**357 test passed, 0 failed, 99% coverage**).
3. **Siap Dikumpulkan / Di-deploy:** Struktur folder (`STRUKTUR_PROJECT.txt`), dependency (`requirements.txt`), database utama (`pmb.db`), migrasi Alembic, REST API, UI Dashboard, dan seluruh dokumentasi tugas dosen berada dalam kondisi prima.
