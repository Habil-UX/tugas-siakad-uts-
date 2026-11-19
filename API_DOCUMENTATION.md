# DOKUMENTASI REST API LENGKAP (`API_DOCUMENTATION.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 3–11  
**Base URL:** `http://127.0.0.1:8000`  
**Swagger UI:** `http://127.0.0.1:8000/docs`  
**OpenAPI Spec:** `http://127.0.0.1:8000/openapi.json`

---

## 1. Standar HTTP Status Code & Penanganan Error

Seluruh endpoint SIAKAD mengikuti konvensi HTTP status code yang ketat:
- **`200 OK` / `201 Created`**: Operasi berhasil dieksekusi.
- **`400 Bad Request`**: Validasi input gagal (misal: format nomor telepon tidak valid, presensi $< 75\%$, submit KRS kosong, transisi status KRS ilegal, atau alasan edit nilai kosong).
- **`401 Unauthorized`**: Token autentikasi tidak valid/kedaluwarsa atau signature HMAC-SHA256 pada webhook tidak cocok.
- **`403 Forbidden`**: Peran pengguna tidak memiliki izin (RBAC), Dosen yang melakukan approve bukan Dosen PA mahasiswa terkait, atau **mahasiswa memiliki tunggakan SPP `overdue`** saat menambah/submit KRS.
- **`404 Not Found`**: Data pendaftar, mahasiswa, mata kuliah, jadwal, riwayat nilai, atau tagihan tidak ditemukan.
- **`409 Conflict`**: Duplikasi data unik (email pendaftar ganda, duplikasi mata kuliah/tagihan), bentrok jadwal 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`), kapasitas ruangan penuh, atau mahasiswa belum memiliki Dosen PA saat KRS di-approve.

---

## 2. Modul Autentikasi & RBAC (`/api/auth`)

### 2.1. `POST /api/auth/register`
Mendaftarkan pengguna baru (`admin`, `dosen`, `mahasiswa`).
- **Request Body:**
```json
{
  "username": "dosen_baru",
  "password": "Password123!",
  "role": "dosen",
  "nim": null,
  "nidn": "198501012010011001"
}
```
- **Response (`201 Created`):** Data profil user beserta `id`, `username`, `role`, `is_active`.

### 2.2. `POST /api/auth/login`
Login untuk mendapatkan token Bearer HMAC-SHA256.
- **Request Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```
- **Response (`200 OK`):**
```json
{
  "access_token": "<token_hmac_sha256>",
  "token_type": "bearer",
  "role": "admin",
  "username": "admin"
}
```

### 2.3. `GET /api/auth/me`
Mengambil informasi pengguna yang sedang login berdasarkan header `Authorization: Bearer <token>`.

---

## 3. Modul PMB (`/api/pmb` — Minggu 3–4 & P4)

| Method | Endpoint | Status Sukses | Status Error | Deskripsi |
|---|---|---|---|---|
| `POST` | `/api/pmb/register` | `201 Created` | `400`, `404`, `409` | Registrasi calon mahasiswa baru (status awal `pending`). Menolak email ganda (`409`) dan format telepon non-Indonesia (`400`). |
| `PUT` | `/api/pmb/approve/{id}` | `200 OK` | `400`, `404` | Menyetujui calon mahasiswa, menghasilkan NIM unik format `[TAHUN][KODE_PRODI]-[4_DIGIT]` secara *thread-safe* (`BEGIN IMMEDIATE` + row lock). Bersifat *idempotent*. Mendukung query opsional `?dosen_pa_id=`. |
| `PUT` | `/api/pmb/reject/{id}` | `200 OK` | `400`, `404` | Menolak pendaftaran calon mahasiswa (`pending` $\rightarrow$ `rejected`). Menolak perubahan jika sudah `approved` (`400`). |
| `GET` | `/api/pmb/status/{id}` | `200 OK` | `404` | Menampilkan detail pendaftaran, status, dan NIM. |
| `GET` | `/api/pmb/stats` | `200 OK` | - | Statistik pendaftar menggunakan agregasi SQL `GROUP BY` per status, jalur masuk, dan program studi. |

---

## 4. Modul KRS (`/api/krs` — Minggu 5–6, P2, P3, & Integrasi Minggu 11)

| Method | Endpoint | Status Sukses | Status Error | Deskripsi |
|---|---|---|---|---|
| `POST` | `/api/krs/add` | `200 OK` | `400`, `403`, `404` | Menambahkan mata kuliah ke KRS (`nim`, `kode_mk`). Diblokir `403` jika ada tagihan `overdue`. Menjalankan rantai validator (*fail-fast*): `SKSValidator` ($\le 24$), `PrerequisiteValidator` (minimal nilai `C` / bobot $\ge 2.0$ di semester sebelumnya), `ConflictValidator` (membaca `JadwalKuliah` aktif), `DuplicateValidator`. |
| `POST` | `/api/krs/remove` | `200 OK` | `400`, `404` | Menghapus mata kuliah dari KRS berstatus `DRAFT` atau `REVISION`. |
| `GET` | `/api/krs/{nim}` | `200 OK` | `404` | Menampilkan status KRS, `version`, `needs_review`, total SKS, dan daftar mata kuliah. |
| `GET` | `/api/krs/validate/{nim}` | `200 OK` | `404` | Menjalankan validasi menyeluruh (*collect-all*) pada KRS dan mengembalikan daftar seluruh pesan error jika ada. |
| `GET` | `/api/krs/explain-prerequisite/{nim}/{matakuliah_id}` | `200 OK` | `404` | Mengeksekusi `EXPLAIN QUERY PLAN` pada query `NOT EXISTS` prasyarat (membuktikan pemakaian index `ix_prerequisite_matakuliah_id` dan `ix_riwayat_nilai_nim_mk_skala`). |
| `POST` | `/api/krs/submit/{nim}` | `200 OK` | `400`, `403`, `404` | Mengajukan KRS (`DRAFT`/`REVISION` $\rightarrow$ `SUBMITTED`). Menolak KRS kosong (`400`), KRS tidak valid (`400`), atau mahasiswa dengan tunggakan SPP (`403`). |
| `POST` | `/api/krs/approve/{nim}` | `200 OK` | `400`, `403`, `404`, `409` | Persetujuan KRS oleh Dosen PA (`SUBMITTED` $\rightarrow$ `APPROVED`). Memvalidasi kepemilikan Dosen PA (`403` jika bukan Dosen PA, `409` jika Dosen PA belum diset) dalam satu transaksi atomic. |
| `POST` | `/api/krs/revise/{nim}` | `200 OK` | `400`, `403`, `404`, `409` | Permintaan revisi KRS oleh Dosen PA (`SUBMITTED` $\rightarrow$ `REVISION`) disertai catatan (`notes`). |
| `POST` | `/api/krs/recommend/{nim}` | `200 OK` | `404` | Rekomendasi paket KRS otomatis berbasis algoritma *CSP Backtracking* (`target_semester`, `max_sks`, `ipk`). |

---

## 5. Modul Jadwal & Ruangan (`/api/schedules` — Minggu 7–8 & P3)

| Method | Endpoint | Status Sukses | Status Error | Deskripsi |
|---|---|---|---|---|
| `POST` | `/api/schedules` | `201 Created` | `400`, `404`, `409` | Membuat jadwal kuliah baru. Memeriksa kapasitas ruangan vs `enrolled_count` dan konflik 3 dimensi (`room_conflict`, `lecturer_conflict`, `time_overlap`) dengan interval `[jam_mulai, jam_selesai)`. Memicu Observer Pattern. |
| `GET` | `/api/schedules` | `200 OK` | - | Mengambil daftar seluruh jadwal kuliah. |
| `PUT` | `/api/schedules/{id}` | `200 OK` | `400`, `404`, `409` | Memperbarui jadwal kuliah. Mengidentifikasi seluruh KRS terdampak, memvalidasi ulang terhadap `JadwalKuliah` terbaru, menandai `needs_review = True`, mencatat `KrsTransition`, dan memicu notifikasi Observer. |
| `DELETE` | `/api/schedules/{id}` | `200 OK` | `404` | Menghapus jadwal kuliah, menandai KRS terdampak `needs_review = True`, dan memicu notifikasi Observer. |
| `GET` | `/api/schedules/conflicts` | `200 OK` | - | Mendeteksi seluruh pasangan jadwal yang mengalami bentrok ruangan, dosen, atau waktu. |
| `POST` | `/api/schedules/{id}/suggestions` | `200 OK` | `404` | Menghasilkan maksimal **3 alternatif jadwal** bebas bentrok berbasis CSP. |
| `GET` | `/api/admin/scheduling/dashboard` | `200 OK` | - | Mengembalikan data terstruktur untuk halaman Conflict Resolver Dashboard. |

---

## 6. Modul Nilai & Transkrip PDF (`/api/grades` — Minggu 9–10, P2, & P5)

| Method | Endpoint | Status Sukses | Status Error | Deskripsi |
|---|---|---|---|---|
| `POST` | `/api/grades/input` | `201 Created` | `400`, `404` | Input nilai mahasiswa (`nim`, `matakuliah_id`, `semester`, `nilai_huruf`, `presensi_persen`). Ditolak `400` jika `presensi_persen < 75.0`. |
| `PUT` | `/api/grades/update/{grade_id}` | `200 OK` | `400`, `404` | Memperbarui nilai mahasiswa (`nilai_huruf_baru`, `changed_by`, `reason` wajib). Memicu SQLite Trigger `trg_grade_history_update` untuk mencatat riwayat ke `grade_history`. |
| `GET` | `/api/grades/history/{nim}` | `200 OK` | - | Menampilkan riwayat audit perubahan nilai mahasiswa dari view `v_grade_history`. |
| `GET` | `/api/grades/ips/{nim}/{semester}` | `200 OK` | - | Menghitung IPS semester tertentu (nilai `A`/`B`/`C`/`D` dengan bobot $\ge 1.0$ dihitung lulus). |
| `GET` | `/api/grades/ipk/{nim}` | `200 OK` | - | Menghitung IPK kumulatif (mengambil nilai tertinggi jika mata kuliah diulang, mengecualikan nilai `E`). |
| `GET` | `/api/grades/transcript/{nim}` | `200 OK` | `404` | Mengembalikan data lengkap Transkrip Akademik dalam format JSON. |
| `GET` | `/api/grades/transcript/{nim}/pdf` | `200 OK` | `404` | Mengunduh dokumen **PDF Transkrip Akademik Resmi** (`application/pdf`) yang dihasilkan oleh `ReportLab`. |

---

## 7. Modul Keuangan SPP, APScheduler, & Webhook (`/api/billing` & `/api/payments` — Minggu 11 & P1)

| Method | Endpoint | Status Sukses | Status Error | Deskripsi |
|---|---|---|---|---|
| `POST` | `/api/billing/generate` | `201 Created` | `400`, `404`, `409` | Membuat tagihan SPP individu untuk seorang mahasiswa pada semester tertentu. |
| `POST` | `/api/billing/generate-semester` | `200 OK` | `400` | Membuat tagihan SPP massal seluruh mahasiswa aktif berdasarkan tarif program studi dengan jatuh tempo 14 hari setelah awal semester (idempotent). |
| `GET` | `/api/billing/{billing_id}/late-fee` | `200 OK` | `404` | Menghitung denda keterlambatan tagihan SPP. |
| `PUT` | `/api/billing/{billing_id}/status` | `200 OK` | `404` | Memperbarui status tagihan (`unpaid`, `partial`, `paid`, `overdue`). |
| `POST` | `/api/billing/reminders/run` | `200 OK` | - | Menjalankan job pengiriman pengingat otomatis untuk seluruh tagihan yang melewati jatuh tempo (`overdue`). |
| `GET` | `/api/billing/scheduler/status` | `200 OK` | - | Menampilkan status `APScheduler` (`BackgroundScheduler`) beserta daftar job `CronTrigger` aktif dan `next_run_time`. |
| `GET` | `/api/billing/dashboard` | `200 OK` | - | Mengembalikan metrik Dashboard Keuangan real-time (tagihan mahasiswa, collection rate per prodi, rekap bulanan, daftar penunggak). |
| `GET` | `/api/billing/ai-report` | `200 OK` | - | Menghasilkan laporan *AI Financial Insights* berformat JSON (`collection_rate`, `prediksi_pendapatan`, `mahasiswa_berisiko`, `rekomendasi_tindakan`). |
| `POST` | `/api/payments/create` | `201 Created` | `400`, `404`, `409` | Membuat transaksi pembayaran berstatus `pending`. |
| `POST` | `/api/payments/process` | `200 OK` | `400`, `404`, `409` | Memproses pembayaran secara atomic (mendukung cicilan `partial` dan pelunasan `paid`, mencegah duplikasi `reference_number`, dan mengirim bukti pembayaran ke `notification_log`). |
| `POST` | `/api/payments/webhook` | `200 OK` | `400`, `401`, `404` | Menerima callback Payment Gateway, memverifikasi header `X-Webhook-Signature` (HMAC-SHA256), menjamin *idempotency* `transaction_id`, dan memperbarui status tagihan. |
| `POST` | `/api/payments/webhook/simulate-signature` | `200 OK` | `400` | Menghasilkan signature HMAC-SHA256 valid untuk pengujian endpoint webhook. |
| `POST` | `/api/payments/{payment_id}/confirm` | `200 OK` | `400`, `404` | Mengonfirmasi pembayaran `pending` menjadi `success`. |
| `POST` | `/api/payments/{payment_id}/fail` | `200 OK` | `400`, `404` | Menandai pembayaran `pending` menjadi `failed`. |
