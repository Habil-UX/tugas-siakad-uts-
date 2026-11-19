# AI USAGE LOG — SISTEM INFORMASI AKADEMIK (MINGGU 3–11)

Dokumentasi ini mencatat penggunaan AI secara jujur dan transparan selama pengembangan, audit, perbaikan bug, dan pengujian proyek Sistem Informasi Akademik (SIAKAD), termasuk prompt terbaik per modul, ringkasan hasil AI, verifikasi/revisi manual, serta hasil pengujian aktual.

---

## 1. Ringkasan Log Penggunaan AI per Modul

| Tanggal | Modul | Tujuan Penggunaan AI | Bagian Kode yang Dibantu AI | Revisi / Verifikasi Manual | Hasil Pengujian |
|---|---|---|---|---|---|
| 2026-11-09 | **Minggu 3–4: Modul PMB** | Perancangan skema SQLAlchemy 2.0 (`calon_mahasiswa`, `program_studi`, `jalur_masuk`, `nim_sequences`), validasi nomor telepon Indonesia, endpoint REST API PMB, dan generator NIM aman dari *race condition*. | `app/models/calon_mahasiswa.py`, `app/schemas/pmb.py`, `app/services/pmb_service.py`, `app/routers/pmb.py`, `tests/test_pmb_register.py`, `tests/test_pmb_week4.py` | - Penyesuaian regex nomor telepon Indonesia (`^(\+62|62|0)8[1-9][0-9]{6,11}$`).<br>- Penambahan exception handler agar validasi request mengembalikan HTTP 400 sesuai spesifikasi dosen.<br>- Dukungan signature 3 argumen & 4 argumen pada `generate_nim` serta concurrency test pada SQLite file DB. | Seluruh test PMB & concurrency NIM **PASSED** (Coverage modul PMB: **99%–100%**). |
| 2026-11-10 | **Minggu 5–6: Modul KRS & Challenge** | Implementasi *Chain of Responsibility* (`SKSValidator`, `PrerequisiteValidator`, `ConflictValidator`, `DuplicateValidator`), *State Machine* (`KRSStatus`), query `NOT EXISTS` prasyarat + `EXPLAIN QUERY PLAN`, *Property-Based Testing* (Hypothesis 1000 kombinasi), dan CSP *KRS Recommender*. | `app/services/krs/validators.py`, `app/services/krs_manager.py`, `app/services/krs_state_machine.py`, `app/services/krs_recommender.py`, `tests/test_krs.py`, `tests/test_state_machine.py` | - Perbaikan `ConflictValidator` agar tidak membandingkan MK dengan dirinya sendiri sehingga `DuplicateValidator` tidak tertutup.<br>- Penambahan dua strategi eksplisit pada `build_chain(stop_on_first_error=True/False)` (*fail-fast* vs *collect-all*).<br>- Pengecekan prasyarat pada semester sebelumnya (`RiwayatNilai.semester < krs.semester_akademik`, nilai minimal C / bobot $\ge 2.0$) dan penolakan submit KRS kosong.<br>- Penambahan composite index `ix_riwayat_nilai_nim_mk_skala` dan verifikasi `EXPLAIN QUERY PLAN`. | Hypothesis 1000 kombinasi SKS, 12 transisi ilegal, dan test validator **PASSED**. |
| 2026-11-12 | **Minggu 7–8: Modul Jadwal & Ruangan** | Implementasi deteksi konflik 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`) dengan interval setengah terbuka `[start, end)`, *Observer Pattern* (`ScheduleSubject`, `StudentObserver`, `LecturerObserver`, `AdminObserver`), CSP Rescheduling (3 alternatif), integrasi invalidasi KRS (`needs_review`), dan Conflict Resolver Dashboard. | `app/services/conflict_detector.py`, `app/services/scheduling_service.py`, `app/services/rescheduling_service.py`, `app/observers/`, `app/routers/schedules.py`, `app/routers/dashboard.py` | - Perbaikan bug objek `JadwalKuliah` yang *expired* setelah `NotificationManager.send_notification` melakukan `db.commit()` dengan melakukan `db.refresh` pasca-notifikasi.<br>- Penambahan endpoint `PUT /api/schedules/{id}`, `DELETE /api/schedules/{id}`, `GET /api/schedules/conflicts`, dan `GET /api/admin/scheduling/dashboard`.<br>- Pencatatan audit `KrsTransition` saat jadwal berubah dan menandai KRS terdampak (`needs_review = True`). | Seluruh test CRUD jadwal, 3 dimensi konflik, Observer log, dan dashboard **PASSED**. |
| 2026-11-14 | **Minggu 9–10: Modul Nilai & Transkrip** | Implementasi input/update nilai dengan validasi presensi $\ge 75\%$, Audit Trail otomatis via SQLite Trigger (`trg_grade_history_update`) dan View (`v_grade_history`), perhitungan IPS/IPK (`GPACalculator`), generator PDF transkrip resmi (`ReportLab`), serta form web input & edit nilai (`/grades-ui`). | `app/services/grade_service.py`, `app/services/gpa_calculator.py`, `app/services/transcript_service.py`, `app/utils/pdf_generator.py`, `app/routers/grades.py`, `alembic/versions/0f9e48bbab1f_*.py` | - Konsistensi `GPACalculator` (`MINIMUM_LULUS = 1.0` sehingga nilai A/B/C/D dihitung lulus dan E tidak lulus, dengan pengambilan nilai tertinggi jika mata kuliah diulang) sementara `PrerequisiteValidator` tetap mensyaratkan minimal nilai C (`bobot >= 2.0`).<br>- Penyempurnaan layout PDF transkrip dengan Logo Universitas vektor, Biodata (NIM, Nama, Prodi, Angkatan), kolom Mutu (`SKS x Bobot`), Predikat Kelulusan, dan area tanda tangan **Dekan**.<br>- Pembuatan 14 skenario test parametrik perhitungan IPK. | 14 skenario IPK, trigger audit trail, dan PDF generator **PASSED**. |
| 2026-11-16 | **Minggu 11 & Audit Menyeluruh (Termasuk P1–P5): Modul Keuangan SPP, APScheduler & Integrasi** | Implementasi skema keuangan (`billing`, `payment`, `payment_method`), generator tagihan semester idempotent, perhitungan denda keterlambatan, scheduled job reminder dengan `APScheduler` (`BackgroundScheduler` + `CronTrigger` pada FastAPI lifespan), `process_payment`, simulasi webhook dengan verifikasi signature HMAC-SHA256, pembatasan KRS bagi mahasiswa menunggak (`overdue`), Dashboard Keuangan, AI Financial Report JSON, serta perbaikan P1–P5 hasil Final Verification. | `app/services/billing_service.py`, `app/services/payment_service.py`, `app/services/scheduler_service.py`, `app/utils/security.py`, `app/routers/billing.py`, `app/routers/payment.py`, `app/routers/auth.py`, `alembic/versions/b7e4c1d9a204_*.py`, `tests/test_audit_week3_to_11.py` | - **P1**: Integrasi `APScheduler` (`BackgroundScheduler` + `CronTrigger`) dengan FastAPI `lifespan` dan lock anti-duplikat saat `uvicorn --reload`.<br>- **P2**: Konsistensi kelulusan nilai `D (1.0)` pada `GPACalculator` sementara `PrerequisiteValidator` tetap mensyaratkan minimal `C (2.0)`.<br>- **P3**: Menjadikan `JadwalKuliah` sebagai sumber data jadwal aktual untuk `ConflictValidator` tanpa menimpa `Matakuliah`.<br>- **P4**: Pengamanan transaksi SQLite (`BEGIN IMMEDIATE`, `PRAGMA busy_timeout = 30000`, retry) dan pengujian konkurensi nyata menggunakan `ThreadPoolExecutor` (8 worker paralel dengan `Barrier`).<br>- **P5**: Penambahan form edit nilai (`PUT /api/grades/update/{grade_id}` dengan wajib `reason`) pada `/grades-ui`. | Seluruh test suite (**357 test**) **PASSED** dengan coverage **99%** (`2.374` statements). |

---

## 2. Koleksi Prompt Terbaik per Modul

### A. Prompt Terbaik Minggu 3–4 (Modul PMB & NIM Generator)
```text
Desain skema database dan service PMB menggunakan FastAPI dan SQLAlchemy 2.0:
1. Tabel calon_mahasiswa (id, nama_lengkap, email unique, phone dengan validasi regex nomor Indonesia, tanggal_lahir, alamat, program_studi_id FK, jalur_masuk_id FK, dosen_pa_id FK nullable, status enum pending/approved/rejected, nim unique nullable, created_at, approved_at).
2. Implementasikan endpoint POST /api/pmb/register (status awal pending, 409 jika email duplikat, 400 jika format telepon/input tidak valid), GET /api/pmb/status/{id}, PUT /api/pmb/approve/{id}, PUT /api/pmb/reject/{id}, dan GET /api/pmb/stats (menggunakan agregasi SQL GROUP BY).
3. Buat fungsi generate_nim(tahun, kode_prodi, db) dengan format YYYY[KODE]-[4_DIGIT_SEQ] (contoh: 2025001-0001) yang menggunakan tabel nim_sequences, BEGIN IMMEDIATE pada SQLite, PRAGMA busy_timeout, dan row locking (with_for_update) agar aman dari race condition multi-thread serta bersifat idempotent ketika approve dipanggil berulang.
```

### B. Prompt Terbaik Minggu 5–6 (Modul KRS, Chain of Responsibility & State Machine)
```text
Implementasikan layanan KRSManager dengan pola desain Chain of Responsibility dan State Machine:
1. Buat abstract class Validator dan dataclass ValidationResult, serta 4 validator berurutan:
   - SKSValidator (total SKS <= 24)
   - PrerequisiteValidator (query NOT EXISTS memeriksa kelulusan prasyarat dengan nilai >= C pada semester sebelumnya, dioptimasi dengan composite index dan dibuktikan melalui EXPLAIN QUERY PLAN)
   - ConflictValidator (deteksi irisan interval setengah terbuka [jam_mulai, jam_selesai) pada hari yang sama dari tabel JadwalKuliah aktif, abaikan pembandingan MK dengan dirinya sendiri)
   - DuplicateValidator (cegah pendaftaran MK yang sama dua kali di KRS yang sama)
2. Dukung dua strategi pada build_chain(stop_on_first_error: bool): fail-fast (berhenti pada error pertama saat add_course) dan collect-all (kumpulkan semua error saat validate_krs).
3. Buat enum KRSStatus (DRAFT, SUBMITTED, APPROVED, REVISION) dengan transisi ketat, tolak submit KRS kosong, validasi otorisasi Dosen PA (403 jika bukan PA, 409 jika PA belum ditetapkan), dan catat setiap transisi ke tabel krs_transition dalam satu transaksi database.
4. Buat pengujian Hypothesis (@settings(max_examples=1000)) untuk properti batas maksimal 24 SKS dan parametrized test untuk seluruh 12 transisi status ilegal.
```

### C. Prompt Terbaik Minggu 7–8 (Modul Jadwal, Observer Pattern & CSP Rescheduling)
```text
Implementasikan SchedulingService, ConflictDetector, Observer Pattern, dan ReschedulingService:
1. detect_schedule_conflict & detect_all_schedule_conflicts memeriksa 3 dimensi bentrok pada periode akademik dan hari yang sama menggunakan interval [start, end): room_conflict (ruangan sama), lecturer_conflict (dosen sama), dan time_overlap (mata kuliah/jadwal sama), serta validasi kapasitas ruangan >= jumlah mahasiswa enrolled.
2. Implementasikan ScheduleSubject, StudentObserver, LecturerObserver, AdminObserver, dan NotificationManager yang mencatat notifikasi ke tabel notification_log HANYA setelah transaksi database CRUD jadwal berhasil di-commit.
3. Saat jadwal diubah atau dihapus, validasi ulang KRS dari JadwalKuliah terbaru tanpa menimpa Matakuliah, tandai KRS mahasiswa terdampak (status != APPROVED) dengan needs_review = True, dan catat ke krs_transition.
4. Buat ReschedulingService berbasis Constraint Satisfaction Problem (CSP) yang merekomendasikan maksimal 3 alternatif slot (hari, jam, ruangan, reason) yang kapasitasnya cukup, tidak bentrok, dan memprioritaskan jam pagi/siang.
```

### D. Prompt Terbaik Minggu 9–10 (Modul Nilai, Audit Trail Trigger, IPK & PDF Transkrip)
```text
Implementasikan GradeService, GPACalculator, dan PDF Generator untuk Transkrip Akademik:
1. Validasi input nilai: tolak dengan HTTP 400 jika presensi_persen < 75.0%.
2. Buat tabel grade_history, tabel konteks grade_audit_context, trigger SQLite trg_grade_history_update (AFTER UPDATE OF skala_nilai_id ON riwayat_nilai), serta view v_grade_history untuk mencatat nilai lama, nilai baru, pengubah, waktu, dan alasan perubahan secara otomatis.
3. Implementasikan calculate_ips(nim, semester) dan calculate_ipk(nim) dengan rumus IPK = Σ(SKS × Bobot) / Σ(SKS) yang menghitung mata kuliah lulus (A/B/C/D dengan bobot >= 1.0), mengecualikan nilai E (0.0), mengambil nilai tertinggi apabila mata kuliah diulang, dan mengembalikan 0.0 jika belum ada nilai.
4. Buat generate_transcript_pdf menggunakan ReportLab yang memuat Logo Universitas, judul TRANSKRIP AKADEMIK, NIM, Nama, Program Studi, Angkatan, tabel nilai per semester [Kode MK | Nama MK | SKS | Nilai | Bobot | Mutu | Status], rekap IPS, Total SKS, IPK, Predikat Kelulusan, dan blok tanda tangan Dekan.
```

### E. Prompt Terbaik Minggu 11 (Modul Keuangan SPP, Webhook & Integrasi Blokir KRS)
```text
Implementasikan BillingService, PaymentService, BillingScheduler (APScheduler), Webhook Payment Gateway, dan Integrasi KRS:
1. Buat generate_semester_billing(semester, tahun, semester_start_date) yang bersifat idempotent untuk membuat tagihan SPP seluruh mahasiswa aktif berdasarkan tarif program studi (Teknik: Rp5.000.000, Ekonomi: Rp4.000.000, atau kolom tarif_spp pada program_studi) dengan jatuh tempo 14 hari setelah awal semester dan status awal 'unpaid'.
2. Integrasikan APScheduler (BackgroundScheduler + CronTrigger) dengan FastAPI lifespan untuk menjalankan job generate_semester_billing dan overdue_billing_reminder secara terjadwal maupun on-demand.
3. Implementasikan process_payment(billing_id, amount, method, reference_number) dalam satu transaksi database atomic dengan row lock: buat record payment, hitung total pembayaran berhasil, perbarui status billing ('partial' jika < tagihan, 'paid' jika >= tagihan, 'overdue' jika melewati due_date), cegah pembayaran ganda berdasarkan reference_number, dan catat pengiriman receipt email ke notification_log.
4. Implementasikan handle_webhook(payload, signature) yang memverifikasi HMAC-SHA256 signature, memvalidasi payload, menjamin idempotency untuk transaction_id duplikat, dan memanggil process_payment.
5. Integrasikan dengan KRSManager: blokir add_course dan submit_krs (HTTP 403) apabila mahasiswa memiliki tagihan berstatus 'overdue' yang belum lunas, dan buka kembali akses KRS secara otomatis setelah tagihan dilunasi.
```

---

## 3. Penanda Kontribusi AI pada Perubahan Proyek

Kontribusi AI dan verifikasi manual ditandai secara eksplisit pada dokumen ini, pada [OPAR.md](OPAR.md), serta pada laporan akhir proyek:
- `[AI-Assisted + Human-Verified]` Pembuatan struktur awal model, router, dan layanan dasar.
- `[Human-Audited & Fixed]` Perbaikan konflik migrasi Alembic (`50747fbd5ef0` dan `a8c2d6e9f103`), perbaikan bug objek ORM expired pasca-notifikasi Observer pada `SchedulingService`, perbaikan urutan `ConflictValidator` vs `DuplicateValidator`, konsistensi `GPACalculator.MINIMUM_LULUS = 1.0` vs `PrerequisiteValidator >= 2.0`, integrasi `JadwalKuliah` ke validasi KRS, integrasi `APScheduler` dengan FastAPI `lifespan`, pengamanan konkurensi multi-thread SQLite (`BEGIN IMMEDIATE`), serta implementasi autentikasi HMAC dan webhook signature verification.
