# LAPORAN AKHIR PENGUJIAN & CODE COVERAGE (`FINAL_TEST_REPORT.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 3–11  
**Tanggal Eksekusi:** 17 November 2026  
**Framework Pengujian:** `pytest 8.3.5`, `pytest-cov 6.0.0`, `hypothesis 6.130.5`, `httpx 0.28.1`

---

## 1. Ringkasan Eksekutif Hasil Pengujian

| Metrik Pengujian | Target Dosen | Hasil Aktual | Status |
|---|---|---|---|
| **Total Test Cases** | Mencakup seluruh modul Minggu 3–11 | **357 Test Cases** (27 file test) | **VERIFIED PASS** |
| **Test Passed / Failed** | 0 Failed | **357 Passed, 0 Failed, 0 Error** | **100% LULUS** |
| **Total Code Coverage** | Minimal $\ge 80\%$ | **99% Coverage** (`2.374` statements, `33` missed) | **MELAMPAUI TARGET (+19%)** |
| **Property-Based Testing (KRS)** | Minimal 1.000 contoh kombinasi SKS | `@settings(max_examples=1000)` (`Hypothesis`) | **PASSED** |
| **State Machine Illegal Transitions** |Seluruh transisi ilegal diuji | 12 kombinasi transisi ilegal (`@pytest.mark.parametrize`) | **PASSED** |
| **True Multi-Thread Concurrency NIM** | Bebas race condition & duplikasi | `ThreadPoolExecutor(max_workers=8)` + `Barrier(8)` pada file DB | **PASSED** |
| **Kasus Pengujian IPK (GPA)** | Minimal 10 skenario uji | **14 skenario uji parametrik** (A/B/C/D/E, ulang MK, lintas semester) | **PASSED** |
| **Migrasi Database (Alembic)** | Upgrade & Downgrade tanpa error | `upgrade head` $\rightarrow$ `downgrade base` $\rightarrow$ `upgrade head` | **PASSED** |

---

## 2. Tabel Code Coverage per File Modul (`app/`)

Hasil eksekusi `python -m pytest -v --cov=app --cov-report=term-missing --cov-report=html`:

```text
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
app\database.py                            17      0   100%
app\main.py                                28      0   100%
app\models\__init__.py                     10      0   100%
app\models\base.py                          0      0   100%
app\models\calon_mahasiswa.py              29      0   100%
app\models\finance_models.py               42      0   100%
app\models\grade_history.py                13      0   100%
app\models\jadwal_models.py                53      0   100%
app\models\jalur_masuk.py                  10      0   100%
app\models\krs_models.py                   76      0   100%
app\models\nim_sequence.py                 10      0   100%
app\models\program_studi.py                13      0   100%
app\models\user_model.py                   15      0   100%
app\observers\concrete_observers.py        24      0   100%
app\observers\notification_manager.py      10      0   100%
app\observers\schedule_subject.py          20      0   100%
app\routers\__init__.py                     0      0   100%
app\routers\auth.py                        31      0   100%
app\routers\billing.py                     40      0   100%
app\routers\dashboard.py                   34      0   100%
app\routers\grades.py                      44      0   100%
app\routers\krs.py                         61      0   100%
app\routers\payment.py                     35      0   100%
app\routers\pmb.py                         54      0   100%
app\routers\schedules.py                   34      0   100%
app\schemas\auth.py                        18      0   100%
app\schemas\finance.py                     34      0   100%
app\schemas\grade.py                       34      0   100%
app\schemas\krs.py                         26      0   100%
app\schemas\pmb.py                         51      0   100%
app\services\billing_service.py           213     13    94%   192, 252-254, 401, 404-407, 446, 449-452, 490
app\services\conflict_detector.py          51      0   100%
app\services\gpa_calculator.py             59      0   100%
app\services\grade_service.py              62      0   100%
app\services\krs\validators.py            136      2    99%   49, 276
app\services\krs_manager.py               178      2    99%   77-78
app\services\krs_recommender.py            73      0   100%
app\services\krs_state_machine.py          18      0   100%
app\services\payment_service.py           201     12    94%   175, 211, 258, 307-315, 330, 358, 364
app\services\pmb_service.py                83      1    99%   29
app\services\rescheduling_service.py       35      0   100%
app\services\scheduler_service.py          63      0   100%
app\services\scheduling_service.py        142      0   100%
app\services\transcript_service.py         39      2    95%   32, 35
app\utils\__init__.py                       0      0   100%
app\utils\pdf_generator.py                 76      0   100%
app\utils\security.py                      79      1    99%   107
---------------------------------------------------------------------
TOTAL                                    2374     33    99%
```

---

## 3. Rincian 27 File Pengujian (`tests/`)

| No | Nama File Test | Cakupan Modul & Fitur yang Diuji |
|---:|---|---|
| 1 | `tests/test_audit_week3_to_11.py` | Pengujian terpadu Minggu 3–11 & P1–P5: autentikasi & RBAC, konkurensi NIM multi-thread (`ThreadPoolExecutor` 8 worker), konsistensi nilai D vs prasyarat C (P2), integrasi `JadwalKuliah` $\rightarrow$ KRS (P3), `APScheduler` lifecycle (P1), dan form edit nilai `/grades-ui` (P5). |
| 2 | `tests/test_pmb_register.py` | Registrasi calon mahasiswa, validasi nomor telepon Indonesia, penolakan email duplikat (`409`), validasi foreign key prodi & jalur masuk. |
| 3 | `tests/test_pmb_week4.py` | Persetujuan (`approve`) & penolakan (`reject`) PMB, idempotency NIM, format NIM, statistik `GROUP BY`, dan konkurensi pembuatan NIM. |
| 4 | `tests/test_krs.py` | `KRSManager` (`add_course`, `remove_course`, `validate_krs`), batas 24 SKS, prasyarat nilai minimal C, jadwal bentrok, dan duplikasi mata kuliah. |
| 5 | `tests/test_krs_property.py` | *Property-Based Testing* menggunakan `Hypothesis` (`@settings(max_examples=1000)`) untuk memastikan invariant batas SKS KRS. |
| 6 | `tests/test_state_machine.py` | Transisi valid & 12 kombinasi transisi ilegal pada `KRSStatus` (`DRAFT`, `SUBMITTED`, `APPROVED`, `REVISION`), otorisasi Dosen PA (`403`/`409`). |
| 7 | `tests/test_recommender.py` | Algoritma *CSP Backtracking* pada `KRSRecommender` (prioritas MK wajib, semester berjalan, prasyarat, bebas konflik). |
| 8 | `tests/test_week5_6_Anchor.py` | Pengujian komprehensif deliverable Minggu 5–6 (Chain of Responsibility, `EXPLAIN QUERY PLAN`, State Machine, Hypothesis). |
| 9 | `tests/test_scheduling.py` | CRUD `JadwalKuliah`, deteksi konflik 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`), kapasitas ruangan, dan Observer Pattern. |
| 10 | `tests/test_rescheduling.py` | Rekomendasi maksimal 3 alternatif jadwal bebas bentrok oleh `ReschedulingService`. |
| 11 | `tests/test_week7_8_coverage.py` | Endpoint `/api/schedules`, `/api/schedules/{id}/suggestions`, `/dashboard`, dan penyimpanan `notification_log`. |
| 12 | `tests/test_transcript_service.py` | 14 skenario uji parametrik perhitungan IPK/IPS (nilai A/B/C/D/E, pengulangan mata kuliah D$\rightarrow$B dan E$\rightarrow$B, lintas semester, pembulatan) & Audit Trail. |
| 13 | `tests/test_grades_api.py` | Endpoint `/api/grades/input` (validasi presensi $\ge 75\%$), `/api/grades/update/{grade_id}` (trigger `trg_grade_history_update`), `/api/grades/history/{nim}`, dan unduh PDF `/api/grades/transcript/{nim}/pdf`. |
| 14 | `tests/test_pdf_generator_coverage.py` | Verifikasi biner PDF (`%PDF-1.4`), ekstraksi konten, Logo Universitas, biodata, tabel nilai, predikat kelulusan, dan tanda tangan Dekan. |
| 15 | `tests/test_billing_service.py` | Pembuatan tagihan SPP berdasarkan tarif prodi, jatuh tempo 14 hari, denda keterlambatan, dan sinkronisasi status `unpaid`/`partial`/`paid`/`overdue`. |
| 16 | `tests/test_payment_service.py` | Pemrosesan pembayaran atomic (`process_payment`), cicilan (`partial`), pelunasan (`paid`), dan pencegahan duplikasi `reference_number`. |
| 17 | `tests/test_payment_webhook.py` | Verifikasi signature HMAC-SHA256 pada `/api/payments/webhook`, penolakan signature palsu (`401`), dan *idempotency* `transaction_id` duplikat. |
| 18 | `tests/test_krs_finance_integration.py` | Blokir otomatis `add_course` dan `submit_krs` (`403 Forbidden`) saat mahasiswa memiliki tagihan `overdue`, serta pembukaan blokir otomatis saat tagihan `paid`. |
| 19 | `tests/test_finance_router_coverage.py` | Pengujian seluruh endpoint `/api/billing/*`, `/api/payments/*`, `/finance-dashboard`, dan `/api/billing/ai-report`. |
| 20–27 | `test_boost_coverage.py`, `test_conflict_detector_coverage.py`, `test_final_coverage.py`, `test_final_fixes.py`, `test_krs_api_coverage.py`, `test_krs_manager_extra_coverage.py`, `test_ultimate_coverage.py`, `test_validator_exception_coverage.py` | Pengujian *edge cases*, *boundary conditions*, dan penanganan rollback transaksi pada seluruh service dan router. |
