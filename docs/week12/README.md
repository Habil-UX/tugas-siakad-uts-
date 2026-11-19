# Minggu 12 — Sistem Manajemen Presensi QR Code & AI Attendance Insights

## 1. Tujuan Tugas
Mengembangkan modul presensi mahasiswa berbasis **QR Code** dinamis (`PyJWT` `HS256` + `qrcode` PNG) yang diterbitkan oleh dosen untuk sesi perkuliahan tertentu, dipindai oleh mahasiswa melalui kamera browser atau input token, divalidasi secara ketat terhadap jadwal kuliah, jendela waktu kehadiran (`HADIR` $\le 15$ menit, `TERLAMBAT` $15\text{–}30$ menit, `DITOLAK` $>30$ menit dalam zona waktu `Asia/Jakarta`), serta dilengkapi **Laporan Presensi**, **Indikator Warning ($<75\%$)**, **Export Excel (`.xlsx`)**, dan **AI Attendance Insights**.

---

## 2. Requirement Dosen (Berdasarkan PDF Tugas Minggu 12)
1. **QR Generation Service (30%):**
   - Fungsi `generate_attendance_qr(schedule_id, valid_minutes=15)` menggunakan library `qrcode` dan `PyJWT` (`HS256`) dengan `SECRET_KEY` dari environment variable.
   - Payload JWT memuat `schedule_id`, `session_id`, `generated_at`/`iat`, `expires_at`/`exp`, dan `jti` unik.
   - Endpoint `GET /attendance/qr/{schedule_id}` mengembalikan gambar `image/png` disertai header countdown masa berlaku.
   - Validasi otorisasi bahwa dosen hanya dapat membuat QR untuk jadwal kuliah yang diampunya.
2. **Attendance Recording (30%):**
   - Endpoint `POST /attendance/scan` dengan input `{"token": "jwt_from_qr", "nim": "xxx"}`.
   - Validasi signature JWT `HS256`, expiration, `jti`, `session_id`, hari jadwal kuliah, pendaftaran mahasiswa pada mata kuliah di KRS berstatus `APPROVED`, dan pencegahan scan duplikat (`409 Conflict`).
   - Penentuan status: **`HADIR`** (scan dalam 15 menit pertama sejak `jam_mulai`), **`TERLAMBAT`** (scan setelah 15 menit hingga maksimal 30 menit sejak `jam_mulai`), dan **`DITOLAK`** ($>30$ menit).
   - Dukungan penerbitan ulang QR untuk periode keterlambatan (15–30 menit) dengan pencabutan token lama (`revoked_at`).
3. **Attendance Report (20%):**
   - Perhitungan persentase kehadiran per mahasiswa per mata kuliah: $\frac{\text{Hadir} + \text{Terlambat}}{\text{Total Sesi Berlangsung}} \times 100\%$.
   - Sesi yang belum berlangsung (di masa depan) tidak dihitung sebagai ketidakhadiran.
   - Daftar mahasiswa dengan presentase kehadiran $<75\%$ (`WARNING (<75%)`).
   - Fitur Export Laporan ke format Microsoft Excel (`.xlsx` menggunakan `openpyxl`).
4. **AI Attendance Insights (15%):**
   - Deteksi pola ketidakhadiran berdasarkan hari (contoh: *"Sering tidak hadir pada hari Senin"*) dan jam kuliah (contoh: *"Kelas di jam 07:00 memiliki tingkat ketidakhadiran tinggi"*).
   - *Early warning* jumlah mahasiswa berisiko ($<75\%$) beserta rekomendasi tindakan prioritas dalam format JSON terstruktur.
5. **Security & Rate Limiting (5%):**
   - QR expiration, verifikasi signature, pencegahan *replay attack* tanpa mematikan QR bagi mahasiswa lain di kelas yang sama, pencegahan pemalsuan NIM, proteksi akses laporan, dan *persistent database-backed rate limiting* (`429 Too Many Requests`).

---

## 3. Fitur yang Diimplementasikan
- **Database & Migrasi Alembic (`d4e8f2a1c305`):** 4 tabel baru (`attendance_session`, `attendance_qr_token`, `attendance_record`, `attendance_scan_attempt`) dengan Foreign Key, Composite Index, dan Unique Constraint anti-duplikat.
- **QR Generation Service (`app/services/attendance_service.py`):** Pembuatan gambar QR PNG dan token JWT `HS256` dengan dukungan fase `NORMAL` (0–15m) dan `LATE` (15–30m).
- **Scan Validation & Rate Limiting (`app/services/attendance_service.py`):** Validasi berlapis 8 tahap dan pembatasan 5 percobaan scan per 60 detik di database.
- **Attendance Report & Excel Exporter (`app/services/attendance_report_service.py`):** Perhitungan kehadiran akurat dan ekspor `.xlsx` dengan pewarnaan baris warning.
- **AI Attendance Analyzer (`app/services/ai_attendance_analyzer.py`):** Analisis statistik deterministik lokal dengan bukti sampel (`evidence`) dan rekomendasi tindakan.
- **Frontend UI (`/attendance-ui`):** Halaman responsif untuk Dosen (Generate QR, Countdown Timer, Daftar Hadir, Laporan Warning, Export Excel, AI Insights) dan Mahasiswa (Kamera QR Scanner HTML5 + Input Token Manual Fallback).

---

## 4. Database & Relasi
- `attendance_session.schedule_id` $\rightarrow$ `jadwal_kuliah.id` (`uq_attendance_session_schedule_date`)
- `attendance_qr_token.session_id` $\rightarrow$ `attendance_session.id` (`uq_attendance_qr_token_jti`)
- `attendance_record.session_id` $\rightarrow$ `attendance_session.id`
- `attendance_record.student_id` $\rightarrow$ `calon_mahasiswa.id` (`uq_attendance_record_session_student`)
- `attendance_record.nim` $\rightarrow$ `calon_mahasiswa.nim` (`uq_attendance_record_session_nim`)
- `attendance_record.qr_token_id` $\rightarrow$ `attendance_qr_token.id`

---

## 5. Daftar Endpoint API
- `GET /attendance/qr/{schedule_id}` — Gambar PNG QR Code + header countdown.
- `POST /attendance/qr/{schedule_id}/generate` — Generate/Re-generate QR (JSON + Base64 PNG).
- `POST /attendance/scan` — Scan QR presensi oleh mahasiswa.
- `GET /attendance/session/{session_id}/records` — Daftar hadir mahasiswa per sesi.
- `POST /attendance/session/{session_id}/close` — Tutup sesi presensi.
- `GET /attendance/report` — Laporan presensi & daftar warning $<75\%$.
- `GET /attendance/report/export` — Unduh laporan Excel (`.xlsx`).
- `GET /attendance/ai-insights` & `POST /attendance/ai-insights` — Analisis AI Attendance Insights (JSON).
- `GET /attendance-ui` — Antarmuka Web Presensi Dosen & Mahasiswa.

---

## 6. Cara Instalasi, Menjalankan, & Testing
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```
Menjalankan pengujian otomatis:
```powershell
python -m pytest -v tests/test_week12_attendance.py
```
