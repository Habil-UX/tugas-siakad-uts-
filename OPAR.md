# DOKUMENTASI OPAR (OBSERVATION, PROBLEM, ACTION, RESULT)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 3–11  
**Tanggal:** 17 November 2026

Dokumen ini mencatat siklus **OPAR (Observation, Problem, Action, Result)** yang ditemukan dan diselesaikan selama proses pengembangan, audit menyeluruh, dan penyempurnaan prioritas P1–P5 pada seluruh modul SIAKAD.

---

## OPAR 1 — Migrasi Database Alembic & Integritas Rollback (Minggu 3–11)

- **Observation (Observasi):**
  Saat menguji siklus penuh `alembic upgrade head` $\rightarrow$ `alembic downgrade base` $\rightarrow$ `alembic upgrade head` pada database SQLite kosong, eksekusi berhenti dengan error pada dua file revisi menengah (`50747fbd5ef0` dan `a8c2d6e9f103`).
- **Problem (Masalah):**
  1. Revisi `c0b4e3a8c963` sudah membuat kolom `version` pada tabel `krs`, tetapi revisi berikutnya (`50747fbd5ef0`) mencoba menambahkan kolom `version` lagi tanpa memeriksa keberadaan kolom (`duplicate column name: version`).
  2. Fungsi `downgrade()` pada revisi `a8c2d6e9f103` memanggil `batch_op.drop_constraint('fk_calon_mahasiswa_dosen_pa_id_dosen')`, padahal pada SQLite foreign key tersebut dibuat secara inline tanpa nama constraint eksplisit sehingga memicu `ValueError: No such constraint`.
- **Action (Tindakan):**
  1. Menambahkan pemeriksaan `sqlalchemy.inspect(bind).get_columns("krs")` secara idempotent pada `50747fbd5ef0`.
  2. Memeriksa daftar nama foreign key aktual pada `a8c2d6e9f103` sebelum memanggil `drop_constraint`, dan menambahkan revisi `b7e4c1d9a204` untuk tabel `app_user`, kolom `program_studi.tarif_spp`, index `ix_riwayat_nilai_nim_mk_skala`, serta *seed data* referensi non-destruktif (`INSERT OR IGNORE`).
- **Result (Hasil):**
  Siklus penuh `upgrade head` $\rightarrow$ `downgrade base` $\rightarrow$ `upgrade head` berjalan 100% bersih tanpa error dan tanpa kehilangan data pada `pmb.db`.

---

## OPAR 2 — True Multi-Thread Concurrency pada Generator NIM (Minggu 3–4 & P4)

- **Observation (Observasi):**
  Pembuatan NIM menggunakan tabel `nim_sequences` dengan `with_for_update()` bekerja pada PostgreSQL/MySQL, tetapi pada SQLite mode transaksi default (`DEFERRED`) masih berisiko mengalami `OperationalError: database is locked` atau kondisi *race condition* ketika beberapa thread melakukan `SELECT` sebelum `UPDATE` secara bersamaan.
- **Problem (Masalah):**
  Pengujian konkurensi menggunakan `ThreadPoolExecutor(max_workers=8)` dan `threading.Barrier(8)` pada database SQLite berbasis file memerlukan akuisisi *write lock* sejak awal transaksi dan penanganan *lock contention*.
- **Action (Tindakan):**
  1. Mengatur `PRAGMA busy_timeout = 30000` dan `PRAGMA foreign_keys = ON` melalui event listener koneksi SQLAlchemy di `app/database.py`.
  2. Menggunakan `BEGIN IMMEDIATE` pada koneksi SQLite yang dikombinasikan dengan *threading lock* dan mekanisme *retry* eksponensial pada `app/services/pmb_service.py`.
- **Result (Hasil):**
  Pengujian paralel 8 worker thread (`test_concurrent_nim_generation_multithread_file_db`) menghasilkan 8 NIM berurutan yang 100% unik (`2025TIF-0001` s/d `2025TIF-0008`) tanpa nomor ganda dan tanpa kegagalan lock.

---

## OPAR 3 — Chain of Responsibility, Query Prasyarat, & Integrasi JadwalKuliah pada KRS (Minggu 5–6 & P3)

- **Observation (Observasi):**
  Saat menguji penambahan mata kuliah duplikat dan perubahan jadwal kuliah pada modul KRS:
  1. Penambahan mata kuliah yang sama sempat tertangkap oleh `ConflictValidator` (karena jamnya sama dengan dirinya sendiri) sebelum mencapai `DuplicateValidator`.
  2. Satu mata kuliah (`Matakuliah`) dapat memiliki beberapa kelas/sesi jadwal pada tabel `JadwalKuliah`, sehingga validasi konflik jadwal KRS tidak boleh hanya bergantung pada atribut statis di tabel `Matakuliah`.
- **Problem (Masalah):**
  - `DuplicateValidator` tertutup oleh `ConflictValidator` jika MK dibandingkan dengan dirinya sendiri.
  - Perubahan jadwal pada `JadwalKuliah` harus langsung terbaca oleh validator KRS tanpa menimpa master `Matakuliah`, serta harus menandai KRS terdampak dengan `needs_review = True` dan mencatat `KrsTransition`.
- **Action (Tindakan):**
  1. Mengecualikan pembandingan `detail.matakuliah_id == new_mk.id` di dalam `ConflictValidator` sehingga duplikasi MK ditangani secara presisi oleh `DuplicateValidator`.
  2. Memperbarui `ConflictValidator._get_course_schedules` agar membaca slot aktif langsung dari tabel `JadwalKuliah` (dengan fallback ke `Matakuliah` jika belum ada jadwal di `JadwalKuliah`).
  3. Memperbarui `SchedulingService._invalidate_krs` untuk melakukan `db.flush()`, memvalidasi ulang KRS terdampak, menyetel `needs_review = True`, mencatat `KrsTransition`, dan mengirim notifikasi Observer setelah `db.commit()`.
- **Result (Hasil):**
  Validasi KRS berjalan akurat dalam mode *fail-fast* (`add_course`) maupun *collect-all* (`validate_krs`), query prasyarat terindeks (`SEARCH ... USING INDEX ix_riwayat_nilai_nim_mk_skala` pada `EXPLAIN QUERY PLAN`), dan perubahan jadwal terintegrasi penuh dengan KRS.

---

## OPAR 4 — Objek ORM Expired Pasca-Notifikasi Observer Pattern (Minggu 7–8)

- **Observation (Observasi):**
  Pada saat membuat jadwal baru melalui `POST /api/schedules`, respons JSON sempat mengembalikan objek kosong `{}` meskipun baris jadwal berhasil tersimpan di database.
- **Problem (Masalah):**
  Setelah `SchedulingService.create_schedule` melakukan `self.db.commit()` dan `self.db.refresh(candidate)`, metode `self._trigger_observers(...)` memanggil `NotificationManager.send_notification(...)` yang kembali memanggil `db.commit()` pada session yang sama. Di SQLAlchemy, `commit()` kedua tersebut membuat atribut `candidate` berstatus *expired*.
- **Action (Tindakan):**
  Menambahkan `if isinstance(self.db, Session): self.db.refresh(candidate)` tepat setelah `self._trigger_observers(...)` selesai pada `create_schedule` dan `update_schedule`.
- **Result (Hasil):**
  Endpoint `POST /api/schedules` dan `PUT /api/schedules/{id}` mengembalikan seluruh atribut jadwal (`id`, `matakuliah_id`, `ruangan_id`, `dosen_id`, `hari`, `jam_mulai`, `jam_selesai`, `status`) secara lengkap sekaligus mencatat notifikasi ke `notification_log`.

---

## OPAR 5 — Konsistensi Nilai D vs C pada IPK/Transkrip dan Prasyarat (Minggu 9–10, P2 & P5)

- **Observation (Observasi):**
  Dalam aturan akademik, nilai `D` (bobot `1.0`) merupakan nilai lulus untuk mata kuliah umum (sedangkan `E` dengan bobot `0.0` tidak lulus), namun untuk memenuhi **prasyarat** mata kuliah lanjutan tetap diwajibkan minimal nilai `C` (bobot `2.0`).
- **Problem (Masalah):**
  Jika `GPACalculator` menggunakan batas `2.0`, maka mata kuliah bernilai `D` tidak dihitung ke dalam SKS lulus dan IPK/Transkrip menjadi tidak sinkron dengan status kelulusan nilai `D`. Selain itu, halaman `/grades-ui` awalnya baru memiliki form input nilai baru dan belum menyediakan form edit nilai yang terhubung ke `PUT /api/grades/update/{grade_id}`.
- **Action (Tindakan):**
  1. Menetapkan `GPACalculator.MINIMUM_LULUS = 1.0` sehingga nilai `A (4.0)`, `B (3.0)`, `C (2.0)`, dan `D (1.0)` dihitung sebagai lulus dalam IPS, IPK, dan PDF Transkrip (dengan tetap mengambil nilai tertinggi jika mata kuliah diulang), sedangkan `PrerequisiteValidator` tetap mensyaratkan `bobot >= 2.0 (C)`.
  2. Menambahkan form **Edit Nilai Mahasiswa** pada `/grades-ui` yang mengirim request `PUT /api/grades/update/{grade_id}` dengan validasi wajib mengisi alasan perubahan (`reason`) dan langsung memperbarui tabel Audit Trail.
- **Result (Hasil):**
  Perhitungan IPS, IPK (14 skenario uji parametrik), Transkrip PDF, pengulangan mata kuliah (`D` diulang menjadi `B` mengambil `B`), validasi prasyarat (`D` ditolak sebagai prasyarat), dan form edit nilai di `/grades-ui` berjalan 100% konsisten.

---

## OPAR 6 — Integrasi APScheduler, Webhook HMAC, & Blokir KRS atas Tunggakan SPP (Minggu 11 & P1)

- **Observation (Observasi):**
  Modul keuangan membutuhkan penjadwalan otomatis pembuatan tagihan semester dan pengingat keterlambatan (`overdue`), pemrosesan webhook payment gateway yang aman dan idempotent, serta integrasi langsung dengan pembatasan KRS.
- **Problem (Masalah):**
  1. Scheduler perlu diintegrasikan dengan lifecycle FastAPI (`lifespan`) menggunakan `APScheduler` (`BackgroundScheduler` + `CronTrigger`) tanpa berjalan ganda saat menggunakan `uvicorn --reload`.
  2. Webhook harus menolak signature palsu (`401 Unauthorized`) dan menangani pengiriman ulang `transaction_id` yang sama secara idempotent (`200 OK` tanpa menduplikasi pembayaran).
- **Action (Tindakan):**
  1. Mengimplementasikan `BillingScheduler` dengan `BackgroundScheduler` dan `CronTrigger` di `app/services/scheduler_service.py`, mengintegrasikannya dengan `lifespan` di `app/main.py`, serta menyediakan endpoint `GET /api/billing/scheduler/status` dan trigger manual `POST /api/billing/generate-semester` & `POST /api/billing/reminders/run`.
  2. Mengimplementasikan verifikasi HMAC-SHA256 `hmac.compare_digest` dan pengecekan idempotency `reference_number` pada `PaymentService.handle_webhook`, serta pengecekan tunggakan `overdue` pada `KRSManager._ensure_no_overdue_billing`.
- **Result (Hasil):**
  Seluruh alur Keuangan SPP, APScheduler, Webhook HMAC, pembatasan KRS saat `overdue`, dan pembukaan blokir otomatis saat `paid` berjalan sempurna dan teruji pada 357 automated tests.
