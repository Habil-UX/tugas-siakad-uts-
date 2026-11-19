# LAPORAN PENGUJIAN & QUALITY ASSURANCE MINGGU 12 (`WEEK12_TEST_REPORT.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 12: Modul Presensi (QR Code)  
**Tanggal Eksekusi:** 18 November 2026  
**File Test Minggu 12:** `tests/test_week12_attendance.py`

---

## 1. Ringkasan Eksekusi Pengujian

| Kategori Pengujian | Jumlah Test | Hasil Eksekusi | Status |
|---|---:|---|---|
| **Test Suite Baru Minggu 12 (`test_week12_attendance.py`)** | **8 Test Komprehensif** (mencakup 28 sub-assertion skenario) | **`8 passed, 0 failed`** | **100% PASSED** |
| **Regression Test Suite Minggu 3–11 (27 file test)** | **357 Test** | **`357 passed, 0 failed`** | **100% PASSED** |
| **Total Keseluruhan Suite SIAKAD (Minggu 3–12)** | **365 Test** | **`365 passed, 0 failed`** | **100% PASSED** |
| **Code Coverage Keseluruhan (`--cov=app`)** | `2.992` Statements | **`98% Coverage`** (melampaui target $\ge 80\%$) | **VERIFIED** |

---

## 2. Rincian Skenario Pengujian Minggu 12 yang Terverifikasi

### A. QR Generation Service (30%)
1. **`test_qr_generation_png_jwt_expiry_and_unique_jti`:**
   - Memastikan `generate_attendance_qr(schedule_id, valid_minutes=15)` menghasilkan gambar PNG valid (`\x89PNG\r\n\x1a\n`) dan token JWT `HS256`.
   - Memastikan payload JWT memuat `schedule_id`, `session_id`, `generated_at`/`iat`, `expires_at`/`exp` (tepat 15 menit = 900 detik), dan `jti` unik.
   - Memastikan setiap penerbitan QR menghasilkan `jti` yang berbeda.
   - Memastikan endpoint `GET /attendance/qr/{schedule_id}` mengembalikan `Content-Type: image/png` beserta header countdown (`X-Attendance-Expires-In`, `X-Attendance-JTI`, `X-Attendance-Phase`).
2. **`test_lecturer_authorization_on_qr_generation`:**
   - Memastikan dosen tidak dapat membuat QR untuk jadwal milik dosen lain (`403 Forbidden`).
   - Memastikan mahasiswa tidak dapat mengakses endpoint pembuatan QR (`403 Forbidden`).

### B. Attendance Recording & Scan Validation (30%)
3. **`test_scan_hadir_terlambat_late_reissue_and_over_30m_rejected`:**
   - **Status `HADIR`:** Scan pada menit ke-10 sejak `jam_mulai` berhasil disimpan dengan status `HADIR`.
   - **Duplicate Scan Prevention:** Scan kedua oleh mahasiswa yang sama pada sesi yang sama ditolak (`409 Conflict`).
   - **Expired QR Rejection:** Scan menggunakan QR pertama setelah 15 menit ditolak (`400 Bad Request - expired`).
   - **Re-Issue QR Periode Keterlambatan (15–30m):** Dosen menerbitkan QR baru pada menit ke-16 (`phase = "LATE"`), masa berlaku otomatis dibatasi tidak melewati menit ke-30, dan scan mahasiswa ke-2 pada menit ke-22 berhasil disimpan dengan status **`TERLAMBAT`**.
   - **Batas Maksimal 30 Menit:** Scan pada menit ke-35 ($>30$ menit sejak `jam_mulai`) ditolak (`400 Bad Request`).
4. **`test_scan_rejects_unregistered_wrong_class_invalid_sig_and_revoked_token`:**
   - Mahasiswa kelas lain ditolak (`403 Forbidden`).
   - Mahasiswa dengan KRS belum `APPROVED` (`DRAFT`) ditolak (`403 Forbidden`).
   - Token dengan signature `HS256` palsu/dimodifikasi ditolak (`400 Bad Request`).
   - Token lama yang telah dicabut (`revoked_at`) saat dosen menerbitkan QR baru ditolak (`400 Bad Request`), sedangkan mahasiswa lain tetap dapat menggunakan QR baru yang aktif.
   - Token dengan manipulasi `schedule_id` lintas kelas ditolak (`400 Bad Request`).

### C. Security & Persistent Rate Limiting (5%)
5. **`test_security_nim_spoofing_rate_limiting_and_report_protection`:**
   - **Anti-Spoofing NIM:** Mahasiswa yang login dengan token miliknya ditolak (`403 Forbidden`) saat mencoba mengirim NIM mahasiswa lain pada body `/attendance/scan`.
   - **Proteksi Laporan:** Akses ke `/attendance/report`, `/attendance/report/export`, dan `/attendance/ai-insights` tanpa kredensial ditolak (`401 Unauthorized`), dan akses oleh role `mahasiswa` ditolak (`403 Forbidden`).
   - **Database-Backed Rate Limiting:** Percobaan scan berulang $>5$ kali dalam 60 detik oleh aktor yang sama langsung diblokir dengan **`429 Too Many Requests`** dan tercatat pada tabel `attendance_scan_attempt`.

### D. Attendance Report & Excel Export (20%)
6. **`test_attendance_report_warning_future_session_exclusion_and_excel_export`:**
   - Menghitung persentase kehadiran dari 4 sesi yang telah berlangsung (`100.0%` untuk 3 Hadir + 1 Terlambat; `50.0%` untuk 2 Hadir + 2 Tidak Hadir).
   - Menandai mahasiswa dengan kehadiran `50.0%` ($<75\%$) sebagai `is_warning = True` (`WARNING (<75%)`).
   - Memastikan 2 sesi masa depan yang belum berlangsung **tidak** dihitung sebagai ketidakhadiran.
   - Memastikan file `.xlsx` hasil `/attendance/report/export` dapat dibuka dengan `openpyxl.load_workbook` dan berisi baris data yang akurat.

### E. AI Attendance Insights & Frontend UI (15%)
7. **`test_ai_attendance_insights_day_hour_early_warning_and_ui`:**
   - Mendeteksi pola absensi hari (`attendance_pattern`: sering tidak hadir pada hari Senin), pola jam (`time_slot_pattern`: kelas jam `07:00` absen rate tinggi), dan `early_warning` ($<75\%$).
   - Menghasilkan rekomendasi tindakan (`actions`) yang valid untuk konseling akademik dan evaluasi jadwal.
   - Memastikan halaman `/attendance-ui` merespons `200 OK` dengan antarmuka Dosen & Mahasiswa lengkap.
8. **`test_session_records_close_and_validation_edge_cases`:**
   - Menguji penolakan scan sebelum jam kuliah dimulai, daftar hadir sesi (`/attendance/session/{id}/records`), penutupan sesi (`/attendance/session/{id}/close`), dan penolakan scan setelah sesi ditutup.
