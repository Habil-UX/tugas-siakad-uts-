# DOKUMENTASI KEAMANAN & RATE LIMITING MODUL PRESENSI (`SECURITY_DOCUMENTATION.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 12

---

## 1. Arsitektur Keamanan Token QR Presensi (JWT HS256)

1. **Penandatanganan Kriptografis (`HS256`):**
   - Setiap QR Code mengemas token JSON Web Token (`PyJWT`) yang ditandatangani dengan algoritma `HS256` menggunakan `SECRET_KEY` yang dibaca dari variabel environment (`os.getenv("SECRET_KEY")`).
   - Tidak ada `SECRET_KEY` produksi yang disimpan secara *hardcoded* di dalam repositori publik maupun ditampilkan pada log aplikasi.
2. **Pembatasan Masa Berlaku Ketat (`<= 15 Menit` & Cap Window 30 Menit):**
   - Setiap token memiliki klaim `iat`, `exp`, `generated_at`, dan `expires_at` maksimal 15 menit.
   - Apabila dosen menerbitkan ulang QR pada periode keterlambatan (menit ke-15 s/d ke-30 sejak `jam_mulai`), masa berlaku token otomatis dipotong agar tidak melewati batas akhir 30 menit sesi perkuliahan.

---

## 2. Pencegahan Replay Attack Tanpa Memblokir Mahasiswa Sekelas

Karena satu QR Code ditampilkan oleh dosen di depan kelas untuk dipindai oleh banyak mahasiswa peserta kelas yang sama, token tidak boleh langsung hangus secara global setelah scan pertama. Pencegahan *replay attack* diterapkan melalui 6 lapisan:
1. **`jti` (JWT ID) Unik & Database Registry:** Setiap pembuatan QR menghasilkan `jti` (`UUID4 hex`) unik yang disimpan pada tabel `attendance_qr_token`. Token dengan `jti` yang tidak terdaftar di database langsung ditolak.
2. **Revokasi Token Lama Saat Re-Generate (`revoked_at`):** Ketika dosen menerbitkan QR baru untuk sesi yang sama, token QR sebelumnya langsung ditandai `revoked_at` sehingga tangkapan layar (*screenshot*) QR lama tidak dapat digunakan lagi.
3. **Session & Schedule Binding:** Klaim `schedule_id` dan `session_id` di dalam JWT dicocokkan terhadap baris `attendance_qr_token` dan `attendance_session` di database, mencegah penggunaan token untuk kelas atau sesi lain.
4. **Validasi Hari & Jam Perkuliahan (`Asia/Jakarta`):** Sistem memverifikasi bahwa sesi berlangsung pada hari yang sama dengan `JadwalKuliah.hari` dan waktu scan berada dalam rentang `0..30` menit sejak `JadwalKuliah.jam_mulai`.
5. **Verifikasi Enrollment KRS `APPROVED`:** Hanya mahasiswa yang memiliki `KRS` berstatus `APPROVED` dengan `KRSDetail` pada `matakuliah_id` jadwal tersebut yang diizinkan melakukan presensi (`403 Forbidden` bagi mahasiswa luar kelas).
6. **Constraint Unik Anti-Duplikat per Mahasiswa per Sesi:** Tabel `attendance_record` menerapkan `UniqueConstraint("session_id", "student_id")` dan `UniqueConstraint("session_id", "nim")` yang menolak scan kedua oleh mahasiswa yang sama (`409 Conflict`).

---

## 3. Anti-Spoofing Identitas & Otorisasi Peran (RBAC)

1. **Pencegahan Pemalsuan NIM Mahasiswa:**
   - Apabila mahasiswa mengirim request dengan token autentikasi (`Authorization: Bearer <token>` atau header identitas), sistem memverifikasi bahwa `claims["nim"] == payload.nim`. Upaya mengirim NIM mahasiswa lain langsung ditolak dengan HTTP `403 Forbidden` dan dicatat sebagai `REJECTED_NIM_SPOOF`.
2. **Validasi Kepemilikan Jadwal Dosen:**
   - Dosen hanya dapat membuat QR Code untuk jadwal kuliah yang diampunya (`schedule.dosen_id == dosen.id`). Upaya membuat QR untuk jadwal dosen lain ditolak dengan HTTP `403 Forbidden`.
3. **Proteksi Akses Laporan & AI Insights:**
   - Endpoint `/attendance/report`, `/attendance/report/export`, dan `/attendance/ai-insights` diproteksi oleh `require_report_authorization`: menolak akses tanpa kredensial (`401 Unauthorized`) maupun akses oleh role `mahasiswa` (`403 Forbidden`).

---

## 4. Persistent Database-Backed Rate Limiting

- Berbeda dengan *in-memory counter* yang hilang ketika server mengalami *restart* atau *multi-worker reload*, rate limiting scan presensi diimplementasikan secara persisten menggunakan tabel database **`attendance_scan_attempt`** dengan composite index `ix_attendance_scan_attempt_actor_time(actor_key, attempted_at)`.
- **Aturan Batas:** Maksimal **5 percobaan scan dalam jendela waktu 60 detik** untuk setiap `actor_key` (`nim`).
- Percobaan ke-6 dan seterusnya dalam 60 detik langsung diblokir dengan HTTP **`429 Too Many Requests`** sebelum pemrosesan lebih lanjut.
