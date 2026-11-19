# PANDUAN PENGGUNA (`USER_GUIDE.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 3–11

Dokumen ini menjelaskan cara menggunakan fitur-fitur aplikasi SIAKAD bagi tiga peran pengguna utama (**Admin Akademik/Keuangan**, **Dosen / Dosen PA**, dan **Calon Mahasiswa / Mahasiswa**) baik melalui halaman antarmuka web (UI) maupun antarmuka interaktif Swagger (`/docs`).

---

## 1. Peran Pengguna & Akun Demo Default

Setelah menjalankan `alembic upgrade head`, sistem menyediakan 3 akun demo untuk pengujian autentikasi dan *Role-Based Access Control (RBAC)* di `/api/auth/login`:

| Peran (`role`) | Username | Password | Hak Akses Utama |
|---|---|---|---|
| **Admin** (`admin`) | `admin` | `admin123` | Persetujuan/penolakan PMB, manajemen jadwal kuliah & ruangan, resolusi konflik jadwal, pembuatan tagihan SPP semester, reminder tunggakan, dashboard keuangan. |
| **Dosen / Dosen PA** (`dosen`) | `dosen_pa` | `dosen123` | Persetujuan (`approve`) & permintaan revisi (`revise`) KRS mahasiswa bimbingan, input nilai baru, dan edit nilai mahasiswa beserta alasan perubahan. |
| **Mahasiswa** (`mahasiswa`) | `mahasiswa1` | `mhs123` | Pengisian KRS (`add`/`remove`/`submit`), rekomendasi KRS pintar, melihat IPS/IPK, mengunduh PDF Transkrip Akademik, dan melakukan pembayaran SPP. |

---

## 2. Alur Penggunaan per Modul (End-to-End Workflow)

### A. Modul 1: Penerimaan Mahasiswa Baru — PMB (Minggu 3–4)
1. **Pendaftaran Calon Mahasiswa (`POST /api/pmb/register`):**
   - Calon mahasiswa mengisi `nama_lengkap`, `email` (unik), `phone` (format Indonesia: `08...` / `+628...`), `tanggal_lahir`, `alamat`, `program_studi_id`, dan `jalur_masuk_id`.
   - Status awal otomatis tercatat sebagai `pending`.
2. **Persetujuan & Pembuatan NIM (`PUT /api/pmb/approve/{id}`):**
   - Admin menyetujui pendaftaran (dapat menyertakan `?dosen_pa_id=1` untuk menetapkan Dosen Pembimbing Akademik).
   - Sistem secara otomatis dan *thread-safe* menghasilkan **NIM** unik dengan format `[TAHUN][KODE_PRODI]-[4_DIGIT]` (contoh: `2025001-0001`).
   - Jika endpoint dipanggil ulang untuk mahasiswa yang sudah `approved`, sistem mengembalikan NIM yang sama (*idempotent*).
3. **Statistik PMB (`GET /api/pmb/stats`):**
   - Menampilkan rekapitulasi pendaftar berdasarkan status, jalur masuk, dan program studi menggunakan agregasi SQL `GROUP BY`.

---

### B. Modul 2: Kartu Rencana Studi — KRS (Minggu 5–6)
1. **Menambah & Menghapus Mata Kuliah (`POST /api/krs/add` & `POST /api/krs/remove`):**
   - Mahasiswa menambahkan mata kuliah ke KRS berstatus `DRAFT` atau `REVISION`.
   - Sistem memvalidasi melalui rantai **Chain of Responsibility**:
     1. **Cek Tunggakan Keuangan:** Diblokir (`403 Forbidden`) jika mahasiswa memiliki tagihan SPP `overdue`.
     2. **SKSValidator:** Total SKS maksimal **24 SKS**.
     3. **PrerequisiteValidator:** Seluruh prasyarat harus sudah lulus dengan nilai minimal **C (bobot $\ge 2.0$)** pada semester sebelumnya.
     4. **ConflictValidator:** Tidak ada jadwal kuliah aktif (`JadwalKuliah`) yang beririsan pada hari dan jam yang sama.
     5. **DuplicateValidator:** Mata kuliah yang sama tidak boleh diambil dua kali dalam satu KRS.
2. **Submit, Approve, & Revise KRS (State Machine):**
   - Mahasiswa menekan `POST /api/krs/submit/{nim}` (`DRAFT`/`REVISION` $\rightarrow$ `SUBMITTED`; KRS kosong ditolak dengan HTTP `400`).
   - Dosen PA memverifikasi melalui `POST /api/krs/approve/{nim}` (`SUBMITTED` $\rightarrow$ `APPROVED`) atau meminta perbaikan melalui `POST /api/krs/revise/{nim}` (`SUBMITTED` $\rightarrow$ `REVISION`).
3. **AI KRS Recommender (`POST /api/krs/recommend/{nim}`):**
   - Menghasilkan kombinasi mata kuliah optimal berbasis *Constraint Satisfaction Problem (CSP) Backtracking* yang memprioritaskan mata kuliah wajib, semester berjalan, bebas konflik jadwal, dan memenuhi prasyarat.

---

### C. Modul 3: Jadwal Kuliah, Ruangan & Conflict Resolver UI (Minggu 7–8)
1. **Buka Halaman Dashboard Penjadwalan (`GET /dashboard`):**
   - Akses `http://127.0.0.1:8000/dashboard` pada browser.
   - Halaman menampilkan daftar seluruh jadwal kuliah aktif, deteksi konflik 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`), serta log notifikasi *Observer Pattern*.
2. **Perubahan Jadwal & Integrasi KRS (`PUT /api/schedules/{id}`):**
   - Saat Admin mengubah jadwal kuliah, sistem secara otomatis:
     - Memvalidasi ulang seluruh KRS mahasiswa yang mengambil mata kuliah tersebut menggunakan data `JadwalKuliah` terbaru.
     - Menandai KRS yang terdampak dengan `needs_review = True` dan mencatat transisi di `krs_transition`.
     - Mengirimkan notifikasi otomatis ke Mahasiswa (`StudentObserver`), Dosen (`LecturerObserver`), dan Admin (`AdminObserver`).
3. **Rekomendasi Jadwal Alternatif (`POST /api/schedules/{id}/suggestions`):**
   - Memberikan maksimal **3 alternatif slot jadwal** (hari, jam, ruangan) yang bebas bentrok dan memenuhi kapasitas ruangan.

---

### D. Modul 4: Manajemen Nilai, Form Edit Nilai, & Transkrip PDF (Minggu 9–10)
1. **Buka Halaman Web Manajemen Nilai (`GET /grades-ui`):**
   - Akses `http://127.0.0.1:8000/grades-ui` pada browser.
2. **Form Input Nilai Baru:**
   - Dosen mengisi NIM, ID Mata Kuliah, Semester, Nilai Huruf (`A`/`B`/`C`/`D`/`E`), dan Persentase Kehadiran.
   - Jika kehadiran $< 75\%$, sistem menolak input nilai dengan pesan error yang jelas (`400 Bad Request`).
3. **Form Edit Nilai Mahasiswa (P5):**
   - Pada kartu **"Edit Nilai Mahasiswa (Audit Trail Otomatis)"** di `/grades-ui`, isi `ID Riwayat Nilai (grade_id)`, pilih `Nilai Huruf Baru`, isi `Diubah Oleh`, dan isi **`Alasan Perubahan Nilai (Wajib)`**.
   - Klik **Simpan Perubahan Nilai**. Sistem memanggil `PUT /api/grades/update/{grade_id}`, memicu SQLite Trigger `trg_grade_history_update`, dan langsung menampilkan entri perubahan pada tabel **Audit Trail Perubahan Nilai**.
4. **Cek IPS/IPK & Unduh PDF Transkrip Akademik:**
   - Masukkan NIM pada bagian **Cek IPK & Transkrip PDF**, lalu klik **Unduh Transkrip PDF Resmi** (`/api/grades/transcript/{nim}/pdf`).
   - File PDF resmi akan terunduh lengkap dengan Logo Universitas, Biodata Mahasiswa, Tabel Nilai per Semester, Rekap IPS/IPK (nilai `D` bobot `1.0` dihitung lulus, mata kuliah berulang diambil nilai tertinggi), Predikat Kelulusan, dan blok tanda tangan **Dekan**.

---

### E. Modul 5: Keuangan SPP, APScheduler, & Webhook Payment Gateway (Minggu 11)
1. **Buka Halaman Dashboard Keuangan (`GET /finance-dashboard`):**
   - Akses `http://127.0.0.1:8000/finance-dashboard` pada browser.
   - Menampilkan ringkasan tagihan SPP, tingkat kolektibilitas (*collection rate*) per program studi, tren pembayaran bulanan, daftar mahasiswa menunggak (`overdue`), dan laporan **AI Financial Insights**.
2. **Penjadwalan Otomatis (`APScheduler`) & Eksekusi Manual:**
   - Cek status scheduler kapan saja di `GET /api/billing/scheduler/status`.
   - Untuk menguji pembuatan tagihan semester atau pengiriman pengingat keterlambatan tanpa menunggu jadwal cron awal semester:
     - Panggil `POST /api/billing/generate-semester` dengan body `{"semester": "2025-1", "tahun": 2025}`.
     - Panggil `POST /api/billing/reminders/run` untuk memicu job pengingat tagihan `overdue`.
3. **Pembayaran SPP & Pembukaan Blokir KRS Otomatis:**
   - Pembayaran dapat diproses melalui `POST /api/payments/process` atau melalui simulasi Webhook Payment Gateway `POST /api/payments/webhook` dengan header `X-Webhook-Signature`.
   - Begitu tagihan `overdue` dilunasi (`status == "paid"`), blokir pengisian dan submit KRS mahasiswa yang bersangkutan otomatis terbuka kembali.
