# LAPORAN AUDIT SEBELUM PEMBERSIHAN (CLEANUP AUDIT REPORT)
## Project SIAKAD — Minggu 3–11

Laporan ini disusun pada **Tahap 1–3** sebelum eksekusi penghapusan file dilakukan. Seluruh file di dalam workspace (di luar folder `venv/`) yang berjumlah **725 file** dan **94 direktori** telah diperiksa berdasarkan referensi import, pemanggilan fungsi/class, router API, template UI, konfigurasi, migrasi Alembic, dan suite pengujian.

---

## 1. Ringkasan Statistik Audit File (Di Luar `venv/`)

| Indikator | Jumlah | Keterangan |
|---|---:|---|
| **Total File Diperiksa** | **725 file** | Seluruh file di dalam direktori project (tidak termasuk `venv/`) |
| **A. Kategori `SAFE TO DELETE`** | **535 file** | Cache Python (`__pycache__/*.pyc`), `.pytest_cache`, `.hypothesis`, folder snapshot sementara sesi audit (`backup_pra_audit_20261116/`, `backup_pra_p1_p5_20261116/`), dan laporan coverage usang (`reports/coverage/`) |
| **B. Kategori `NEEDS CONFIRMATION`** | **9 file** | 6 file database backup (`.db`), 1 file database 0-byte (`pmb_final.db`), 1 dokumen ADR pendek yang tumpang tindih (`ADR-011-Observer-Pattern.md`), dan 1 file catatan struktur lama (`STRUKTUR_PROJECT.txt`) |
| **C. Kategori `MUST KEEP`** | **181 file** | Seluruh source code `app/` (29 file), migrasi `alembic/` (11 file), `tests/` (29 file), `docs/` (26 file), database utama `pmb.db`, konfigurasi & dokumentasi utama, serta laporan `htmlcov/` aktif (56 file) |

---

## 2. Tabel Klasifikasi Temuan File & Folder

| No | Nama File / Folder | Lokasi | Alasan | Kategori | Risiko |
|---:|---|---|---|---|---|
| 1 | `__pycache__/` & `*.pyc` (termasuk `c0cf20ccd802_*.pyc` yatim) | `app/**/`, `alembic/**/`, `tests/**/` (78 file) | Bytecode cache Python yang dapat dibuat ulang otomatis oleh interpreter; terdapat 1 file `.pyc` revisi lama (`c0cf20ccd802`) yang sudah tidak memiliki file `.py`. | **SAFE TO DELETE** | Rendah (0%) |
| 2 | `.pytest_cache/` | `/.pytest_cache/` (6 file) | Cache internal eksekusi Pytest yang dibuat ulang otomatis saat test dijalankan. | **SAFE TO DELETE** | Rendah (0%) |
| 3 | `.hypothesis/` | `/.hypothesis/` (11 file) | Cache contoh properti Hypothesis yang dibuat ulang otomatis saat property-based test dijalankan. | **SAFE TO DELETE** | Rendah (0%) |
| 4 | `backup_pra_audit_20261116/` | `/backup_pra_audit_20261116/` (193 file) | Folder snapshot sementara sebelum audit awal yang berisi duplikat source code lama (dan sempat memicu `ImportPathMismatchError` pada Pytest jika tidak dikecualikan). | **SAFE TO DELETE** | Rendah (0%) |
| 5 | `backup_pra_p1_p5_20261116/` | `/backup_pra_p1_p5_20261116/` (208 file) | Folder snapshot sementara sebelum implementasi P1–P5 yang berisi duplikat source code di dalam workspace. | **SAFE TO DELETE** | Rendah (0%) |
| 6 | `reports/` (`reports/coverage/*`) | `/reports/` (39 file) | Laporan HTML coverage lama tertanggal 9 November 2026 (Minggu 3–8) yang sudah usang dan digantikan oleh direktori standar `htmlcov/`. | **SAFE TO DELETE** | Rendah (0%) |
| 7 | `pmb_final.db` | `/pmb_final.db` (1 file, 0 bytes) | File database kosong (0 byte) yang tidak direferensikan oleh `.env`, `app/database.py`, maupun `tests/`. | **NEEDS CONFIRMATION** | Rendah (Tidak dihapus tanpa izin) |
| 8 | File Backup Database (`.db`) | `/pmb_backup_*.db` (5 file) & `/database_backup/pmb_backup_*.db` (1 file) | Cadangan historis database SQLite dari tahap pengembangan sebelumnya. Tidak digunakan oleh aplikasi aktif namun berguna sebagai cadangan historis. | **NEEDS CONFIRMATION** | Sedang (Tidak dihapus tanpa izin) |
| 9 | `ADR-011-Observer-Pattern.md` | `/docs/adr/ADR-011-Observer-Pattern.md` (1 file) | Memiliki nomor urut ganda (`ADR-011` dipakai juga oleh `ADR-011-Strategi-Deteksi-Konflik.md`) dan topiknya sudah tercakup lebih lengkap di `ADR-010-Observer-Pattern.md`. | **NEEDS CONFIRMATION** | Rendah (Tidak dihapus tanpa izin) |
| 10 | `STRUKTUR_PROJECT.txt` | `/STRUKTUR_PROJECT.txt` (1 file) | Catatan teks struktur direktori yang dirujuk oleh `README.md`. Dipertahankan dan diperbarui agar sesuai struktur terbaru. | **NEEDS CONFIRMATION / KEEP** | Rendah |
| 11 | Source Code Utama (`app/`) | `/app/` (`main.py`, `database.py`, `models/`, `routers/`, `services/`, `schemas/`, `observers/`, `utils/` — 29 file `.py`) | Seluruh modul inti PMB, KRS, Jadwal, Nilai, Transkrip PDF, Keuangan SPP, APScheduler, dan Autentikasi HMAC. | **MUST KEEP** | Tinggi (Wajib dipertahankan) |
| 12 | Migrasi Database (`alembic/`) | `/alembic/` (`env.py`, `script.py.mako`, `README`, `versions/*.py` — 11 file) | Seluruh 8 revisi migrasi database dari Minggu 3 hingga Minggu 11. | **MUST KEEP** | Tinggi (Wajib dipertahankan) |
| 13 | Suite Pengujian (`tests/`) | `/tests/` (`conftest.py`, `__init__.py`, 27 file `test_*.py` — 29 file) | Seluruh 357 unit, integration, concurrency, dan property-based tests. | **MUST KEEP** | Tinggi (Wajib dipertahankan) |
| 14 | Dokumentasi, ADR & Diagram (`docs/` & Root `.md`) | `/docs/`, `README.md`, `FINAL_SUBMISSION.md`, `AI_USAGE_LOG.md`, `PR_TEMPLATE.md` | Bukti pemenuhan kriteria dokumentasi dosen, ADR, sequence diagram Observer/KRS/Rescheduling, AI Usage Log, dan OPAR. | **MUST KEEP** | Tinggi (Wajib dipertahankan) |
| 15 | Konfigurasi, Environment & DB Utama | `pmb.db`, `.env`, `.env.example`, `alembic.ini`, `pytest.ini`, `requirements.txt`, `venv/` | Konfigurasi runtime aplikasi, database aktif, dan virtual environment Python. | **MUST KEEP** | Tinggi (Wajib dipertahankan) |

---

## 3. Audit Dependency (`requirements.txt`)

Seluruh 14 entri pada `requirements.txt` telah diperiksa terhadap kode sumber dan kebutuhan runtime/plugin:
1. `fastapi==0.109.0` — Framework REST API utama (`app/`). (**DIPERTAHANKAN**)
2. `uvicorn==0.27.0` — ASGI server untuk menjalankan aplikasi. (**DIPERTAHANKAN**)
3. `sqlalchemy==2.0.25` — ORM dan manajemen transaksi database. (**DIPERTAHANKAN**)
4. `alembic==1.13.1` — Migrasi skema database. (**DIPERTAHANKAN**)
5. `pydantic==2.5.3` — Validasi schema request/response. (**DIPERTAHANKAN**)
6. `pydantic-settings==2.1.0` — Manajemen konfigurasi ekosistem FastAPI/Pydantic. (**DIPERTAHANKAN**)
7. `email-validator==2.1.0` — Plugin wajib untuk tipe `EmailStr` pada `app/schemas/pmb.py`. (**DIPERTAHANKAN**)
8. `pytest==7.4.4` — Test runner utama. (**DIPERTAHANKAN**)
9. `httpx==0.26.0` — Dependency wajib `starlette.testclient.TestClient` pada `tests/conftest.py`. (**DIPERTAHANKAN**)
10. `pytest-cov==4.1.0` — Plugin perhitungan code coverage. (**DIPERTAHANKAN**)
11. `hypothesis==6.98.0` — Library property-based testing (1000 kombinasi SKS KRS). (**DIPERTAHANKAN**)
12. `reportlab==4.2.5` — Generator PDF Transkrip Akademik (`app/utils/pdf_generator.py`). (**DIPERTAHANKAN**)
13. `python-dotenv` — Pembaca variabel `.env` pada `app/database.py`. (**DIPERTAHANKAN**)
14. `APScheduler==3.11.3` — Engine `BackgroundScheduler` & `CronTrigger` pada `app/services/scheduler_service.py`. (**DIPERTAHANKAN**)

---

## 4. Potensi Dampak Penghapusan
- Penghapusan seluruh item pada kategori **A (`SAFE TO DELETE` — 535 file)** tidak mengubah satu baris pun kode sumber aplikasi, skema database, migrasi, maupun pengujian, serta memangkas lebih dari 70% file sampah/duplikat di dalam workspace.
- Seluruh item pada kategori **B (`NEEDS CONFIRMATION` — 9 file)** **TIDAK DIHAPUS** dan menunggu konfirmasi Anda.
