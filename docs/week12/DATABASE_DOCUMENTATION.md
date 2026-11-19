# DOKUMENTASI SKEMA & MIGRASI DATABASE (`DATABASE_DOCUMENTATION.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 3–11  
**ORM & Engine:** SQLAlchemy 2.0.39 + SQLite 3 (`PRAGMA foreign_keys = ON`, `PRAGMA busy_timeout = 30000`)  
**Tool Migrasi:** Alembic 1.13.1 (Head Revision: `d4e8f2a1c305`)

---

## 1. Ringkasan Arsitektur Database

Database SIAKAD terdiri dari **27 tabel** (26 tabel domain aplikasi + 1 tabel `alembic_version`), **1 SQLite Trigger** (`trg_grade_history_update`), dan **1 Database View** (`v_grade_history`).

### Kelompok Tabel Berdasarkan Modul:
1. **Autentikasi & RBAC:** `app_user`
2. **Modul PMB (Minggu 3–4):** `program_studi`, `jalur_masuk`, `calon_mahasiswa`, `nim_sequences`
3. **Modul KRS (Minggu 5–6):** `matakuliah`, `prerequisite`, `krs`, `krs_detail`, `krs_transition`
4. **Modul Jadwal, Ruangan & Observer (Minggu 7–8):** `dosen`, `ruangan`, `jadwal_kuliah`, `schedule_change_log`, `notification_log`
5. **Modul Nilai & Audit Trail (Minggu 9–10):** `skala_nilai`, `riwayat_nilai`, `grade_history`, `grade_audit_context`
6. **Modul Keuangan SPP & Pembayaran (Minggu 11):** `billing`, `payment_method`, `payment`
7. **Modul Presensi QR Code & Rate Limiting (Minggu 12):** `attendance_session`, `attendance_qr_token`, `attendance_record`, `attendance_scan_attempt`

---

## 2. Spesifikasi Detail Seluruh Tabel, Constraint, & Index

### 2.1. Modul PMB & Master Akademik
- **`program_studi`** (`app/models/program_studi.py`)
  - **PK:** `id` (`INTEGER`)
  - **Kolom:** `kode` (`VARCHAR(3)`, `NOT NULL`), `nama` (`VARCHAR(100)`, `NOT NULL`), `fakultas` (`VARCHAR(100)`, `NOT NULL`), `tarif_spp` (`NUMERIC(12,2)`, default `5000000.00`)
  - **Unique Constraint:** `uq_program_studi_kode(kode)`
- **`jalur_masuk`** (`app/models/jalur_masuk.py`)
  - **PK:** `id` (`INTEGER`)
  - **Kolom:** `kode` (`VARCHAR(20)`, `NOT NULL`), `nama` (`VARCHAR(100)`, `NOT NULL`), `deskripsi` (`VARCHAR(255)`)
  - **Unique Constraint:** `uq_jalur_masuk_kode(kode)`
- **`calon_mahasiswa`** (`app/models/calon_mahasiswa.py`)
  - **PK:** `id` (`INTEGER`)
  - **FK:** `program_studi_id -> program_studi.id`, `jalur_masuk_id -> jalur_masuk.id`, `dosen_pa_id -> dosen.id` (`NULLABLE`)
  - **Kolom:** `nama_lengkap`, `email`, `phone`, `tanggal_lahir`, `alamat`, `status` (`pending` / `approved` / `rejected`), `nim` (`VARCHAR(20)`, `NULLABLE`), `created_at`, `approved_at`
  - **Unique Constraints:** `uq_calon_mahasiswa_email(email)`, `uq_calon_mahasiswa_nim(nim)`
- **`nim_sequences`** (`app/models/nim_sequence.py`)
  - **PK:** `id` (`INTEGER`)
  - **FK:** `program_studi_id -> program_studi.id`
  - **Kolom:** `tahun` (`INTEGER`, `NOT NULL`), `last_sequence` (`INTEGER`, default `0`)
  - **Unique Constraint:** `uq_nim_tahun_prodi(tahun, program_studi_id)`

### 2.2. Modul KRS & Prasyarat
- **`matakuliah`** (`app/models/krs_models.py`)
  - **PK:** `id` (`INTEGER`)
  - **Kolom:** `kode_mk` (`VARCHAR(20)`), `nama_mk` (`VARCHAR(100)`), `sks` (`INTEGER`), `semester` (`INTEGER`), `hari` (`VARCHAR(20)`), `jam_mulai` (`TIME`), `jam_selesai` (`TIME`), `is_wajib` (`BOOLEAN`)
  - **Unique & Check Constraints:** `UNIQUE(kode_mk)`, `ck_matakuliah_sks_range (sks >= 1 AND sks <= 6)`
- **`prerequisite`** (`app/models/krs_models.py`)
  - **PK:** `id` (`INTEGER`)
  - **FK:** `matakuliah_id -> matakuliah.id`, `prerequisite_id -> matakuliah.id`
  - **Unique & Check Constraints:** `uq_prerequisite_pair(matakuliah_id, prerequisite_id)`, `ck_no_self_prerequisite(matakuliah_id != prerequisite_id)`
  - **Index:** `ix_prerequisite_matakuliah_id(matakuliah_id)`
- **`krs`** (`app/models/krs_models.py`)
  - **PK:** `id` (`INTEGER`)
  - **Kolom:** `nim` (`VARCHAR(20)`, `INDEX`), `semester_akademik` (`INTEGER`), `status` (`DRAFT` / `SUBMITTED` / `APPROVED` / `REVISION`), `dosen_pa_id` (`INTEGER`), `catatan_revisi` (`VARCHAR(255)`), `needs_review` (`BOOLEAN`, default `False`), `version` (`INTEGER`, default `1`)
- **`krs_detail`** (`app/models/krs_models.py`)
  - **PK:** `id` (`INTEGER`)
  - **FK:** `krs_id -> krs.id` (`ON DELETE CASCADE`), `matakuliah_id -> matakuliah.id`
  - **Unique Constraint:** `uq_krs_matakuliah(krs_id, matakuliah_id)`
- **`krs_transition`** (`app/models/krs_models.py`)
  - **PK:** `id` (`INTEGER`)
  - **FK:** `krs_id -> krs.id` (`ON DELETE CASCADE`)
  - **Kolom:** `from_state`, `to_state`, `actor`, `notes`, `created_at`

### 2.3. Modul Jadwal, Ruangan, & Observer
- **`dosen`** (`app/models/jadwal_models.py`): `id` (PK), `nidn` (`UNIQUE`), `nama`, `email` (`UNIQUE`), `fakultas`
- **`ruangan`** (`app/models/jadwal_models.py`): `id` (PK), `kode_ruangan` (`UNIQUE`), `nama_ruangan`, `kapasitas` (`Check: kapasitas > 0`), `gedung`
- **`jadwal_kuliah`** (`app/models/jadwal_models.py`):
  - **PK:** `id` (`INTEGER`)
  - **FK:** `matakuliah_id -> matakuliah.id`, `ruangan_id -> ruangan.id`, `dosen_id -> dosen.id`
  - **Kolom:** `hari`, `jam_mulai`, `jam_selesai`, `tahun_ajaran`, `semester_akademik`, `enrolled_count` (`>= 0`), `status` (`AKTIF` / `BATAL`)
- **`schedule_change_log`** & **`notification_log`** (`app/models/jadwal_models.py`): Mencatat riwayat perubahan jadwal dan log pengiriman notifikasi Observer (`STUDENT`, `LECTURER`, `ADMIN`, serta notifikasi keuangan).

### 2.4. Modul Nilai, Skala Nilai, & Audit Trail
- **`skala_nilai`** (`app/models/krs_models.py`): `id` (PK), `nilai_huruf` (`UNIQUE`: `A`, `B`, `C`, `D`, `E`), `bobot` (`4.0`, `3.0`, `2.0`, `1.0`, `0.0`)
- **`riwayat_nilai`** (`app/models/krs_models.py`):
  - **PK:** `id` (`INTEGER`)
  - **FK:** `matakuliah_id -> matakuliah.id`, `skala_nilai_id -> skala_nilai.id`
  - **Kolom:** `nim` (`INDEX`), `semester` (`INTEGER`), `presensi_persen` (`FLOAT`, default `100.0`)
  - **Composite Index:** `ix_riwayat_nilai_nim_mk_skala(nim, matakuliah_id, skala_nilai_id)` (digunakan untuk optimasi query prasyarat `NOT EXISTS`)
- **`grade_history`** & **`grade_audit_context`** (`app/models/grade_history.py`):
  - Menyimpan audit trail perubahan nilai (`old_grade`, `new_grade`, `changed_by`, `changed_at`, `reason`) yang diisi secara otomatis oleh SQLite Trigger **`trg_grade_history_update`** (`AFTER UPDATE OF skala_nilai_id ON riwayat_nilai`) dan diekspos melalui View **`v_grade_history`**.

### 2.5. Modul Keuangan SPP & Autentikasi
- **`billing`** (`app/models/finance_models.py`):
  - **PK:** `id` (`INTEGER`), **FK:** `mahasiswa_id -> calon_mahasiswa.id`
  - **Kolom:** `semester` (`VARCHAR(20)`), `tahun` (`INTEGER`), `total_amount` (`NUMERIC(12,2)`), `paid_amount` (`NUMERIC(12,2)`), `due_date` (`DATE`), `status` (`unpaid` / `partial` / `paid` / `overdue`), `created_at`, `updated_at`
  - **Unique Constraint:** `uq_billing_mahasiswa_semester(mahasiswa_id, semester)`
- **`payment_method`** (`app/models/finance_models.py`): `id` (PK), `code` (`UNIQUE`), `name`, `is_active`
- **`payment`** (`app/models/finance_models.py`):
  - **PK:** `id` (`INTEGER`), **FK:** `billing_id -> billing.id`, `method_id -> payment_method.id`
  - **Kolom:** `amount` (`NUMERIC(12,2)`), `paid_at` (`DATETIME`), `status` (`pending` / `success` / `failed`), `reference_number` (`UNIQUE`)
- **`app_user`** (`app/models/user_model.py`):
  - **PK:** `id` (`INTEGER`), `username` (`UNIQUE`), `password_hash` (PBKDF2-HMAC-SHA256), `role` (`admin` / `dosen` / `mahasiswa`), `nim`, `nidn`, `is_active`, `created_at`

---

## 3. Rantai Revisi Migrasi Alembic (Base $\rightarrow$ Head)

| Urutan | Revision ID | Down Revision | Deskripsi Perubahan Skema |
|---:|---|---|---|
| 1 | `c0b4e3a8c963` | `None` (Base) | Pembuatan tabel lengkap Minggu 3–8 (`program_studi`, `jalur_masuk`, `calon_mahasiswa`, `nim_sequences`, `matakuliah`, `prerequisite`, `skala_nilai`, `riwayat_nilai`, `krs`, `krs_detail`, `krs_transition`, `dosen`, `ruangan`, `jadwal_kuliah`, `schedule_change_log`, `notification_log`). |
| 2 | `95417f7b9188` | `c0b4e3a8c963` | Penambahan tabel `grade_history` dan kolom `presensi_persen` pada `riwayat_nilai` (Minggu 9–10). |
| 3 | `8d2fbf7e4c2b` | `95417f7b9188` | Penambahan unique constraint `uq_riwayat_nilai_mhs_mk_smt` pada `riwayat_nilai`. |
| 4 | `0f9e48bbab1f` | `8d2fbf7e4c2b` | Penambahan tabel `grade_audit_context`, trigger otomatis `trg_grade_history_update`, dan view `v_grade_history`. |
| 5 | `9fb882e2b5ae` | `0f9e48bbab1f` | Pembuatan tabel modul Keuangan SPP Minggu 11 (`billing`, `payment_method`, `payment`). |
| 6 | `50747fbd5ef0` | `9fb882e2b5ae` | Pemeriksaan idempotent kolom `version` pada tabel `krs`. |
| 7 | `a8c2d6e9f103` | `50747fbd5ef0` | Penambahan kolom `dosen_pa_id` (FK ke `dosen.id`) pada tabel `calon_mahasiswa`. |
| 8 | `b7e4c1d9a204` | `a8c2d6e9f103` | Pembuatan tabel `app_user`, kolom `program_studi.tarif_spp`, composite index `ix_riwayat_nilai_nim_mk_skala`, serta *seed data* referensi non-destruktif (`INSERT OR IGNORE`). |
| 9 | **`d4e8f2a1c305`** | `b7e4c1d9a204` | **(HEAD — Minggu 12)** Pembuatan tabel presensi QR Code (`attendance_session`, `attendance_qr_token`, `attendance_record`, `attendance_scan_attempt`) beserta constraint unik anti-duplikat dan composite index rate limiting. |
