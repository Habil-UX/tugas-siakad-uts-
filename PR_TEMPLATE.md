# Pull Request Template & OPAR (Minggu 3–11)

## Ringkasan Pull Request
Pengembangan, audit menyeluruh, perbaikan bug, dan integrasi akhir **Sistem Informasi Akademik (SIAKAD)** mencakup seluruh kriteria tugas dosen **Minggu 3 sampai Minggu 11** (Modul PMB, Modul KRS, Modul Jadwal & Ruangan, Modul Nilai & Transkrip PDF, serta Modul Keuangan SPP & Webhook).

---

## OPAR (Objective, Problem, Action, Result)

### 1. Objective (Tujuan)
Menyediakan sistem backend dan dashboard akademik terintegrasi dari Minggu 3 hingga Minggu 11 yang memenuhi seluruh acceptance criteria dosen, memiliki integritas skema database dan migrasi Alembic yang dapat dijalankan bolak-balik (*upgrade* & *downgrade*) dari database kosong, menerapkan pola desain OOP (*Chain of Responsibility*, *State Machine*, *Observer Pattern*, *Constraint Satisfaction Problem*), menjaga keamanan API (HMAC Authentication, RBAC, dan Webhook Signature Verification), serta dibuktikan melalui rangkaian pengujian otomatis (Unit, Integration, Concurrency, dan Property-Based Testing).

### 2. Problem (Masalah yang Ditemukan Saat Audit)
1. **Database & Migrasi Alembic**: Migrasi `alembic upgrade head` dari database kosong gagal akibat duplikasi penambahan kolom `krs.version` pada revisi `95417f7b9188` dan `50747fbd5ef0`, serta kegagalan `alembic downgrade base` pada revisi `a8c2d6e9f103` karena nama constraint foreign key tidak ditemukan di SQLite. Selain itu, tabel referensi `skala_nilai` pada database utama belum memiliki seed data.
2. **Modul PMB (Minggu 3–4)**: Validasi format telepon/email mengembalikan HTTP 422 bawaan FastAPI (sementara dokumen tugas meminta HTTP 400), dan belum tersedia pengujian konkurensi pembuatan NIM pada database berbasis file.
3. **Modul KRS (Minggu 5–6)**: `ConflictValidator` mengecek mata kuliah terhadap dirinya sendiri sehingga error duplikasi mata kuliah tertutupi oleh pesan bentrok jadwal; `build_chain()` belum mendukung pilihan strategi *fail-fast* vs *collect-all* secara eksplisit; `PrerequisiteValidator` belum memfilter kelulusan pada semester sebelumnya dan belum mengekspos bukti `EXPLAIN QUERY PLAN`; `submit_krs` belum menolak KRS kosong; serta `test_schedule_conflict` pada `tests/test_krs.py` masih kosong (`pass`).
4. **Modul Jadwal & Ruangan (Minggu 7–8)**: Endpoint `PUT /api/schedules/{id}`, `DELETE /api/schedules/{id}`, `GET /api/schedules/conflicts`, dan `GET /api/admin/scheduling/dashboard` (yang dipanggil oleh UI `/dashboard`) belum tersedia; serta pemanggilan `db.commit()` di dalam `NotificationManager` membuat objek `JadwalKuliah` *expired* saat dikembalikan oleh API.
5. **Modul Nilai & Transkrip (Minggu 9–10)**: Perhitungan IPK pada `GPACalculator` masih memasukkan mata kuliah tidak lulus ke dalam pembagi; PDF transkrip belum memuat Logo Universitas, Angkatan, kolom Mutu, dan area tanda tangan Dekan; serta belum tersedia halaman form web input nilai.
6. **Modul Keuangan SPP & Integrasi KRS (Minggu 11)**: Belum tersedia generator tagihan semester massal yang idempotent, scheduled job reminder otomatis, `process_payment(billing_id, amount, method)`, simulasi webhook dengan verifikasi signature HMAC (`handle_webhook`), pembatasan pengisian KRS bagi mahasiswa yang menunggak (`overdue`), Dashboard Keuangan, dan laporan AI Financial Insights berformat JSON.

### 3. Action (Tindakan Perbaikan & Implementasi)
1. **Perbaikan Migrasi & Seed Data (`T1`)**: Memperbaiki revisi `50747fbd5ef0`, `a8c2d6e9f103`, dan `c0b4e3a8c963`, serta menambahkan revisi `b7e4c1d9a204` yang membuat tabel `app_user`, kolom `program_studi.tarif_spp`, composite index `ix_riwayat_nilai_nim_mk_skala`, serta seed data non-destruktif (`skala_nilai`, `program_studi`, `jalur_masuk`, `payment_method`, `app_user`).
2. **Autentikasi HMAC, RBAC & Validasi HTTP 400 (`T2–T3`)**: Mengimplementasikan autentikasi berbasis HMAC-SHA256 (`app/utils/security.py`, `app/routers/auth.py`), pemeriksaan hak akses peran (`mahasiswa`, `dosen`, `admin`), handler `RequestValidationError` -> HTTP 400, serta pengujian konkurensi generator NIM.
3. **Penyempurnaan KRS & Validator Chain (`T4`)**: Menambahkan parameter `stop_on_first_error` pada `build_chain()`, memperbaiki urutan deteksi `ConflictValidator` vs `DuplicateValidator`, menambahkan pengecekan prasyarat semester sebelumnya + endpoint `EXPLAIN QUERY PLAN`, menolak submit KRS kosong, dan melengkapi pengujian Hypothesis (1000 kombinasi) serta 12 transisi status ilegal.
4. **Penyempurnaan Jadwal, Observer & Conflict Resolver UI (`T5`)**: Melengkapi endpoint CRUD dan deteksi konflik 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`), memperbaiki refresh objek jadwal pasca-notifikasi Observer, mencatat audit `KrsTransition` saat KRS ditandai `needs_review`, dan melengkapi UI `/dashboard`.
5. **Penyempurnaan GPA Calculator, PDF Transkrip & Form Web Nilai (`T6`)**: Memperbarui `GPACalculator` agar hanya menghitung mata kuliah lulus (`bobot >= 2.0`) dan mengambil nilai tertinggi untuk MK ulang, memperbarui template ReportLab dengan logo universitas, angkatan, kolom mutu, dan tanda tangan Dekan, serta menyediakan form web `/grades-ui` dan 12+ skenario pengujian IPK.
6. **Penyempurnaan Keuangan SPP, Webhook & Blokir KRS (`T7–T8`)**: Mengimplementasikan `generate_semester_billing`, `BillingScheduler`, `process_payment`, `handle_webhook` (dengan verifikasi signature HMAC-SHA256, idempotensi `reference_number`, dan simulasi receipt email ke `notification_log`), integrasi blokir KRS otomatis untuk tagihan `overdue`, serta endpoint/UI Dashboard Keuangan (`/api/billing/dashboard`, `/finance-dashboard`) dan AI Financial Report (`/api/billing/ai-report`).

### 4. Result (Hasil Terverifikasi)
- Siklus migrasi `alembic upgrade head -> downgrade base -> upgrade head` berjalan mulus tanpa error baik pada database kosong maupun pada database proyek `pmb.db`.
- Seluruh modul Minggu 3–11 saling terintegrasi dari pendaftaran PMB -> pembuatan NIM -> pengisian/persetujuan KRS -> penjadwalan & notifikasi Observer -> penilaian & PDF transkrip -> penagihan SPP, webhook pembayaran, dan pembatasan KRS.
- Seluruh rangkaian pengujian otomatis lulus (**0 failed**) dengan cakupan kode (*code coverage*) **>= 97%** (melampaui target minimal 80%).

---

## Checklist Verifikasi PR (Minggu 3–11)
- [x] **Minggu 3–4 (PMB)**: Skema 3 tabel + constraint, migrasi upgrade/downgrade teruji, endpoint register/status/approve/reject/stats (`GROUP BY`), NIM generator unik & aman dari race condition, test coverage >= 80%.
- [x] **Minggu 5–6 (KRS)**: Skema 4 tabel + `skala_nilai`, `KRSManager` (`add_course`, `remove_course`, `validate_krs`, `submit_krs`, `approve_krs`, `revise_krs`), 4 Validator *Chain of Responsibility* + `build_chain`, *State Machine* + log transisi, query prasyarat + `EXPLAIN QUERY PLAN`, Hypothesis test 1000 kombinasi + 12 transisi ilegal.
- [x] **Minggu 7–8 (Jadwal & Ruangan)**: CRUD jadwal, deteksi bentrok 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`) dengan interval `[start, end)`, capacity check, *Observer Pattern* + `NotificationManager`, Conflict Resolver UI + 3 rekomendasi jadwal alternatif, integrasi invalidasi KRS (`needs_review`).
- [x] **Minggu 9–10 (Nilai & Transkrip)**: Input/edit nilai oleh dosen, validasi presensi >= 75%, Audit Trail (`grade_history` via trigger & view), `calculate_ips` / `calculate_ipk` / `get_transcript`, PDF transkrip resmi dengan logo & TTD Dekan, 12+ test kasus IPK.
- [x] **Minggu 11 (Keuangan SPP)**: Skema `billing`, `payment`, `payment_method`, generator tagihan semester idempotent, perhitungan denda, reminder otomatis (`BillingScheduler`), `process_payment` & `handle_webhook` (HMAC signature + idempotent + receipt log), blokir KRS untuk mahasiswa menunggak, Dashboard Keuangan & AI Financial Report JSON.
