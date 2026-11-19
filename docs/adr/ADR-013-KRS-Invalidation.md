# ADR-013: Integrasi JadwalKuliah dengan Validasi dan Invalidasi KRS

## Status
Diterapkan & Disempurnakan (P3).

## Konteks
Satu mata kuliah (`Matakuliah`) dapat memiliki jadwal aktual yang dikelola pada tabel `JadwalKuliah` (termasuk kemungkinan beberapa sesi/kelas). Ketika jadwal pada `JadwalKuliah` diubah oleh Admin, KRS mahasiswa yang mengambil mata kuliah tersebut harus diidentifikasi, divalidasi ulang menggunakan jadwal terbaru tanpa menimpa atribut master `Matakuliah`, ditandai `needs_review`, dicatat pada riwayat transisi, dan diberi notifikasi.

## Keputusan
1. Menjadikan tabel `JadwalKuliah` (dengan `status == "AKTIF"`) sebagai sumber data jadwal aktual pada `ConflictValidator._get_course_schedules` ketika memvalidasi konflik waktu KRS, dengan fallback ke atribut `Matakuliah` apabila mata kuliah belum memiliki entri di `JadwalKuliah`.
2. Tidak melakukan sinkronisasi timpa langsung ke tabel `Matakuliah` saat jadwal diubah, sehingga mendukung multi-sesi/kelas pada `JadwalKuliah`.
3. Pada `SchedulingService.update_schedule` dan `delete_schedule`:
   - Melakukan `db.flush()` agar perubahan jadwal langsung terlihat oleh validator.
   - Mengidentifikasi seluruh KRS mahasiswa terdampak (`status != "APPROVED"`), mengatur `krs.needs_review = True`, menjalankan validasi ulang `KRSManager(db).validate_krs(nim)`, dan mencatat entri audit pada tabel `krs_transition` (`SYSTEM_SCHEDULE_CHANGED_CONFLICT_DETECTED` / `SYSTEM_SCHEDULE_CHANGED_NEEDS_REVIEW`).
   - Mengirimkan notifikasi melalui `ScheduleSubject` (`StudentObserver`, `LecturerObserver`, `AdminObserver`) setelah `db.commit()` berhasil.
