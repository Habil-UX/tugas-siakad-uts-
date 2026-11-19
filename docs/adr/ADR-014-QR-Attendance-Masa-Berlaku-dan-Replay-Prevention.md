# ADR-014: Arsitektur Presensi QR Code, Resolusi Masa Berlaku 15 Menit vs Window Terlambat 30 Menit, dan Pencegahan Replay Attack

## Status
Diterapkan (Minggu 12).

## Konteks
Dokumen tugas Minggu 12 menetapkan dua aturan waktu yang harus diselaraskan:
1. QR Code yang diterbitkan dosen hanya berlaku maksimal **15 menit** (`valid_minutes <= 15`).
2. Mahasiswa yang melakukan scan dalam **15 menit pertama** sejak waktu mulai kuliah (`jam_mulai`) berstatus **`HADIR`**, sedangkan scan setelah 15 menit hingga maksimal **30 menit** sejak waktu mulai kuliah berstatus **`TERLAMBAT`**, dan di atas 30 menit **`DITOLAK`**.
3. Selain itu, satu QR Code yang ditampilkan dosen di proyektor kelas harus dapat dipindai oleh banyak mahasiswa yang terdaftar di kelas tersebut, tetapi tetap harus mencegah *replay attack* dan *duplicate scan*.

## Keputusan
1. **Pemisahan Masa Berlaku Token QR (`expires_at`) dan Window Presensi Sesi (`jam_mulai + 30 menit`):**
   - QR pertama diterbitkan untuk fase kehadiran normal (`phase = "NORMAL"`, menit ke-0 s/d ke-15) dengan masa berlaku maksimal 15 menit.
   - Dosen dapat menerbitkan ulang QR kedua untuk fase keterlambatan (`phase = "LATE"`, menit ke-15 s/d ke-30) dengan `jti` unik baru.
   - Saat QR baru diterbitkan pada sesi yang sama (`revoke_previous = True`), token QR sebelumnya dicabut (`revoked_at = generated_at`) dan masa berlaku QR baru dibatasi agar tidak melewati batas akhir window presensi sesi (`jam_mulai + 30 menit`).
   - Penentuan status `HADIR` vs `TERLAMBAT` selalu dihitung berdasarkan selisih waktu scan terhadap **`schedule.jam_mulai`**, bukan terhadap waktu terbit QR kedua.
2. **Mekanisme Multi-Layer Replay Attack Prevention:**
   - **Shared-Class Safe:** Token QR tidak langsung hangus secara global ketika mahasiswa pertama melakukan scan, agar mahasiswa lain di kelas yang sama tetap dapat memindai QR di layar.
   - **Unique `jti` & Session Binding:** Setiap QR memiliki klaim `jti` (UUID4 hex), `session_id`, dan `schedule_id` yang ditandatangani dengan `HS256` (`PyJWT`) dan disimpan pada tabel `attendance_qr_token`.
   - **Per-Student Single Use (`UniqueConstraint`):** Tabel `attendance_record` menerapkan constraint unik `uq_attendance_record_session_student(session_id, student_id)` dan `uq_attendance_record_session_nim(session_id, nim)` sehingga satu mahasiswa hanya dapat melakukan scan satu kali per sesi.
   - **KRS Enrollment & Anti-Spoofing Binding:** Mahasiswa wajib terdaftar pada mata kuliah terkait di KRS berstatus `APPROVED`, dan identitas `nim` diverifikasi terhadap klaim token autentikasi pengguna aktif.
   - **Persistent Database-Backed Rate Limiting:** Setiap percobaan scan dicatat ke tabel `attendance_scan_attempt` dan dibatasi maksimal 5 percobaan per 60 detik per pengguna (`HTTP 429 Too Many Requests`).

## Konsekuensi
- Tidak ada kontradiksi antara aturan masa berlaku QR 15 menit dan batas keterlambatan 30 menit.
- Keamanan terhadap pemalsuan token, *replay attack* lintas kelas/sesi, pemalsuan NIM, dan *spam scan* terjaga secara persisten di level aplikasi maupun database.
