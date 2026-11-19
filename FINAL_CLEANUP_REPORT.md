# LAPORAN AKHIR PEMBERSIHAN TAHAP LANJUT (`FINAL_CLEANUP_REPORT.md`)
**Project:** Sistem Informasi Akademik (SIAKAD) — Minggu 3–11  
**Tanggal Eksekusi & Validasi:** 17 November 2026  
**Auditor:** Senior Software Engineer & Software Repository Auditor  
**Pendahulu:** `CLEANUP_AUDIT.md` & `CLEANUP_REPORT.md`

---

## 1. Ringkasan Eksekutif & Laporan Rekomendasi (9 File `NEEDS CONFIRMATION`)

Berdasarkan pemeriksaan teknis mendalam terhadap 9 item yang sebelumnya berstatus `NEEDS CONFIRMATION`, berikut adalah hasil analisis dan tindakan yang diambil sesuai aturan keselamatan:

| No | File / Item yang Diperiksa | Hasil Pemeriksaan Teknis | Rekomendasi & Tindakan Eksekusi | Status Akhir |
|---:|---|---|---|---|
| 1 | `pmb_final.db` | Berukuran **0 byte**, 0 tabel, tidak memiliki revisi Alembic, tidak direferensikan oleh `.env`, `alembic.ini`, `app/`, `tests/`, maupun konfigurasi deployment. | **Hapus Permanen** | **DIHAPUS** |
| 2 | `pmb_backup_before_migration.db` | Valid (`PRAGMA integrity_check = ok`), `262.144` B, 18 tabel, revisi `95417f7b9188`, seluruh 17 tabel domain kosong (0 baris). | **Arsipkan** ke `archive_database_backup/` (tidak dihapus tanpa persetujuan) | **DIARSIPKAN** |
| 3 | `pmb_backup_before_week11_20261115_100248.db` | Valid (`PRAGMA integrity_check = ok`), `274.432` B, 19 tabel, revisi `0f9e48bbab1f`, seluruh 18 tabel domain kosong (0 baris). | **Arsipkan** ke `archive_database_backup/` (tidak dihapus tanpa persetujuan) | **DIARSIPKAN** |
| 4 | `pmb_backup_before_dosen_pa.db` | Valid (`PRAGMA integrity_check = ok`), `319.488` B, 22 tabel, revisi `50747fbd5ef0`, berisi 12 baris data awal. | **Arsipkan** ke `archive_database_backup/` (tidak dihapus tanpa persetujuan) | **DIARSIPKAN** |
| 5 | `pmb_backup_20261115_153131.db` | Valid (`PRAGMA integrity_check = ok`), `327.680` B, 23 tabel (termasuk tabel sementara `_alembic_tmp_calon_mahasiswa`), revisi `50747fbd5ef0`, isi data logis identik dengan `pmb_backup_before_dosen_pa.db`. | **Arsipkan** ke `archive_database_backup/` (tidak dihapus tanpa persetujuan) | **DIARSIPKAN** |
| 6 | `pmb_backup_before_audit_20261116.db` | Valid (`PRAGMA integrity_check = ok`), `327.680` B, 22 tabel, revisi `a8c2d6e9f103`, berisi 22 baris data lengkap pra-audit across 14 tabel. | **Arsipkan** ke `archive_database_backup/` sebagai backup historis pra-audit | **DIARSIPKAN** |
| 7 | `database_backup/pmb_backup_minggu7_8_20261115_195247.db` *(catatan: pada laporan sebelumnya sempat tertulis nama estimasi `pmb_20261115_095651.db` / `pmb_before_week7_8_clean.db`)* | Valid (`PRAGMA integrity_check = ok`), `327.680` B, 22 tabel, revisi `a8c2d6e9f103`, **100% identik secara skema dan isi data logis** dengan `pmb_backup_before_audit_20261116.db`. | **Arsipkan** ke `archive_database_backup/` dan hapus folder kosong `database_backup/` | **DIARSIPKAN** |
| 8 | `docs/adr/ADR-011-Observer-Pattern.md` | Duplikat topik dengan `docs/adr/ADR-010-Observer-Pattern.md` sekaligus bentrok penomoran dengan `docs/adr/ADR-011-Strategi-Deteksi-Konflik.md`. Tidak dirujuk oleh `README.md` atau dokumen lain. | **Gabungkan** informasi unik (*loose coupling* & contoh kanal WhatsApp) ke `ADR-010-Observer-Pattern.md`, lalu **Hapus** file duplikat | **DIGABUNG & DIHAPUS** |
| 9 | `STRUKTUR_PROJECT.txt` | File dokumentasi pohon direktori yang dirujuk di `README.md`. | **Pertahankan & Perbarui** sesuai struktur akhir pasca-cleanup | **DIPERBARUI** |

---

## 2. Pemeriksaan Database Kosong (`pmb_final.db`)

- **Path:** `pmb_final.db`
- **Ukuran Aktual:** `0 byte`
- **Waktu Modifikasi (`mtime`):** `2026-11-10 14:27:40`
- **SHA-256:** `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (hash standar file kosong)
- **Referensi Konfigurasi & Source Code:**
  - `.env` dan `.env.example` menggunakan `DATABASE_URL=sqlite:///./pmb.db`.
  - `alembic.ini` menggunakan `sqlalchemy.url = sqlite:///./pmb.db`.
  - Pencarian teks menyeluruh pada `app/`, `alembic/`, `tests/`, dan `docs/` menghasilkan **0 referensi** ke `pmb_final.db`.
- **Keputusan:** **Dihapus permanen** karena terbukti 0 byte dan tidak digunakan di bagian mana pun.

---

## 3. Pemeriksaan Mendalam Database Backup & Pengarsipan

### 3.1. Tabel Audit Teknis Seluruh File Database (`.db`)

| No | Nama File Database | Ukuran (Byte) | Waktu Modifikasi (`mtime`) | `PRAGMA integrity_check` | Jml Tabel | Revisi Alembic | SHA-256 | Ringkasan Isi Data Penting |
|---:|---|---:|---|---|---:|---|---|---|
| 0 | **`pmb.db` (DB Utama Aktif)** | `356.352` | `2026-11-16 20:46:11` | `ok` | **23** | **`b7e4c1d9a204` (HEAD)** | `3e0f65d6895191dd...ceda0140` | **Lengkap (Minggu 3–11 + P1–P5):** `app_user: 3`, `billing: 2`, `calon_mahasiswa: 3`, `dosen: 1`, `jadwal_kuliah: 1`, `jalur_masuk: 3`, `krs: 1`, `krs_detail: 3`, `krs_transition: 4`, `matakuliah: 3`, `nim_sequences: 1`, `notification_log: 3`, `payment_method: 4`, `program_studi: 2`, `ruangan: 1`, `schedule_change_log: 1`, `skala_nilai: 5`. |
| 1 | `pmb_backup_pre_final_cleanup_20261117.db` *(baru dibuat)* | `356.352` | `2026-11-16 20:46:11` | `ok` | **23** | **`b7e4c1d9a204` (HEAD)** | `3e0f65d6895191dd...ceda0140` | **100% Identik Byte-for-Byte (SHA-256 sama)** dengan `pmb.db` utama sebelum cleanup akhir dijalankan. |
| 2 | `pmb_backup_minggu7_8_20261115_195247.db` | `327.680` | `2026-11-15 19:52:47` | `ok` | **22** | `a8c2d6e9f103` | `f4c060ab86c0fa0b...0dee6aa9` | **100% Identik Secara Data Logis** dengan `pmb_backup_before_audit_20261116.db` (`calon_mahasiswa: 3`, `dosen: 1`, `jadwal_kuliah: 1`, `krs: 1`, `krs_detail: 3`, `krs_transition: 4`, `matakuliah: 3`, `notification_log: 3`, `ruangan: 1`, `schedule_change_log: 1`). |
| 3 | `pmb_backup_before_audit_20261116.db` | `327.680` | `2026-11-15 19:28:34` | `ok` | **22** | `a8c2d6e9f103` | `c76a8f8159195a15...aa4d0bc0` | **100% Identik Secara Data Logis** dengan `pmb_backup_minggu7_8_20261115_195247.db` (hanya berbeda pada header halaman internal SQLite). |
| 4 | `pmb_backup_20261115_153131.db` | `327.680` | `2026-11-15 15:29:35` | `ok` | **23** | `50747fbd5ef0` | `5f0f22eda2f24f17...30257675` | Isi data domain **100% identik** dengan `pmb_backup_before_dosen_pa.db`, namun memiliki tabel sisa migrasi `_alembic_tmp_calon_mahasiswa` (0 baris). |
| 5 | `pmb_backup_before_dosen_pa.db` | `319.488` | `2026-11-15 14:43:42` | `ok` | **22** | `50747fbd5ef0` | `5ebd5458e5b8fffc...0722ef13` | Berisi data tahap awal (`calon_mahasiswa: 3`, `jalur_masuk: 1`, `krs: 1`, `krs_detail: 1`, `matakuliah: 3`, `nim_sequences: 1`, `payment_method: 2`, `program_studi: 1`). |
| 6 | `pmb_backup_before_week11_20261115_100248.db` | `274.432` | `2026-11-10 19:35:57` | `ok` | **19** | `0f9e48bbab1f` | `ffaf68600595747f...2eefc22c` | Skema kosong (seluruh 18 tabel domain berisi `0 baris`; hanya `alembic_version` berisi 1 baris). |
| 7 | `pmb_backup_before_migration.db` | `262.144` | `2026-11-10 14:03:19` | `ok` | **18** | `95417f7b9188` | `5a7d3899535d3a21...b2cac577` | Skema kosong (seluruh 17 tabel domain berisi `0 baris`; hanya `alembic_version` berisi 1 baris). |

### 3.2. Identifikasi Backup Terbaru & Paling Lengkap
1. **Backup Terbaru & Paling Lengkap (Revisi `b7e4c1d9a204` — Head Minggu 3–11 + P1–P5):**
   - `archive_database_backup/pmb_backup_pre_final_cleanup_20261117.db` (`356.352` byte, 23 tabel, `PRAGMA integrity_check = ok`).
2. **Backup Historis Paling Lengkap Pra-Audit P1–P5 (Revisi `a8c2d6e9f103`):**
   - `archive_database_backup/pmb_backup_minggu7_8_20261115_195247.db` dan `archive_database_backup/pmb_backup_before_audit_20261116.db` (`327.680` byte, 22 tabel, `PRAGMA integrity_check = ok`).

### 3.3. Tindakan Pengarsipan Sesuai Aturan
- Seluruh file backup valid dipindahkan dari direktori root dan `database_backup/` ke dalam folder khusus **`archive_database_backup/`** di luar direktori runtime aplikasi (`app/`).
- Folder `database_backup/` lama yang sudah kosong telah dihapus.
- **Tidak ada satu pun backup database valid yang dihapus** (mematuhi aturan *"Jangan menghapus backup database valid tanpa persetujuan"*).
- Database utama `pmb.db` **tidak disentuh dan tidak dimodifikasi** (hash SHA-256 sebelum dan sesudah proses tetap `3e0f65d6895191dd340d1ce993351c3afbb587be2af967f95a31366aceda0140`).

---

## 4. Pemeriksaan & Konsolidasi Dokumentasi ADR

### 4.1. Perbandingan `ADR-011-Observer-Pattern.md` vs Dokumen ADR Utama (`ADR-010-Observer-Pattern.md`)
- Pada direktori `docs/adr/`, dokumentasi utama Observer Pattern untuk notifikasi perubahan jadwal berada di **`docs/adr/ADR-010-Observer-Pattern.md`** (`# ADR-010: Observer Pattern untuk Notifikasi Perubahan Jadwal`, sedangkan `ADR-002` di repository ini digunakan oleh `ADR-002-Query-Prasyarat.md`).
- File **`docs/adr/ADR-011-Observer-Pattern.md`** hanya terdiri dari 7 baris ringkas yang membahas topik yang sama (`ScheduleSubject`, `StudentObserver`, `LecturerObserver`, `AdminObserver`), serta menimbulkan **konflik penomoran ganda (`ADR-011`)** dengan file **`docs/adr/ADR-011-Strategi-Deteksi-Konflik.md`**.
- Pemeriksaan referensi di seluruh file (`README.md`, `FINAL_SUBMISSION.md`, `AI_USAGE_LOG.md`, `docs/`, `app/`, `tests/`) membuktikan **tidak ada tautan** yang mengarah ke `ADR-011-Observer-Pattern.md`.

### 4.2. Penggabungan Informasi Unik & Riwayat Keputusan
- Informasi unik pada `ADR-011-Observer-Pattern.md` (penjelasan eksplisit *Loose coupling* serta contoh kemudahan menambah Observer baru untuk kanal **WhatsApp** di masa depan, ditambah detail pencatatan ke tabel `notification_log`) telah **digabungkan terlebih dahulu** ke dalam **`docs/adr/ADR-010-Observer-Pattern.md`** beserta sub-bagian **Riwayat Keputusan**.
- Setelah penggabungan selesai, file duplikat `docs/adr/ADR-011-Observer-Pattern.md` telah **dihapus** sehingga penomoran di `docs/adr/` menjadi konsisten tanpa duplikasi.

---

## 5. Hasil Validasi Akhir (Pasca-Cleanup)

Seluruh pemeriksaan wajib pada **Tahap 5 — Validasi Akhir** telah dijalankan secara nyata dengan hasil sebagai berikut:

1. **Eksekusi Seluruh Unit, Integration, Concurrency & Property Tests (`pytest`):**
   - Perintah: `.\venv\Scripts\python.exe -B -u -m pytest -v -p no:cacheprovider --no-header --cov=app --cov-report=term-missing --cov-report=html`
   - **Total Test:** `357 collected`
   - **Hasil:** **`357 passed, 0 failed, 0 errors`** (waktu eksekusi: `30.05s`)
2. **Code Coverage (`pytest-cov`):**
   - **Total Statements:** `2.374`
   - **Missed Statements:** `33`
   - **Total Coverage:** **`99%`** (40 dari 47 file modul mencapai `100%` coverage)
3. **Koneksi & Integritas Database Utama (`pmb.db`):**
   - `PRAGMA integrity_check` $\rightarrow$ **`ok`**
   - Jumlah tabel aktif $\rightarrow$ **`23 tabel`**
   - SHA-256 `pmb.db` $\rightarrow$ `3e0f65d6895191dd340d1ce993351c3afbb587be2af967f95a31366aceda0140` (**100% utuh, tidak berubah**)
4. **Revisi Alembic (`alembic current` vs `alembic heads`):**
   - Revisi database aktif: **`b7e4c1d9a204`**
   - Revisi `head` skrip migrasi: **`b7e4c1d9a204`** (`MATCH 100%`)
5. **Pemeriksaan Endpoint API, Swagger, & Halaman Utama UI:**
   - `GET /` $\rightarrow$ `200 OK`
   - `GET /docs` (Swagger UI) & `GET /openapi.json` (47 path terdaftar) $\rightarrow$ `200 OK`
   - `GET /dashboard` (Dashboard Penjadwalan & Monitoring Akademik) $\rightarrow$ `200 OK`
   - `GET /grades-ui` (Manajemen Nilai, Transkrip PDF & Form Edit Nilai Mahasiswa) $\rightarrow$ `200 OK`
   - `GET /finance-dashboard` (Dashboard Keuangan SPP & Webhook) $\rightarrow$ `200 OK`
   - `GET /api/pmb/stats`, `GET /api/schedules`, `GET /api/schedules/conflicts`, `GET /api/admin/scheduling/dashboard`, `GET /api/billing/dashboard?semester=2025-1`, `GET /api/billing/ai-report?semester=2025-1` $\rightarrow$ `200 OK`
6. **Verifikasi Fitur Perbaikan P1–P5:**
   - **P1 (APScheduler):** `GET /api/billing/scheduler/status` mengembalikan `status: "running"`, `is_running: True`, `scheduler_class: "BackgroundScheduler"` dengan 2 job aktif (`overdue_billing_reminder` dan `semester_billing_generator`).
   - **P2 (Konsistensi Nilai D & C):** `GPACalculator.MINIMUM_LULUS == 1.0` (nilai D dihitung lulus pada IPS/IPK/Transkrip) dan `PrerequisiteValidator` tetap mensyaratkan minimal nilai C (`bobot >= 2.0`).
   - **P3 (Integrasi JadwalKuliah $\rightarrow$ KRS):** Perubahan jadwal memvalidasi ulang KRS dari `JadwalKuliah` aktif, menandai `needs_review = True`, mencatat `KrsTransition`, dan mengirim notifikasi.
   - **P4 (True Multi-Thread Concurrency NIM):** Pengujian paralel 8 worker thread (`test_concurrent_nim_generation_multithread_file_db`) **PASSED** tanpa duplikasi NIM atau `OperationalError: database is locked`.
   - **P5 (Form Edit Nilai UI):** Halaman `/grades-ui` memuat form *Edit Nilai Mahasiswa* yang terhubung ke `PUT /api/grades/update/{grade_id}` dengan validasi alasan wajib (`reason`) dan riwayat audit trail.

---

## 6. Struktur Akhir Direktori Project (Bersih & Siap Kumpul)

```text
TUGAS PMB/
├── alembic/
│   ├── versions/                  # 9 file revisi migrasi Alembic (Minggu 3–11)
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── models/                    # 11 file model SQLAlchemy
│   ├── observers/                 # 3 file implementasi Observer Pattern
│   ├── routers/                   # 9 file router FastAPI (47 endpoint)
│   ├── schemas/                   # 5 file Pydantic schema
│   ├── services/                  # 12 file service + krs/validators.py
│   │   └── krs/
│   ├── utils/                     # 3 file utilitas (PDF generator & security)
│   ├── database.py
│   └── main.py
├── archive_database_backup/       # Arsip terpisah berisi 7 backup .db valid (termasuk snapshot HEAD terbaru)
├── docs/
│   ├── adr/                       # 11 dokumen ADR bersih (ADR-010 telah dikonsolidasikan, tanpa duplikat)
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
├── FINAL_CLEANUP_REPORT.md
├── FINAL_SUBMISSION.md
├── PR_TEMPLATE.md
├── README.md
├── STRUKTUR_PROJECT.txt
├── alembic.ini
├── pmb.db                         # Satu-satunya file database aktif di direktori root
├── pytest.ini
└── requirements.txt
```
