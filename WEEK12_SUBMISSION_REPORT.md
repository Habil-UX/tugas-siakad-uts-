# LAPORAN AKHIR PENGUMPULAN MINGGU 12 (`WEEK12_SUBMISSION_REPORT.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 12: Modul Presensi (QR Code)  
**Tanggal Penyelesaian & Verifikasi:** 18 November 2026  
**File Paket ZIP:** `PENGUMPULAN_SIAKAD/MINGGU_12.zip`

---

## 1. Ringkasan Implementasi

Modul Presensi Mahasiswa Berbasis QR Code (Minggu 12) telah berhasil dikembangkan dan diintegrasikan penuh ke dalam arsitektur utama SIAKAD (Minggu 3–11) tanpa merusak fitur existing maupun mengubah ketujuh file ZIP pengumpulan sebelumnya (`MINGGU_3.zip` s/d `MINGGU_11.zip`).

Cakupan implementasi meliputi:
- **Database & Model Presensi:** 4 entitas SQLAlchemy (`AttendanceSession`, `AttendanceQRToken`, `AttendanceRecord`, `AttendanceScanAttempt`) dengan relasi Foreign Key ke `JadwalKuliah`, `CalonMahasiswa`, `Matakuliah`, `KRS`, dan `Dosen`, serta constraint unik anti-duplikat per sesi.
- **QR Generation Service (30%):** Pembuatan gambar PNG QR Code (`qrcode`) yang mengemas token JWT `HS256` (`PyJWT`) dengan `SECRET_KEY` dari environment variable, masa berlaku maksimal 15 menit, `jti` unik, serta validasi kewenangan dosen pengampu.
- **Attendance Recording & Scan Validation (30%):** Validasi berlapis terhadap signature JWT, expiration, `jti`, `session_id`, hari jadwal kuliah, pendaftaran KRS `APPROVED`, pencegahan scan duplikat, serta penentuan status **`HADIR`** ($\le 15$ menit sejak `jam_mulai`), **`TERLAMBAT`** ($15\text{–}30$ menit sejak `jam_mulai`), dan **`DITOLAK`** ($>30$ menit) menggunakan zona waktu `Asia/Jakarta`.
- **Attendance Report & Export Excel (20%):** Perhitungan persentase kehadiran $\frac{\text{Hadir} + \text{Terlambat}}{\text{Total Sesi Berlangsung}} \times 100\%$ (mengabaikan sesi masa depan yang belum berlangsung), deteksi mahasiswa dengan kehadiran $<75\%$ (`WARNING (<75%)`), serta ekspor file `.xlsx` valid menggunakan `openpyxl`.
- **AI Attendance Insights (15%):** Analisis pola ketidakhadiran berdasarkan hari dan jam kuliah, *early warning* mahasiswa berisiko ($<75\%$), bukti kuantitatif (`evidence` & `sample_sessions`), serta rekomendasi tindakan prioritas dalam format JSON.
- **Security & Persistent Rate Limiting (5%):** Pencegahan *replay attack* lintas sesi/kelas, pencabutan token lama (`revoked_at`) saat QR diterbitkan ulang untuk periode keterlambatan, anti-spoofing NIM mahasiswa, proteksi akses laporan, serta *persistent database-backed rate limiting* (maksimal 5 percobaan per 60 detik $\rightarrow$ HTTP `429 Too Many Requests`).
- **Frontend UI (`/attendance-ui`):** Halaman web responsif untuk Dosen (Generate QR, Countdown Timer, Daftar Hadir, Laporan Warning, Export Excel, AI Insights) dan Mahasiswa (Kamera QR Scanner HTML5 + Input Token Manual Fallback).

---

## 2. Requirement Dosen dan Pemetaannya

| No | Requirement Dosen (PDF Minggu 12) | File Implementasi | Bukti Pengujian (`pytest`) | Status |
|---:|---|---|---|---|
| 1 | **QR Generation Service (30%):** Fungsi `generate_attendance_qr(schedule_id, valid_minutes=15)`, `qrcode` PNG, `PyJWT` `HS256`, `SECRET_KEY` dari env, `jti` unik, masa berlaku maks 15 menit, endpoint `GET /attendance/qr/{schedule_id}` (`image/png` + countdown). | `app/services/attendance_service.py`, `app/routers/attendance.py` | `test_qr_generation_png_jwt_expiry_and_unique_jti`, `test_lecturer_authorization_on_qr_generation` (`PASSED`) | **VERIFIED** |
| 2 | **Attendance Recording (30%):** Endpoint `POST /attendance/scan` (`token`, `nim`), verifikasi JWT, cek jadwal hari ini, cek enrollment KRS `APPROVED`, cegah duplikat, status `HADIR` ($\le 15$m), `TERLAMBAT` ($15\text{–}30$m), `DITOLAK` ($>30$m), re-issue QR periode terlambat. | `app/services/attendance_service.py`, `app/routers/attendance.py`, `docs/adr/ADR-014-*.md` | `test_scan_hadir_terlambat_late_reissue_and_over_30m_rejected`, `test_scan_rejects_unregistered_wrong_class_invalid_sig_and_revoked_token` (`PASSED`) | **VERIFIED** |
| 3 | **Attendance Report (20%):** Persentase kehadiran per mahasiswa per MK, daftar mahasiswa dengan presensi $<75\%$ (`WARNING`), sesi belum berlangsung tidak dihitung absen, dan Export ke Excel (`.xlsx`). | `app/services/attendance_report_service.py`, `app/routers/attendance.py` | `test_attendance_report_warning_future_session_exclusion_and_excel_export` (`PASSED`) | **VERIFIED** |
| 4 | **AI Attendance Insights (15%):** Deteksi pola hari (misal sering absen hari Senin) & jam kuliah (misal jam 07:00 absen rate tinggi), *early warning* mahasiswa berisiko $<75\%$, bukti sampel (`evidence`), dan rekomendasi tindakan JSON. | `app/services/ai_attendance_analyzer.py`, `app/routers/attendance.py` | `test_ai_attendance_insights_day_hour_early_warning_and_ui`, `test_attendance_report_warning_future_session_exclusion_and_excel_export` (`PASSED`) | **VERIFIED** |
| 5 | **Security & Rate Limiting (5%):** QR expiration, signature verification, replay prevention, anti-spoofing NIM, validasi kepemilikan jadwal dosen, proteksi akses laporan (`401`/`403`), dan persistent rate limiting (`429`). | `app/services/attendance_service.py`, `app/routers/attendance.py`, `app/models/attendance_models.py` | `test_security_nim_spoofing_rate_limiting_and_report_protection` (`PASSED`) | **VERIFIED** |
| 6 | **Frontend UI Dosen & Mahasiswa:** Halaman `/attendance-ui` terintegrasi dengan navigasi SIAKAD, menampilkan QR & countdown, kamera QR scanner + fallback manual, laporan warning, export Excel, dan AI Insights. | `app/routers/attendance.py`, `app/routers/dashboard.py` | `test_ai_attendance_insights_day_hour_early_warning_and_ui` & E2E probe di `temp_venv` (`PASSED`) | **VERIFIED** |

---

## 3. File yang Dibuat dan Diubah

### A. File Baru yang Dibuat:
1. `app/models/attendance_models.py` — Model SQLAlchemy `AttendanceSession`, `AttendanceQRToken`, `AttendanceRecord`, `AttendanceScanAttempt`.
2. `app/schemas/attendance.py` — Skema Pydantic `AttendanceQRGenerateRequest`, `AttendanceScanRequest`, `AIInsightsAnalyzeRequest`.
3. `app/services/attendance_service.py` — Layanan `generate_attendance_qr` dan `AttendanceService` (QR PNG, JWT HS256, validasi scan, rate limiting).
4. `app/services/attendance_report_service.py` — Layanan `AttendanceReportService` (perhitungan kehadiran, warning $<75\%$, export Excel `.xlsx`).
5. `app/services/ai_attendance_analyzer.py` — Layanan `AIAttendanceAnalyzer` (deteksi pola hari/jam, early warning, rekomendasi JSON).
6. `app/routers/attendance.py` — Router REST API `/attendance/*` & halaman UI `/attendance-ui`.
7. `alembic/versions/d4e8f2a1c305_add_week12_qr_attendance_tables.py` — Migrasi Alembic Minggu 12.
8. `tests/test_week12_attendance.py` — Suite pengujian unit, integrasi, dan keamanan Minggu 12.
9. `docs/adr/ADR-014-QR-Attendance-Masa-Berlaku-dan-Replay-Prevention.md` — Dokumen keputusan arsitektur Minggu 12.
10. Dokumentasi Minggu 12 (`ATTENDANCE_API_DOCUMENTATION.md`, `ATTENDANCE_USER_GUIDE.md`, `AI_ATTENDANCE_DOCUMENTATION.md`, `SECURITY_DOCUMENTATION.md`, `WEEK12_TEST_REPORT.md`, `WEEK12_REQUIREMENT_TRACEABILITY.md`, `WEEK12_SUBMISSION_REPORT.md`, dan `docs/week12/*`).
11. `PENGUMPULAN_SIAKAD/MINGGU_12.zip` — Paket pengumpulan mandiri Minggu 12.

### B. File Existing yang Diperbarui Secara Non-Destruktif:
1. `app/models/__init__.py` — Mengekspor model presensi Minggu 12.
2. `app/main.py` — Mendaftarkan `attendance.router`.
3. `app/routers/dashboard.py` — Menambahkan tautan navigasi `/attendance-ui`.
4. `requirements.txt` — Menambahkan `qrcode==7.4.2`, `PyJWT==2.9.0`, `openpyxl==3.1.5`, `tzdata==2024.2`.
5. `DATABASE_DOCUMENTATION.md` — Menambahkan dokumentasi 4 tabel Minggu 12 dan revisi `d4e8f2a1c305`.

---

## 4. Database Migration

- **Revision ID Baru:** `d4e8f2a1c305` (`down_revision = "b7e4c1d9a204"`).
- **Tabel yang Dibuat:**
  1. `attendance_session` (`uq_attendance_session_schedule_date`)
  2. `attendance_qr_token` (`uq_attendance_qr_token_jti`)
  3. `attendance_record` (`uq_attendance_record_session_student`, `uq_attendance_record_session_nim`)
  4. `attendance_scan_attempt` (`ix_attendance_scan_attempt_actor_time`)
- **Hasil Uji Migrasi pada Database Sementara:**
  - `upgrade head` $\rightarrow$ **27 tabel** terbentuk (`version = d4e8f2a1c305`).
  - `downgrade b7e4c1d9a204` $\rightarrow$ kembali ke **23 tabel** (`version = b7e4c1d9a204`).
  - `upgrade head` kembali $\rightarrow$ **27 tabel** (`version = d4e8f2a1c305`).

---

## 5. API Endpoint Minggu 12

- `GET /attendance/qr/{schedule_id}` (`+ /api/attendance/qr/{schedule_id}`) — Mengembalikan gambar QR (`image/png`) + header countdown.
- `POST /attendance/qr/{schedule_id}/generate` — Menerbitkan QR baru (`NORMAL` / `LATE`) dalam format JSON + Base64 PNG.
- `POST /attendance/scan` — Memvalidasi scan QR mahasiswa dan mencatat status `HADIR` atau `TERLAMBAT`.
- `GET /attendance/session/{session_id}/records` — Daftar mahasiswa yang telah presensi pada sesi tersebut.
- `POST /attendance/session/{session_id}/close` — Menutup sesi presensi.
- `GET /attendance/report` — Laporan presensi per mahasiswa & daftar warning $<75\%$.
- `GET /attendance/report/export` — Mengunduh laporan presensi dalam format Excel (`.xlsx`).
- `GET /attendance/ai-insights` & `POST /attendance/ai-insights` — Analisis pola absensi & rekomendasi tindakan JSON.
- `GET /attendance-ui` — Antarmuka web presensi Dosen & Mahasiswa.

---

## 6. Fitur Frontend (`/attendance-ui`)

1. **Panel Dosen:**
   - Pemilihan jadwal kuliah aktif dari database.
   - Tombol **Generate QR (Periode Normal 0–15m)** dan **Re-Generate QR (Periode Terlambat 15–30m)**.
   - Tampilan QR Code ukuran besar (`240x240px`) disertai **Countdown Timer (`MM:SS`)** real-time, `Session ID`, dan `JTI`.
   - Tabel daftar mahasiswa yang sudah melakukan presensi pada sesi berjalan.
   - Tabel laporan presensi dengan badge merah **`WARNING (<75%)`** dan tombol **Export Laporan ke Excel (.xlsx)**.
   - Panel **AI Attendance Insights** yang menampilkan *early warning*, pola hari/jam, dan rekomendasi tindakan.
2. **Panel Mahasiswa:**
   - **Kamera QR Scanner HTML5** (`navigator.mediaDevices.getUserMedia` + `BarcodeDetector`).
   - **Input Token Manual Fallback** beserta tombol bantu salin token untuk pengujian desktop tanpa kamera.
   - Kotak status dinamis yang menampilkan hasil **`HADIR`**, **`TERLAMBAT`**, atau pesan penolakan spesifik.

---

## 7. Hasil Testing & 8. Code Coverage

- **Pengujian Modul Minggu 12 (`tests/test_week12_attendance.py`):**
  - **`8 passed, 0 failed`** dalam `9.61s` (pada workspace) dan `3.88s` (pada clean `temp_venv`).
  - **Coverage Modul Minggu 12:** **`92%`** (`attendance_models.py: 100%`, `schemas/attendance.py: 100%`, `routers/attendance.py: 99%`, `attendance_report_service.py: 95%`, `ai_attendance_analyzer.py: 88%`, `attendance_service.py: 88%`).
- **Regression Testing Seluruh Project (Minggu 3–12):**
  - **`365 passed, 0 failed`** (`357` test Minggu 3–11 + `8` test Minggu 12).
  - **Total Code Coverage Project:** **`98%`** (`2.992` statements).

---

## 9. Security Verification

- **QR Expiration & Signature (`HS256`):** Token kedaluwarsa atau token dengan signature dimodifikasi langsung ditolak (`400 Bad Request`).
- **Replay & Duplicate Prevention:** `jti` unik terdaftar di DB, token lama dicabut (`revoked_at`) saat re-generate, dan constraint unik `(session_id, student_id)` menolak scan kedua (`409 Conflict`).
- **Anti-Spoofing NIM & Kepemilikan Jadwal:** Mahasiswa tidak dapat mengirim NIM mahasiswa lain (`403 Forbidden`), dan dosen tidak dapat membuat QR untuk jadwal dosen lain (`403 Forbidden`).
- **Persistent Rate Limiting:** Percobaan scan ke-6 dalam 60 detik oleh NIM yang sama diblokir dengan **`429 Too Many Requests`**.
- **Proteksi Laporan:** Akses `/attendance/report`, `/attendance/report/export`, dan `/attendance/ai-insights` tanpa kredensial ditolak (`401 Unauthorized`) dan akses oleh mahasiswa ditolak (`403 Forbidden`).

---

## 10. Clean Installation Verification (`temp_venv`)

Verifikasi instalasi bersih dilakukan dari hasil ekstraksi `PENGUMPULAN_SIAKAD/MINGGU_12.zip` pada direktori terisolasi:
1. Ekstraksi `MINGGU_12.zip` (`zipfile.testzip() == None`) $\rightarrow$ **PASS**
2. Pembuatan `temp_venv` baru & `pip install -r requirements.txt` $\rightarrow$ **PASS**
3. Eksekusi `alembic upgrade head` pada database kosong $\rightarrow$ **27 tabel** terbentuk pada revisi `d4e8f2a1c305` $\rightarrow$ **PASS**
4. Eksekusi `pytest -v` di dalam `temp_venv` $\rightarrow$ **`8 passed in 3.88s`** $\rightarrow$ **PASS**
5. Uji End-to-End (Seed data $\rightarrow$ FastAPI $\rightarrow$ Swagger `/docs` $\rightarrow$ UI `/attendance-ui` $\rightarrow$ Generate QR PNG $\rightarrow$ Scan QR `HADIR` $\rightarrow$ Laporan & Export `.xlsx` $\rightarrow$ AI Insights JSON) $\rightarrow$ **PASS**

---

## 11. Struktur ZIP, 12. Ukuran ZIP, 13. Jumlah File, & 14. SHA-256

- **Lokasi File ZIP:** `PENGUMPULAN_SIAKAD/MINGGU_12.zip`
- **Ukuran ZIP:** **`146.995` byte** (`~143,5 KB`)
- **Jumlah File di Dalam ZIP:** **`91` file**
- **SHA-256 Checksum:** `43b2edab826a990560f8ea19d6bda1ed1c78531c105c5d1444fb710f81f83640`
- **Struktur Ringkas `MINGGU_12.zip`:**
```text
MINGGU_12.zip
├── alembic/
│   ├── versions/                  # 9 revisi migrasi Alembic (c0b4e3a8c963 s/d d4e8f2a1c305)
│   ├── README
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── models/                    # Termasuk attendance_models.py
│   ├── observers/
│   ├── routers/                   # Termasuk attendance.py
│   ├── schemas/                   # Termasuk attendance.py
│   ├── services/                  # Termasuk attendance_service.py, attendance_report_service.py, ai_attendance_analyzer.py
│   │   └── krs/
│   ├── utils/
│   ├── database.py
│   └── main.py
├── docs/
│   ├── adr/
│   │   └── ADR-014-QR-Attendance-Masa-Berlaku-dan-Replay-Prevention.md
│   └── week12/                    # Salinan lengkap dokumentasi Minggu 12
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_week12_attendance.py
├── .env.example
├── AI_ATTENDANCE_DOCUMENTATION.md
├── ATTENDANCE_API_DOCUMENTATION.md
├── ATTENDANCE_USER_GUIDE.md
├── DATABASE_DOCUMENTATION.md
├── INSTALLATION_GUIDE.md
├── README.md
├── SECURITY_DOCUMENTATION.md
├── WEEK12_REQUIREMENT_TRACEABILITY.md
├── WEEK12_TEST_REPORT.md
├── alembic.ini
├── pytest.ini
└── requirements.txt
```

---

## 15. Kesimpulan Kesiapan Pengumpulan

Seluruh requirement tugas dosen Minggu 12 (Modul Presensi QR Code) berstatus **`VERIFIED`**, seluruh regression test Minggu 3–11 (`357 passed`) dan test baru Minggu 12 (`8 passed`) lulus 100% (`365 passed`), serta paket **`PENGUMPULAN_SIAKAD/MINGGU_12.zip`** telah teruji pada *clean virtual environment* dan **SIAP DIKUMPULKAN KEPADA DOSEN**.
