# LAPORAN PENGEMASAN MINGGUAN SIAKAD (`WEEKLY_SUBMISSION_REPORT.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 3–11  
**Tanggal Pembuatan & Verifikasi:** 17 November 2026  
**Baseline Acuan:** `FINAL_SUBMISSION/` & `FINAL_SUBMISSION_SIAKAD.zip` (Frozen Codebase)

---

## 1. Ringkasan 7 Paket ZIP Mingguan (`PENGUMPULAN_SIAKAD/`)

Seluruh **7 file ZIP mingguan** telah dibuat secara selektif sesuai pembagian tugas dosen tanpa mengubah kode sumber project utama, telah dilengkapi `README.md` mandiri (11 bagian lengkap) di masing-masing ZIP, serta telah diekstrak dan diuji secara terpisah menggunakan `pytest`:

| Urutan | Nama File ZIP | Ukuran ZIP | Jumlah File di Dalam ZIP | Hasil Pengujian Mandiri (`pytest`) | Uji Ekstraksi (`testzip`) | Status |
|---:|---|---:|---:|---|---|---|
| 1 | `MINGGU_3.zip` | `38.578` B | 41 file | **`7 passed in 0.76s`** | `OK (None)` | **VERIFIED** |
| 2 | `MINGGU_4.zip` | `48.645` B | 45 file | **`17 passed in 1.43s`** | `OK (None)` | **VERIFIED** |
| 3 | `MINGGU_5.zip` | `60.393` B | 54 file | **`36 passed in 2.49s`** | `OK (None)` | **VERIFIED** |
| 4 | `MINGGU_6.zip` | `69.666` B | 59 file | **`75 passed in 3.27s`** | `OK (None)` | **VERIFIED** |
| 5 | `MINGGU_7-8.zip` | `94.808` B | 71 file | **`53 passed in 1.34s`** | `OK (None)` | **VERIFIED** |
| 6 | `MINGGU_9-10.zip` | `70.818` B | 58 file | **`73 passed in 3.16s`** | `OK (None)` | **VERIFIED** |
| 7 | `MINGGU_11.zip` | `116.112` B | 77 file | **`89 passed in 6.17s`** | `OK (None)` | **VERIFIED** |

---

## 2. Matriks Verifikasi Requirement Dosen per Minggu

| Minggu | Requirement Dosen | File Implementasi | ZIP Tujuan | Bukti Testing | Status |
|---|---|---|---|---|---|
| **Minggu 3** | Skema 3 tabel utama PMB (`program_studi`, `jalur_masuk`, `calon_mahasiswa`) + relasi Foreign Key & constraint SQLAlchemy 2.0 | `app/models/program_studi.py`, `app/models/jalur_masuk.py`, `app/models/calon_mahasiswa.py` | `MINGGU_3.zip` | `tests/test_pmb_register.py::test_register_success` (`7 passed`) | **VERIFIED** |
| **Minggu 3** | Migrasi database Alembic: `upgrade` dan `downgrade` teruji tanpa error | `alembic/env.py`, `alembic/versions/c0b4e3a8c963_*.py`, `a8c2d6e9f103_*.py`, `b7e4c1d9a204_*.py` | `MINGGU_3.zip` | Siklus `alembic upgrade head` $\rightarrow$ `downgrade base` $\rightarrow$ `upgrade head` (`0 error`) | **VERIFIED** |
| **Minggu 3** | Endpoint `POST /api/pmb/register` (status awal `pending`, validasi regex nomor telepon Indonesia `400 Bad Request`) | `app/routers/pmb.py`, `app/services/pmb_service.py`, `app/schemas/pmb.py` | `MINGGU_3.zip` | `test_register_invalid_phone`, `test_register_invalid_prodi`, `test_register_invalid_jalur` (`PASSED`) | **VERIFIED** |
| **Minggu 3** | Penolakan pendaftaran dengan email ganda (`409 Conflict`) | `app/services/pmb_service.py`, `app/routers/pmb.py` | `MINGGU_3.zip` | `tests/test_pmb_register.py::test_register_duplicate_email` (`PASSED`) | **VERIFIED** |
| **Minggu 3** | Dokumentasi `AI_USAGE_LOG.md` beserta prompt terbaik dan penanda kontribusi AI | `AI_USAGE_LOG.md`, `README.md` | `MINGGU_3.zip` | Pemeriksaan dokumen di dalam `MINGGU_3.zip` | **VERIFIED** |
| **Minggu 4** | Endpoint `PUT /api/pmb/approve/{id}` & `PUT /api/pmb/reject/{id}` dengan HTTP `200`, `400`, `404`, `409` | `app/routers/pmb.py`, `app/services/pmb_service.py` | `MINGGU_4.zip` | `tests/test_pmb_week4.py::test_approve_calon_mahasiswa_success`, `test_reject_already_approved_fails` (`17 passed`) | **VERIFIED** |
| **Minggu 4** | Format NIM terdokumentasi (`[TAHUN:4][KODE_PRODI:3]-[SEQ:4]`) & sifat *idempotent* pada `approve` | `app/services/pmb_service.py`, `app/models/nim_sequence.py`, `README.md` | `MINGGU_4.zip` | `test_approve_idempotent`, `test_nim_format_and_sequence` (`PASSED`) | **VERIFIED** |
| **Minggu 4** | Fungsi `generate_nim` aman dari *race condition* (transaksi atomic + `BEGIN IMMEDIATE` + row lock `with_for_update()` + `UNIQUE`) | `app/services/pmb_service.py`, `app/database.py`, `docs/adr/ADR-005-Race-Condition-NIM-Generator.md` | `MINGGU_4.zip` | `test_concurrent_nim_generation` (`test_pmb_week4.py`) & `ThreadPoolExecutor` 8 worker (`PASSED`) | **VERIFIED** |
| **Minggu 4** | Endpoint `GET /api/pmb/status/{id}` & `GET /api/pmb/stats` menggunakan agregasi SQL `GROUP BY` | `app/routers/pmb.py`, `app/services/pmb_service.py` | `MINGGU_4.zip` | `test_get_status_endpoint`, `test_get_stats_endpoint` (`PASSED`) | **VERIFIED** |
| **Minggu 4** | Minimal 5 test + *approve invalid*, coverage $\ge 80\%$, `AI_USAGE_LOG.md`, `OPAR.md`, `PR_TEMPLATE.md` | `tests/test_pmb_register.py`, `tests/test_pmb_week4.py`, `OPAR.md`, `PR_TEMPLATE.md` | `MINGGU_4.zip` | `17 passed in 1.43s` (Coverage modul PMB: **99%–100%**) | **VERIFIED** |
| **Minggu 5** | Model & migrasi tabel KRS (`krs`, `krs_detail`, `prerequisite`, `matakuliah`, `skala_nilai`, `riwayat_nilai`) | `app/models/krs_models.py`, `alembic/versions/c0b4e3a8c963_*.py` | `MINGGU_5.zip` | `tests/test_krs.py` (`36 passed in 2.49s`) | **VERIFIED** |
| **Minggu 5** | `KRSManager` tahap awal (`add_course`, `remove_course`, `validate_krs`) | `app/services/krs_manager.py`, `app/routers/krs.py` | `MINGGU_5.zip` | `test_krs.py`, `test_krs_manager_coverage.py`, `test_krs_manager_exception_coverage.py` (`PASSED`) | **VERIFIED** |
| **Minggu 5** | **Chain of Responsibility** (`build_chain`) dengan 4 validator: `SKSValidator` ($\le 24$), `PrerequisiteValidator` (nilai $\ge$ C di semester sebelumnya), `ConflictValidator` (interval `[start, end)`), `DuplicateValidator` | `app/services/krs/validators.py` | `MINGGU_5.zip` | `test_sks_validator_*`, `test_prerequisite_validator_*`, `test_conflict_validator_*`, `test_duplicate_validator_*` (`PASSED`) | **VERIFIED** |
| **Minggu 5** | Optimasi query prasyarat `NOT EXISTS` + composite index `ix_riwayat_nilai_nim_mk_skala` + bukti `EXPLAIN QUERY PLAN` | `app/services/krs/validators.py`, `app/routers/krs.py`, `docs/adr/ADR-002-Query-Prasyarat.md` | `MINGGU_5.zip` | `GET /api/krs/explain-prerequisite/{nim}/{mk_id}` (`SEARCH ... USING INDEX`) | **VERIFIED** |
| **Minggu 5** | Dokumentasi ADR strategi *fail-fast* vs *collect-all* & urutan rantai validator | `docs/adr/ADR-001-Chain-of-Responsibility.md`, `docs/adr/ADR-003-Strategi-Deteksi-Jadwal-Bentrok.md` | `MINGGU_5.zip` | Pemeriksaan dokumen ADR & `test_validator_exception_coverage.py` (`PASSED`) | **VERIFIED** |
| **Minggu 6** | **State Machine** `KRSStatus` (`DRAFT`, `SUBMITTED`, `APPROVED`, `REVISION`) + `can_transition()` + tabel audit `krs_transition` | `app/services/krs_state_machine.py`, `app/models/krs_models.py` | `MINGGU_6.zip` | `tests/test_state_machine.py` (`75 passed in 3.27s`) | **VERIFIED** |
| **Minggu 6** | `submit_krs` (menolak KRS kosong `400` + `validate_krs`) & `approve_krs`/`revise_krs` (cek kepemilikan Dosen PA `403`/`409` dalam satu transaksi atomic + `version` lock) | `app/services/krs_manager.py`, `app/routers/krs.py`, `docs/adr/ADR-004-State-Machine-KRS-dan-Transaksi.md` | `MINGGU_6.zip` | `test_state_machine.py`, `test_krs_missing_coverage.py` (`PASSED`) | **VERIFIED** |
| **Minggu 6** | *Property-Based Testing* `Hypothesis` (`@settings(max_examples=1000)`) & `@pytest.mark.parametrize` pada seluruh transisi ilegal | `tests/test_state_machine.py` | `MINGGU_6.zip` | `test_krs_sks_property_hypothesis` (1.000 contoh) & 12 kombinasi `test_illegal_transitions` (`PASSED`) | **VERIFIED** |
| **Minggu 6** | Fitur Challenge **AI KRS Recommender** (`POST /api/krs/recommend/{nim}`) berbasis *CSP Backtracking* | `app/services/krs_recommender.py`, `app/routers/krs.py` | `MINGGU_6.zip` | `tests/test_krs_recommendation.py` (`PASSED`) | **VERIFIED** |
| **Minggu 7–8** | Model jadwal, ruangan, dosen, log perubahan & notifikasi (`jadwal_kuliah`, `ruangan`, `dosen`, `schedule_change_log`, `notification_log`) | `app/models/jadwal_models.py` | `MINGGU_7-8.zip` | `tests/test_scheduling.py` (`53 passed in 1.34s`) | **VERIFIED** |
| **Minggu 7–8** | Deteksi konflik 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`) dengan interval `[start, end)` & cek kapasitas ruangan | `app/services/conflict_detector.py`, `app/services/scheduling_service.py`, `docs/adr/ADR-011-Strategi-Deteksi-Konflik.md` | `MINGGU_7-8.zip` | `test_scheduling.py`, `test_conflict_detector_coverage.py` (`PASSED`) | **VERIFIED** |
| **Minggu 7–8** | **Observer Pattern** (`ScheduleSubject`, `StudentObserver`, `LecturerObserver`, `AdminObserver`, `NotificationManager`) | `app/observers/schedule_subject.py`, `app/observers/concrete_observers.py`, `app/observers/notification_manager.py`, `docs/adr/ADR-010-Observer-Pattern.md` | `MINGGU_7-8.zip` | `test_schedule_notifications_saved_to_database` (`test_week7_8_coverage.py` — `PASSED`) | **VERIFIED** |
| **Minggu 7–8** | Rekomendasi **3 alternatif jadwal** bebas bentrok (`ReschedulingService` CSP) & **Conflict Resolver Dashboard** (`/dashboard`) | `app/services/rescheduling_service.py`, `app/routers/schedules.py`, `app/routers/dashboard.py`, `docs/adr/ADR-012-AI-Rescheduling.md` | `MINGGU_7-8.zip` | `test_get_schedules_and_suggestions`, `test_dashboard_endpoint` (`PASSED`) | **VERIFIED** |
| **Minggu 7–8** | Integrasi `JadwalKuliah` sebagai sumber aktual validasi KRS, penandaan `needs_review = True`, & pencatatan `KrsTransition` (P3) | `app/services/scheduling_service.py`, `app/services/krs/validators.py`, `docs/adr/ADR-013-KRS-Invalidation.md` | `MINGGU_7-8.zip` | `test_scheduling_service_extended.py` (`PASSED`) | **VERIFIED** |
| **Minggu 9–10** | Konversi nilai A/B/C/D/E (konsistensi nilai `D` bobot `1.0` lulus di IPK vs minimal `C` bobot `2.0` di prasyarat — P2) & validasi presensi $\ge 75\%$ | `app/services/grade_service.py`, `app/services/gpa_calculator.py` | `MINGGU_9-10.zip` | `tests/test_grade_service.py`, `tests/test_transcript_service.py` (`73 passed in 3.16s`) | **VERIFIED** |
| **Minggu 9–10** | Perhitungan IPS & IPK (`GPACalculator`), kebijakan pengulangan mata kuliah mengambil nilai tertinggi, & minimal 10 kasus uji IPK | `app/services/gpa_calculator.py`, `app/services/transcript_service.py` | `MINGGU_9-10.zip` | `test_calculate_ipk_12_cases` (**14 skenario uji parametrik** — `PASSED`) | **VERIFIED** |
| **Minggu 9–10** | **Audit Trail** otomatis via SQLite Trigger (`trg_grade_history_update`) & View (`v_grade_history`) | `app/models/grade_history.py`, `alembic/versions/0f9e48bbab1f_*.py`, `docs/week9-10/ADR-001-Audit-Trail.md` | `MINGGU_9-10.zip` | `test_update_grade_creates_history_record` (`test_grade_service.py` — `PASSED`) | **VERIFIED** |
| **Minggu 9–10** | **PDF Transkrip Akademik Resmi** (`ReportLab` + Logo + Biodata + Tabel Nilai + TTD Dekan) & halaman `/grades-ui` lengkap dengan **Form Edit Nilai** (P5) | `app/utils/pdf_generator.py`, `app/routers/grades.py`, `app/routers/dashboard.py` | `MINGGU_9-10.zip` | `tests/test_pdf_generator.py`, `tests/test_grade_router_coverage.py` (`PASSED`) | **VERIFIED** |
| **Minggu 11** | Generate billing semester otomatis berdasarkan tarif prodi, jatuh tempo 14 hari (2 minggu), & perhitungan denda keterlambatan | `app/services/billing_service.py`, `app/models/finance_models.py`, `app/routers/billing.py` | `MINGGU_11.zip` | `tests/test_billing_service.py` (`89 passed in 6.17s`) | **VERIFIED** |
| **Minggu 11** | Scheduled job menggunakan **`APScheduler`** (`BackgroundScheduler` + `CronTrigger`) terintegrasi dengan FastAPI `lifespan` (P1) | `app/services/scheduler_service.py`, `app/main.py`, `app/routers/billing.py` | `MINGGU_11.zip` | `test_p1_apscheduler_and_p5_grades_ui_and_finance_integration` (`PASSED`) | **VERIFIED** |
| **Minggu 11** | `process_payment` atomic (`partial`/`paid`) & **Payment Gateway Webhook** (`POST /api/payments/webhook`) dengan verifikasi signature **HMAC-SHA256** & *idempotency* | `app/services/payment_service.py`, `app/utils/security.py`, `app/routers/payment.py`, `docs/adr/ADR-007-*.md` | `MINGGU_11.zip` | `tests/test_payment_service.py`, `tests/test_finance_router_coverage.py`, `tests/test_audit_week3_to_11.py` (`PASSED`) | **VERIFIED** |
| **Minggu 11** | Pembatasan KRS (`403 Forbidden`) akibat tunggakan `overdue` & pembukaan blokir otomatis saat lunas, **Finance Dashboard** (`/finance-dashboard`), & **AI Financial Report JSON** | `app/services/krs_manager.py`, `app/services/billing_service.py`, `app/routers/dashboard.py` | `MINGGU_11.zip` | `tests/test_audit_week3_to_11.py`, `tests/test_finance_router_coverage.py` (`PASSED`) | **VERIFIED** |

---

## 3. Rincian Isi Setiap Paket ZIP

1. **`MINGGU_3.zip` (41 file):**
   - **Kode Aplikasi:** `app/database.py`, `app/main.py`, `app/models/*`, `app/schemas/pmb.py`, `app/schemas/auth.py`, `app/services/pmb_service.py`, `app/routers/pmb.py`, `app/routers/auth.py`, `app/utils/security.py`.
   - **Migrasi & Konfigurasi:** `alembic/*`, `alembic.ini`, `pytest.ini`, `requirements.txt`, `.env.example`.
   - **Pengujian & Dokumentasi:** `tests/conftest.py`, `tests/test_pmb_register.py`, `README.md` (Minggu 3), `AI_USAGE_LOG.md`.
2. **`MINGGU_4.zip` (45 file):**
   - **Kode Aplikasi:** Seluruh modul PMB & NIM Generator (`app/services/pmb_service.py`, `app/models/nim_sequence.py`, `app/routers/pmb.py`, `app/schemas/pmb.py`).
   - **Pengujian & Dokumentasi:** `tests/test_pmb_register.py`, `tests/test_pmb_week4.py`, `docs/adr/ADR-005-Race-Condition-NIM-Generator.md`, `README.md` (Minggu 4), `AI_USAGE_LOG.md`, `OPAR.md`, `PR_TEMPLATE.md`.
3. **`MINGGU_5.zip` (54 file):**
   - **Kode Aplikasi:** Modul KRS & 4 Validator Chain of Responsibility (`app/services/krs/validators.py`, `app/services/krs_manager.py`, `app/models/krs_models.py`, `app/routers/krs.py`, `app/schemas/krs.py`) + dependency PMB.
   - **Pengujian & Dokumentasi:** `tests/test_krs.py`, `tests/test_krs_manager_coverage.py`, `tests/test_krs_manager_exception_coverage.py`, `tests/test_validator_exception_coverage.py`, `docs/adr/ADR-001*.md`, `ADR-002*.md`, `ADR-003*.md`, `README.md` (Minggu 5), `AI_USAGE_LOG.md`, `OPAR.md`.
4. **`MINGGU_6.zip` (59 file):**
   - **Kode Aplikasi:** `app/services/krs_state_machine.py`, `app/services/krs_recommender.py`, `app/services/krs_manager.py`, `app/services/krs/validators.py`, `app/routers/krs.py` + dependency Minggu 5 & PMB.
   - **Pengujian & Dokumentasi:** `tests/test_state_machine.py` (Hypothesis 1.000x & 12 transisi ilegal), `tests/test_krs_recommendation.py`, `tests/test_krs_missing_coverage.py`, `tests/test_krs.py`, `docs/adr/ADR-001` s/d `ADR-004`, `README.md` (Minggu 6), `AI_USAGE_LOG.md`, `OPAR.md`, `PR_TEMPLATE.md`.
5. **`MINGGU_7-8.zip` (71 file):**
   - **Kode Aplikasi:** `app/services/conflict_detector.py`, `app/services/scheduling_service.py`, `app/services/rescheduling_service.py`, `app/observers/schedule_subject.py`, `app/observers/concrete_observers.py`, `app/observers/notification_manager.py`, `app/routers/schedules.py`, `app/routers/dashboard.py` + dependency KRS & PMB.
   - **Pengujian & Dokumentasi:** `tests/test_scheduling.py`, `tests/test_scheduling_service_coverage.py`, `tests/test_scheduling_service_extended.py`, `tests/test_conflict_detector_coverage.py`, `tests/test_week7_8_coverage.py`, `docs/adr/ADR-009` s/d `ADR-013`, `docs/diagram/*`, `README.md` (Minggu 7–8), `AI_USAGE_LOG.md`, `OPAR.md`.
6. **`MINGGU_9-10.zip` (58 file):**
   - **Kode Aplikasi:** `app/services/grade_service.py`, `app/services/gpa_calculator.py`, `app/services/transcript_service.py`, `app/utils/pdf_generator.py`, `app/models/grade_history.py`, `app/routers/grades.py`, `app/routers/dashboard.py`, `app/schemas/grade.py`.
   - **Pengujian & Dokumentasi:** `tests/test_grade_service.py`, `tests/test_grade_service_exception_coverage.py`, `tests/test_grade_router_coverage.py`, `tests/test_transcript_service.py` (14 skenario IPK), `tests/test_pdf_generator.py`, `docs/week9-10/*`, `README.md` (Minggu 9–10), `AI_USAGE_LOG.md`, `OPAR.md`.
7. **`MINGGU_11.zip` (77 file):**
   - **Kode Aplikasi:** `app/services/billing_service.py`, `app/services/payment_service.py`, `app/services/scheduler_service.py`, `app/models/finance_models.py`, `app/routers/billing.py`, `app/routers/payment.py`, `app/routers/dashboard.py`, `app/schemas/finance.py`, `app/utils/security.py` + integrasi `krs_manager.py` & `pmb.db`.
   - **Pengujian & Dokumentasi:** `tests/test_billing_service.py`, `tests/test_payment_service.py`, `tests/test_finance_router_coverage.py`, `tests/test_audit_week3_to_11.py`, `docs/adr/ADR-007*.md`, `docs/week11/*`, `README.md` (Minggu 11), `AI_USAGE_LOG.md`, `OPAR.md`.

---

## 4. Struktur Output Akhir (`PENGUMPULAN_SIAKAD/`)

```text
PENGUMPULAN_SIAKAD/
├── MINGGU_3.zip
├── MINGGU_4.zip
├── MINGGU_5.zip
├── MINGGU_6.zip
├── MINGGU_7-8.zip
├── MINGGU_9-10.zip
├── MINGGU_11.zip
└── WEEKLY_SUBMISSION_REPORT.md
```
