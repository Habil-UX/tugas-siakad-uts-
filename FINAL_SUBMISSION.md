# LAPORAN AKHIR AUDIT & PENGEMBANGAN SIAKAD (MINGGU 3–11)

## 1. Identitas Proyek
- **Mata Kuliah**: Pemrograman Berorientasi Objek untuk Sistem AI Agenik (B)
- **Nama**: HABIL PRATAMA YAHYA
- **NIM**: 251635001
- **Program Studi**: Sistem Informasi

---

## 2. Ringkasan Eksekutif
Proyek Sistem Informasi Akademik (SIAKAD) telah diaudit secara menyeluruh, diperbaiki, dan disempurnakan untuk memenuhi seluruh kriteria tugas dosen dari **Minggu 3 sampai Minggu 11** tanpa mengganti teknologi inti (**Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, SQLite, Pydantic, ReportLab, Pytest, Hypothesis**) dan tanpa merusak data existing pada `pmb.db`.

---

## 3. Kondisi Awal vs Hasil Akhir Setelah Audit

| Aspek | Kondisi Awal (Pra-Audit) | Kondisi Akhir (Pasca-Audit & Implementasi) |
|---|---|---|
| **Alembic Migration dari DB Kosong** | **GAGAL** (`duplicate column name: version` pada `50747fbd5ef0` dan error `drop_constraint` pada `a8c2d6e9f103`). | **LULUS 100%** untuk siklus `upgrade head -> downgrade base -> upgrade head` dari DB kosong maupun pada `pmb.db`. |
| **Seed Data Referensi** | Tabel `skala_nilai` pada `pmb.db` kosong (0 baris). | Ter-seed otomatis secara non-destruktif (`skala_nilai` A–E, `program_studi` + `tarif_spp`, `jalur_masuk`, `payment_method`, `app_user`). |
| **Autentikasi & Otorisasi (RBAC)** | Belum tersedia autentikasi user. | Tersedia autentikasi token bertanda tangan **HMAC-SHA256** (`/api/auth/login`, `/api/auth/register`, `/api/auth/me`) dan RBAC (`admin`, `dosen`, `mahasiswa`). |
| **Modul PMB (Minggu 3–4)** | Validasi input mengembalikan 422; belum ada test konkurensi NIM pada DB file. | Validasi input mengembalikan **HTTP 400** sesuai PDF dosen; `generate_nim` mendukung 3/4 argumen; lulus test konkurensi multi-koneksi. |
| **Modul KRS (Minggu 5–6)** | Duplikat MK tertutup oleh `ConflictValidator`; belum ada strategi *collect-all* pada `build_chain`; `submit_krs` belum menolak KRS kosong; `test_schedule_conflict` masih kosong (`pass`). | `build_chain(stop_on_first_error)` mendukung *fail-fast* & *collect-all*; `DuplicateValidator` akurat; prasyarat mengecek semester sebelumnya + endpoint `EXPLAIN QUERY PLAN`; menolak KRS kosong; `test_schedule_conflict` & 12 transisi ilegal teruji. |
| **Modul Jadwal & Ruangan (Minggu 7–8)** | Belum ada endpoint `PUT`/`DELETE`/`conflicts` jadwal dan `/api/admin/scheduling/dashboard`; objek jadwal *expired* pasca-notifikasi Observer. | Endpoint CRUD lengkap + `/api/schedules/conflicts` + `/api/admin/scheduling/dashboard`; deteksi 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`); log audit `KrsTransition` saat KRS ditandai `needs_review`. |
| **Modul Nilai & Transkrip (Minggu 9–10)** | IPK masih memasukkan MK tidak lulus ke penyebut; PDF belum memuat logo, angkatan, kolom mutu, dan TTD Dekan; belum ada form web nilai. | `GPACalculator.calculate_ipk` hanya menghitung MK lulus (`>= 2.0`) & nilai tertinggi jika diulang (diuji dengan 12+ kasus); PDF memuat Logo Universitas, Angkatan, Mutu, & TTD Dekan; form web tersedia di `/grades-ui`. |
| **Modul Keuangan SPP (Minggu 11)** | Belum ada billing semester massal, scheduler reminder, `process_payment`, webhook payment gateway, blokir KRS karena tunggakan, dashboard keuangan, & AI financial report. | Seluruh fitur Minggu 11 tersedia lengkap: `generate_semester_billing` (idempotent), `BillingScheduler`, `process_payment`, `handle_webhook` (HMAC signature + idempotent + receipt log), blokir KRS otomatis saat `overdue`, `/finance-dashboard`, & `/api/billing/ai-report`. |
| **Pengujian & Coverage** | 318 test passed (1 test kosong `pass`). | **357 test passed, 0 failed**, **99% code coverage** (`2,374` statements, termasuk seluruh perbaikan P1–P5). |

---

## 4. Checklist Pemenuhan Kriteria Dosen (Minggu 3–11)

### Minggu 3–4: Modul PMB
- [x] Tabel `calon_mahasiswa`, `program_studi`, `jalur_masuk`, dan `nim_sequences` dengan PK, FK, unique email, validasi nomor telepon Indonesia, enum status (`pending`, `approved`, `rejected`), `created_at`, `approved_at`.
- [x] Migrasi Alembic mendukung `upgrade` dan `downgrade` dari database kosong tanpa merusak data existing.
- [x] Endpoint `POST /api/pmb/register`, `GET /api/pmb/status/{id}`, `PUT /api/pmb/approve/{id}`, `PUT /api/pmb/reject/{id}`, `GET /api/pmb/stats` (dengan `GROUP BY`).
- [x] Generator NIM berformat `YYYY[KODE]-XXXX`, unik, sequential, idempotent, dan aman dari race condition.
- [x] Unit & integration test lengkap dengan coverage > 80% (aktual: 100% pada modul PMB).

### Minggu 5–6: Modul KRS
- [x] Tabel `matakuliah`, `krs`, `krs_detail`, `prerequisite`, `skala_nilai`, `krs_transition`.
- [x] `KRSManager` service: `add_course`, `remove_course`, `validate_krs`, `submit_krs`, `approve_krs`, `revise_krs`, `get_krs`.
- [x] Chain of Responsibility dengan `SKSValidator`, `PrerequisiteValidator`, `ConflictValidator`, `DuplicateValidator`, dan `build_chain(stop_on_first_error=True/False)`.
- [x] State Machine `KRSStatus` (`DRAFT -> SUBMITTED -> APPROVED / REVISION -> SUBMITTED`) dengan penolakan 12 transisi ilegal dalam satu transaksi database.
- [x] Optimasi query prasyarat dengan `NOT EXISTS`, composite index `ix_riwayat_nilai_nim_mk_skala`, dan pembuktian `EXPLAIN QUERY PLAN`.
- [x] Pengujian Hypothesis (1000 kombinasi SKS) dan parametrized test.

### Minggu 7–8: Modul Jadwal & Ruangan
- [x] CRUD jadwal kuliah (`POST`, `GET`, `PUT`, `DELETE /api/schedules`) dan validasi kapasitas ruangan.
- [x] Deteksi bentrok 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`) dengan interval `[start, end)`.
- [x] Observer Pattern (`ScheduleSubject`, `StudentObserver`, `LecturerObserver`, `AdminObserver`, `NotificationManager`) yang hanya mengirim notifikasi setelah transaksi commit berhasil.
- [x] Conflict Resolver UI (`/dashboard` & `/api/admin/scheduling/dashboard`) dan rekomendasi 3 alternatif jadwal (`ReschedulingService`).
- [x] Integrasi KRS: menandai KRS terdampak (`needs_review = True`), mencatat `KrsTransition`, dan mengirim notifikasi.

### Minggu 9–10: Modul Nilai & Transkrip
- [x] Input dan edit nilai mahasiswa dengan validasi presensi >= 75%.
- [x] Audit trail otomatis pada tabel `grade_history` menggunakan database trigger `trg_grade_history_update` dan view `v_grade_history`.
- [x] `GPACalculator`: `calculate_ips(nim, semester)`, `calculate_ipk(nim)`, `get_transcript(nim)` (hanya menghitung MK lulus, nilai tertinggi untuk MK ulang, kembali 0.0 jika belum ada nilai).
- [x] PDF Transkrip Akademik (`ReportLab`) memuat Logo Universitas, judul `TRANSKRIP AKADEMIK`, NIM, Nama, Program Studi, Angkatan, tabel nilai per semester beserta kolom Mutu, Total SKS, IPK, Predikat Kelulusan, dan tanda tangan Dekan.
- [x] Halaman Form Web Input Nilai (`/grades-ui`) dan 12+ kasus pengujian perhitungan IPK.

### Minggu 11: Modul Keuangan SPP
- [x] Tabel `billing`, `payment`, `payment_method` dengan status `unpaid`, `partial`, `paid`, `overdue`.
- [x] Generator tagihan SPP per semester (`generate_semester_billing`) yang idempotent berdasarkan tarif program studi, perhitungan denda keterlambatan, dan scheduled job reminder (`BillingScheduler`).
- [x] `process_payment(billing_id, amount, method)` yang transaksional dan mencegah pembayaran ganda.
- [x] `handle_webhook(payload, signature)` dengan verifikasi signature HMAC-SHA256, idempotency `transaction_id`, dan simulasi pengiriman receipt via email.
- [x] Pembatasan pengisian KRS di backend bagi mahasiswa yang memiliki tunggakan (`overdue`), serta pembukaan blokir otomatis setelah lunas.
- [x] Dashboard Keuangan (`/api/billing/dashboard` & `/finance-dashboard`) dan laporan JSON AI Financial Report (`/api/billing/ai-report`) berbasis data aktual database.
