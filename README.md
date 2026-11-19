# Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 1–12 & UTS

Sistem Informasi Akademik (SIAKAD) berbasis REST API dan Dashboard Web yang dikembangkan menggunakan **Python 3.11**, **FastAPI**, **SQLAlchemy 2.0**, **Alembic**, **SQLite**, **Pydantic**, **ReportLab**, **APScheduler**, **PyJWT + QRCode**, serta **Pytest + Hypothesis**.

---

## Dokumen Utama Pengumpulan UTS (EDLINK)

| Tahap & Deliverables UTS | File PDF / Dokumen di Repository |
|---|---|
| **1. Laporan Final UML Diagram (PDF 9 Halaman — PMB, KRS, & SIAKAD Sesi 3–12)** | [Laporan_Final_UML_Diagram_UTS_SIAKAD.pdf](Laporan_Final_UML_Diagram_UTS_SIAKAD.pdf) / [docs/Final-UML-diagram.pdf](docs/Final-UML-diagram.pdf) |
| **2. Architecture Decision Record / ADR (PDF 1 Halaman)** | [docs/ADR-architecture-decisions.pdf](docs/ADR-architecture-decisions.pdf) |
| **3. Source Mermaid UML Diagrams (`.mmd`)** | [diagrams/class-diagram.mmd](diagrams/class-diagram.mmd), [diagrams/usecase-diagram.mmd](diagrams/usecase-diagram.mmd), [diagrams/sequence-pmb.mmd](diagrams/sequence-pmb.mmd), [diagrams/sequence-krs.mmd](diagrams/sequence-krs.mmd) |
| **4. AI Usage Documentation (7 Prompt + Before/After SOLID + OPAR)** | [prompts/ai-usage-log.md](prompts/ai-usage-log.md) |
| **5. Tahap 1 UTS — Modul PMB (Minggu 3–4)** | [app/models/calon_mahasiswa.py](app/models/calon_mahasiswa.py), [app/services/pmb_service.py](app/services/pmb_service.py), [app/routers/pmb.py](app/routers/pmb.py), [tests/test_pmb_api.py](tests/test_pmb_api.py) |
| **6. Tahap 2 UTS — Modul KRS (Minggu 5–6 & Integrasi)** | [app/services/krs_manager.py](app/services/krs_manager.py), [app/services/krs/validators.py](app/services/krs/validators.py), [app/services/krs_state_machine.py](app/services/krs_state_machine.py), [app/routers/krs.py](app/routers/krs.py) |

---

Proyek ini mengimplementasikan, mengintegrasikan, dan memverifikasi seluruh kriteria tugas perkuliahan **Minggu 1 hingga Minggu 12** beserta penyempurnaan prioritas **P1–P5**:
1. **Minggu 1–2 (Desain UML & Arsitektur SOLID)**: Perancangan *Class Diagram* bebas *God Object*, *Use Case Diagram* (`<<include>>` & `<<extend>>`), *Sequence Diagram* PMB & KRS dengan *alternate flows*, *AI Usage Log* + *OPAR*, dan *Architecture Decision Record (ADR)*.
2. **Minggu 3–4 (Modul PMB)**: Registrasi calon mahasiswa, validasi nomor telepon Indonesia & penolakan email duplikat (`409 Conflict`), persetujuan/penolakan pendaftar, statistik `GROUP BY`, serta **NIM Generator Thread-Safe** (`BEGIN IMMEDIATE`, `PRAGMA busy_timeout`, row lock, dan pengujian konkurensi `ThreadPoolExecutor` multi-thread).
3. **Minggu 5–6 (Modul KRS)**: *Chain of Responsibility* (`SKSValidator`, `PrerequisiteValidator`, `ConflictValidator`, `DuplicateValidator`) dengan mode *fail-fast* & *collect-all*, *State Machine* (`DRAFT`, `SUBMITTED`, `APPROVED`, `REVISION`) beserta pencatatan `KrsTransition`, optimasi query prasyarat `NOT EXISTS` + `EXPLAIN QUERY PLAN`, *Property-Based Testing* (`Hypothesis` 1.000 contoh), dan *AI KRS Recommender* berbasis CSP Backtracking.
4. **Minggu 7–8 (Modul Jadwal & Ruangan)**: Deteksi konflik 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`) dengan interval setengah terbuka `[start, end)`, validasi kapasitas ruangan, *Observer Pattern* (`ScheduleSubject`, `StudentObserver`, `LecturerObserver`, `AdminObserver`, `NotificationManager`), integrasi langsung `JadwalKuliah` ke validasi & invalidasi KRS (`needs_review = True`), *AI Rescheduling* (3 alternatif jadwal bebas bentrok), dan *Conflict Resolver Dashboard*.
5. **Minggu 9–10 (Modul Nilai & Transkrip PDF)**: Input & edit nilai dengan validasi presensi $\ge 75\%$, konsistensi kelulusan nilai `D (1.0)` pada IPS/IPK/Transkrip dengan batas minimal prasyarat tetap `C (2.0)`, *Audit Trail* otomatis via SQLite Trigger (`trg_grade_history_update`) & View (`v_grade_history`), *PDF Generator* Transkrip Akademik Resmi (`ReportLab` dengan Logo Universitas & Tanda Tangan Dekan), serta halaman web `/grades-ui` lengkap dengan **Form Input Nilai** dan **Form Edit Nilai Mahasiswa** (beserta alasan wajib).
6. **Minggu 11 (Modul Keuangan SPP & Webhook)**: Pembuatan tagihan SPP semester otomatis berdasarkan tarif program studi (jatuh tempo 14 hari), perhitungan denda keterlambatan, penjadwalan otomatis `APScheduler` (`BackgroundScheduler` + `CronTrigger` terintegrasi dengan FastAPI `lifespan`), pemrosesan pembayaran atomic, simulasi *Payment Gateway Webhook* (verifikasi signature HMAC-SHA256 & idempotency), pembatasan pengisian/submit KRS bagi mahasiswa menunggak (`overdue`), Dashboard Keuangan (`/finance-dashboard`), dan *AI Financial Report* JSON.
7. **Minggu 12 (Modul Presensi QR Code & AI Attendance Insights)**: Penerbitan QR Code presensi oleh dosen berbasis JWT `HS256` (`exp = 15 menit`, `jti` unik), pemindaian oleh mahasiswa dengan *persistent database rate-limiting* (`5x / 60 detik`), klasifikasi waktu (`0–15 menit = HADIR`, `15–30 menit = TERLAMBAT`, `>30 menit = DITOLAK`), laporan persentase kehadiran & ekspor Excel (`.xlsx`), serta *AI Attendance Pattern Analyzer* (`/attendance-ui`).

---

## Daftar Dokumentasi Proyek

- **Panduan Instalasi:** [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
- **Panduan Pengguna (Admin, Dosen, Mahasiswa):** [USER_GUIDE.md](USER_GUIDE.md)
- **Dokumentasi REST API Lengkap (47 Endpoint):** [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Dokumentasi Skema & Migrasi Database (23 Tabel):** [DATABASE_DOCUMENTATION.md](DATABASE_DOCUMENTATION.md)
- **Log Penggunaan AI & Prompt Terbaik:** [AI_USAGE_LOG.md](AI_USAGE_LOG.md)
- **Dokumentasi OPAR (Observation, Problem, Action, Result):** [OPAR.md](OPAR.md)
- **Architecture Decision Records (ADR):** [docs/adr/](docs/adr/) & [docs/week9-10/ADR-001-Audit-Trail.md](docs/week9-10/ADR-001-Audit-Trail.md)
- **Laporan Hasil Pengujian & Coverage (357 Test / 99%):** [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md)
- **Laporan Pembersihan Repository:** [FINAL_CLEANUP_REPORT.md](FINAL_CLEANUP_REPORT.md)
- **Checklist Pengumpulan Proyek:** [PROJECT_SUBMISSION_CHECKLIST.md](PROJECT_SUBMISSION_CHECKLIST.md)

---

## 1. Dokumentasi Format NIM (Minggu 3–4 & P4)

Format Nomor Induk Mahasiswa (NIM) mengikuti standar institusional:

```text
[TAHUN_MASUK: 4 digit][KODE_PRODI: 3 karakter]-[RUNNING_NUMBER: 4 digit]
```

Contoh:
- `2025001-0001` (Tahun `2025`, Kode Prodi `001`, Pendaftar ke-1)
- `2026TIF-0001` (Tahun `2026`, Kode Prodi `TIF` Teknik Informatika, Pendaftar ke-1)

Karakteristik `generate_nim`:
- **Unik & Sequential**: Nomor urut dikelola per `(tahun, program_studi_id)` melalui tabel `nim_sequences` (`uq_nim_tahun_prodi`) dan constraint `UNIQUE` pada `calon_mahasiswa.nim`.
- **True Multi-Thread Safe**: Menggunakan `BEGIN IMMEDIATE` pada SQLite, `PRAGMA busy_timeout = 30000`, *row-level locking* (`with_for_update()`), dan mekanisme *retry* yang telah diuji secara paralel menggunakan `ThreadPoolExecutor(max_workers=8)` dan `threading.Barrier(8)`.
- **Idempotent**: Pemanggilan `PUT /api/pmb/approve/{id}` berulang pada mahasiswa yang sudah `approved` mengembalikan NIM yang sama tanpa men-generate NIM baru.

---

## 2. Ringkasan Endpoint API & Antarmuka Web (47 Endpoint)

### A. Autentikasi & RBAC (`/api/auth`)
| Method | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/api/auth/register` | Registrasi akun pengguna (`admin`, `dosen`, `mahasiswa`) |
| `POST` | `/api/auth/login` | Login dan mendapatkan token HMAC-SHA256 (`Bearer`) |
| `GET` | `/api/auth/me` | Melihat profil dan peran pengguna dari token aktif |

### B. Modul PMB (`/api/pmb` — Minggu 3–4)
| Method | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/api/pmb/register` | Pendaftaran calon mahasiswa baru (status `pending`, `409` jika email duplikat, `400` jika input tidak valid) |
| `GET` | `/api/pmb/status/{id}` | Cek status pendaftaran dan NIM calon mahasiswa |
| `PUT` | `/api/pmb/approve/{id}` | Persetujuan pendaftaran (idempotent, generate NIM, opsional `?dosen_pa_id=`) |
| `PUT` | `/api/pmb/reject/{id}` | Penolakan pendaftaran calon mahasiswa |
| `GET` | `/api/pmb/stats` | Statistik pendaftar menggunakan agregasi SQL `GROUP BY` |

### C. Modul KRS (`/api/krs` — Minggu 5–6 & Integrasi Minggu 11)
| Method | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/api/krs/add` | Tambah mata kuliah ke KRS (diblokir HTTP `403` jika ada tunggakan SPP `overdue`) |
| `POST` | `/api/krs/remove` | Hapus mata kuliah dari KRS |
| `GET` | `/api/krs/{nim}` | Lihat detail KRS mahasiswa beserta daftar mata kuliah |
| `GET` | `/api/krs/validate/{nim}` | Validasi menyeluruh KRS (SKS, Prasyarat, Konflik JadwalKuliah, Duplikat) |
| `GET` | `/api/krs/explain-prerequisite/{nim}/{matakuliah_id}` | Eksekusi `EXPLAIN QUERY PLAN` pada query pengecekan prasyarat |
| `POST` | `/api/krs/submit/{nim}` | Submit KRS (`DRAFT`/`REVISION` $\rightarrow$ `SUBMITTED`, menolak KRS kosong & tunggakan SPP) |
| `POST` | `/api/krs/approve/{nim}` | Persetujuan KRS oleh Dosen PA (`SUBMITTED` $\rightarrow$ `APPROVED`) |
| `POST` | `/api/krs/revise/{nim}` | Permintaan revisi KRS oleh Dosen PA (`SUBMITTED` $\rightarrow$ `REVISION`) |
| `POST` | `/api/krs/recommend/{nim}` | Rekomendasi KRS optimal menggunakan algoritma CSP Backtracking |

### D. Modul Jadwal & Ruangan (`/api/schedules` — Minggu 7–8 & P3)
| Method | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/api/schedules` | Buat jadwal kuliah baru (validasi kapasitas & konflik 3 dimensi, trigger Observer) |
| `GET` | `/api/schedules` | Lihat seluruh jadwal kuliah |
| `PUT` | `/api/schedules/{id}` | Update jadwal kuliah (validasi ulang & tandai KRS terdampak `needs_review=True`, catat `KrsTransition`, trigger Observer) |
| `DELETE` | `/api/schedules/{id}` | Hapus jadwal kuliah (invalidasi KRS terdampak & trigger Observer) |
| `GET` | `/api/schedules/conflicts` | Deteksi seluruh pasangan jadwal bentrok (`room_conflict`, `lecturer_conflict`, `time_overlap`) |
| `POST` | `/api/schedules/{id}/suggestions` | Rekomendasi 3 alternatif jadwal bebas bentrok (CSP) |
| `GET` | `/api/admin/scheduling/dashboard` | Data JSON untuk Conflict Resolver Dashboard |

### E. Modul Nilai & Transkrip (`/api/grades` — Minggu 9–10, P2 & P5)
| Method | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/api/grades/input` | Input nilai mahasiswa (validasi presensi $\ge 75\%$) |
| `PUT` | `/api/grades/update/{grade_id}` | Edit nilai dengan alasan wajib (`reason`) & pencatatan otomatis ke `grade_history` via DB Trigger |
| `GET` | `/api/grades/history/{nim}` | Lihat riwayat perubahan nilai mahasiswa dari view `v_grade_history` |
| `GET` | `/api/grades/ips/{nim}/{semester}` | Hitung Indeks Prestasi Semester (IPS — nilai D bobot 1.0 dihitung lulus) |
| `GET` | `/api/grades/ipk/{nim}` | Hitung Indeks Prestasi Kumulatif (IPK — mengambil nilai tertinggi jika MK diulang) |
| `GET` | `/api/grades/transcript/{nim}` | Lihat Transkrip Akademik lengkap (JSON) |
| `GET` | `/api/grades/transcript/{nim}/pdf` | Unduh Transkrip Akademik Resmi (PDF dengan Logo Universitas & TTD Dekan) |

### F. Modul Keuangan SPP (`/api/billing` & `/api/payments` — Minggu 11 & P1)
| Method | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/api/billing/generate` | Buat tagihan SPP per mahasiswa |
| `POST` | `/api/billing/generate-semester` | Generate tagihan SPP massal seluruh mahasiswa aktif per semester (idempotent) |
| `GET` | `/api/billing/{billing_id}/late-fee` | Hitung denda keterlambatan SPP (Rp50.000/hari atau 1% per 30 hari sesuai mode) |
| `PUT` | `/api/billing/{billing_id}/status` | Sinkronisasi status tagihan (`unpaid`, `partial`, `paid`, `overdue`) |
| `POST` | `/api/billing/reminders/run` | Jalankan job pengiriman reminder otomatis tagihan `overdue` secara manual/on-demand |
| `GET` | `/api/billing/scheduler/status` | Status `APScheduler` (`BackgroundScheduler` & daftar `CronTrigger` jobs aktif) |
| `GET` | `/api/billing/dashboard` | Data real-time Dashboard Keuangan (per mahasiswa, collection rate prodi, bulanan, penunggak) |
| `GET` | `/api/billing/ai-report` | Laporan AI Financial Insights berformat JSON |
| `POST` | `/api/payments/create` | Buat transaksi pembayaran berstatus `pending` |
| `POST` | `/api/payments/process` | Proses pembayaran langsung secara atomic (`partial`/`paid` + kirim receipt log) |
| `POST` | `/api/payments/webhook` | Endpoint Webhook Payment Gateway (verifikasi signature HMAC-SHA256 & idempotent) |
| `POST` | `/api/payments/webhook/simulate-signature` | Helper simulasi pembuatan signature HMAC-SHA256 untuk pengujian `curl` |
| `POST` | `/api/payments/{payment_id}/confirm` | Konfirmasi pembayaran `pending` menjadi `success` |
| `POST` | `/api/payments/{payment_id}/fail` | Tandai pembayaran `pending` menjadi `failed` |

### G. Halaman Antarmuka Web (UI Dashboard & Form)
- `GET /` — Endpoint status root API
- `GET /dashboard` — Conflict Resolver Dashboard (Admin Jadwal & Ruangan)
- `GET /grades-ui` — Form Input Nilai Dosen, **Form Edit Nilai Mahasiswa (`PUT /api/grades/update/{grade_id}`)**, Cek IPK, Unduh PDF Transkrip & Tabel Audit Trail
- `GET /finance-dashboard` — Dashboard Keuangan SPP & AI Financial Insights
- `GET /docs` — Dokumentasi Interaktif Swagger UI / OpenAPI

---

## 3. Cara Cepat Menjalankan Project, Migrasi, dan Pengujian

### A. Persiapan Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### B. Menjalankan Migrasi Database & Seed Data (Alembic)
Upgrade ke revisi terbaru (`head` — `b7e4c1d9a204` yang sekaligus memuat seed data non-destruktif untuk `skala_nilai`, `program_studi`, `jalur_masuk`, `payment_method`, dan akun `app_user`):
```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
```

### C. Menjalankan Server Aplikasi
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### D. Menjalankan Pengujian (Pytest & Coverage)
```powershell
.\venv\Scripts\python.exe -m pytest -v --cov=app --cov-report=term-missing --cov-report=html
```
Hasil verifikasi pengujian terbaru:
- **357 passed, 0 failed**
- **Total Coverage: 99%** (`2.374` statements, `33` missed — melampaui syarat minimal 80%)

---

## 4. Contoh Pengujian Webhook Payment Gateway dengan `curl`

1. **Dapatkan Signature HMAC-SHA256 Simulasi**:
```bash
curl -X POST http://127.0.0.1:8000/api/payments/webhook/simulate-signature \
  -H "Content-Type: application/json" \
  -d '{"amount":"5000000.00","billing_id":1,"method":"VIRTUAL_ACCOUNT","status":"paid","transaction_id":"TRX-2026-0001"}'
```

2. **Kirim Request Webhook dengan Header `X-Webhook-Signature`**:
```bash
curl -X POST http://127.0.0.1:8000/api/payments/webhook \
  -H "Content-Type: application/json" \
  -d '{"amount":"5000000.00","billing_id":1,"method":"VIRTUAL_ACCOUNT","status":"paid","transaction_id":"TRX-2026-0001"}' \
  -H "X-Webhook-Signature: <SIGNATURE_DARI_LANGKAH_1>"
```
Jika dikirim ulang dengan `transaction_id` yang sama, server mengembalikan HTTP `200 OK` dengan `"idempotent": true` tanpa menduplikasi pembayaran.
