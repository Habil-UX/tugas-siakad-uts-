# PANDUAN PENGGUNA MODUL PRESENSI QR CODE (`ATTENDANCE_USER_GUIDE.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 12

---

## 1. Panduan untuk Dosen (Generate QR, Monitoring, Laporan & AI Insights)

1. **Membuka Halaman Presensi:**
   - Buka browser dan akses `http://127.0.0.1:8000/attendance-ui`.
2. **Membuat QR Code Presensi (Periode Normal 0–15 Menit):**
   - Pada **Panel Dosen**, pilih jadwal kuliah aktif dari dropdown **Pilih Jadwal Kuliah Aktif**.
   - Atur masa berlaku QR (default **15 menit**, maksimal 15 menit).
   - Klik tombol **Generate QR (Periode Normal 0–15m)**.
   - Gambar QR Code berukuran besar beserta **Countdown Timer (`MM:SS`)**, `Session ID`, dan `JTI` akan langsung tampil di layar untuk dipindai oleh mahasiswa.
3. **Menerbitkan Ulang QR untuk Mahasiswa Terlambat (15–30 Menit):**
   - Apabila 15 menit pertama telah habis namun waktu perkuliahan masih berada dalam rentang 15–30 menit sejak `jam_mulai`, klik tombol **Re-Generate QR (Periode Terlambat 15–30m)**.
   - Sistem otomatis mencabut token QR lama, menerbitkan QR baru dengan `jti` unik, dan membatasi masa berlakunya agar tidak melewati menit ke-30 sejak awal kuliah. Mahasiswa yang memindai pada periode ini otomatis tercatat dengan status **`TERLAMBAT`**.
4. **Melihat Laporan Presensi, Warning `<75%`, & Export Excel:**
   - Pada bagian **Laporan Presensi Mahasiswa & Indikator Warning (<75%)**, klik **Refresh Laporan Presensi**.
   - Mahasiswa dengan kehadiran di bawah 75% ditandai dengan lencana merah **`WARNING (<75%)`**.
   - Klik **Export Laporan ke Excel (.xlsx)** untuk mengunduh file `laporan_presensi_mahasiswa.xlsx`.
5. **Melihat AI Attendance Insights:**
   - Klik **Muat Analisis AI Attendance Insights** untuk melihat deteksi pola ketidakhadiran berdasarkan hari, jam kuliah, *early warning* mahasiswa berisiko, serta rekomendasi konseling akademik atau evaluasi jadwal.

---

## 2. Panduan untuk Mahasiswa (Scan QR Kamera & Input Manual Fallback)

1. **Membuka Panel Scan Mahasiswa:**
   - Buka `http://127.0.0.1:8000/attendance-ui` pada smartphone atau laptop.
   - Masukkan **NIM Mahasiswa** pada kolom yang tersedia.
2. **Memindai QR Code Menggunakan Kamera:**
   - Klik tombol **Buka Kamera QR Scanner** dan arahkan kamera ke QR Code dosen.
   - Begitu QR Code terbaca, token JWT otomatis dikirim ke endpoint `POST /attendance/scan`.
3. **Menggunakan Input Token Manual (Fallback Jika Kamera Tidak Tersedia):**
   - Jika perangkat tidak memiliki kamera, tempelkan (*paste*) string token JWT pada kotak **Token JWT QR Presensi** (atau klik tombol bantu **Salin Token ke Form Scan Mahasiswa** saat demonstrasi lokal), lalu klik **Kirim Presensi Sekarang**.
4. **Status Hasil Presensi:**
   - **`HADIR` (Hijau):** Jika scan dilakukan dalam 0–15 menit sejak jam mulai kuliah.
   - **`TERLAMBAT` (Kuning/Hijau):** Jika scan dilakukan pada menit ke-15 hingga ke-30 sejak jam mulai kuliah.
   - **Pesan Penolakan (Merah):** Ditampilkan secara spesifik apabila QR telah *expired*, mahasiswa bukan peserta kelas/mata kuliah tersebut di KRS `APPROVED`, mahasiswa sudah melakukan presensi sebelumnya (*duplikat*), atau waktu scan telah melewati batas 30 menit.
