# DOKUMENTASI MINGGU 11
## BILLING MANAGEMENT DAN PAYMENT MANAGEMENT

## 1. Tujuan

Minggu 11 memperluas Sistem Informasi Akademik dengan modul keuangan untuk mengelola tagihan mahasiswa dan transaksi pembayaran.

Komponen yang ditambahkan:
- Finance Models.
- Finance Schemas.
- Billing Service.
- Payment Service.
- Billing Router.
- Payment Router.
- Migrasi database Alembic.

## 2. Model Data

Model keuangan berada pada `app/models/finance_models.py`.

### 2.1 Billing

Tabel: `billing`

Kolom utama:
- `id`
- `nim`
- `semester_akademik`
- `tahun_akademik`
- `amount`
- `due_date`
- `status`
- `created_at`
- `updated_at`

Relasi:
- `nim` mengacu pada `calon_mahasiswa.nim`.
- Satu Billing dapat memiliki beberapa Payment.

Constraint:
- Kombinasi NIM, semester, dan tahun akademik unik.
- Nominal tagihan harus lebih besar dari nol.
- Status dibatasi pada `unpaid`, `partial`, `paid`, dan `overdue`.

### 2.2 Payment Method

Tabel: `payment_method`

Kolom utama:
- `id`
- `code`
- `name`
- `is_active`
- `created_at`

Kode metode pembayaran bersifat unik. Metode yang tidak aktif tidak boleh digunakan untuk transaksi baru sesuai validasi service.

### 2.3 Payment

Tabel: `payment`

Kolom utama:
- `id`
- `billing_id`
- `payment_method_id`
- `amount`
- `status`
- `reference_number`
- `paid_at`
- `created_at`
- `updated_at`

Relasi:
- `billing_id` mengacu pada `billing.id`.
- `payment_method_id` mengacu pada `payment_method.id`.

Constraint:
- Nominal pembayaran harus lebih besar dari nol.
- Status dibatasi pada `pending`, `success`, dan `failed`.
- Nomor referensi unik apabila diisi.

## 3. Aturan Billing

Konfigurasi pada `BillingService`:
- Tarif kategori program studi teknik: Rp5.000.000.
- Tarif kategori program studi ekonomi: Rp4.000.000.
- Denda: 1% dari sisa tagihan untuk setiap periode keterlambatan 30 hari.
- Jatuh tempo: 14 hari setelah tanggal awal semester.

Penentuan tarif dilakukan berdasarkan teks nama program studi dan fakultas. Program studi yang tidak termasuk kategori tarif yang dikenali memerlukan konfigurasi tarif tambahan.

Perhitungan denda menggunakan jumlah hari terlambat dibagi dalam periode 30 hari penuh. Denda dihitung atas sisa tagihan setelah pembayaran berhasil diperhitungkan.

Status tagihan:
- `paid` jika jumlah pembayaran berhasil telah mencapai atau melebihi nominal tagihan.
- `overdue` jika belum lunas dan tanggal pemeriksaan melewati tanggal jatuh tempo.
- `partial` jika ada pembayaran tetapi belum melewati jatuh tempo.
- `unpaid` jika belum ada pembayaran dan belum melewati jatuh tempo.

Urutan kondisi mengikuti implementasi `BillingService`.

## 4. Aturan Payment

Payment Service menyediakan fungsi untuk:
- Menormalisasi dan memvalidasi nominal.
- Mengambil tagihan.
- Mengambil metode pembayaran dan memeriksa status aktifnya.
- Membuat transaksi pembayaran.
- Menghitung pembayaran berhasil.
- Memeriksa batas sisa tagihan.
- Mengonfirmasi pembayaran.
- Memvalidasi nomor referensi.
- Menangani konfirmasi idempotent.
- Menandai pembayaran gagal.
- Menyinkronkan status tagihan.

Status transaksi:
- `pending`: transaksi dibuat dan belum dikonfirmasi berhasil.
- `success`: pembayaran telah dikonfirmasi berhasil.
- `failed`: transaksi ditandai gagal.

Konfirmasi pembayaran harus mengikuti validasi service dan constraint database. Jangan mengubah status transaksi secara langsung di database untuk menggantikan alur service.

## 5. Alur Proses

### Pembuatan Tagihan
1. Client mengirim NIM, semester, tahun akademik, dan tanggal awal semester.
2. Billing Service memvalidasi semester dan keberadaan mahasiswa.
3. Service memeriksa apakah tagihan periode tersebut sudah ada.
4. Service menentukan tarif berdasarkan program studi.
5. Service menentukan tanggal jatuh tempo.
6. Tagihan disimpan dengan status awal `unpaid`.

### Pembayaran
1. Client membuat transaksi dengan billing ID, metode pembayaran, dan nominal.
2. Payment Service memvalidasi tagihan dan metode pembayaran.
3. Service memvalidasi nominal terhadap sisa tagihan.
4. Transaksi dibuat dengan status awal sesuai implementasi.
5. Transaksi kemudian dikonfirmasi atau ditandai gagal.
6. Pembayaran berhasil diperhitungkan untuk menyinkronkan status tagihan.

## 6. Integrasi Aplikasi

`app/main.py` mendaftarkan:
- `billing.router`
- `payment.router`

Prefix router:
- `/api/billing`
- `/api/payments`

Judul aplikasi: `Sistem Informasi Akademik`  
Versi API: `11.0`

## 7. Batasan Ruang Lingkup

Dokumentasi kode yang tersedia menunjukkan proses pembuatan dan konfirmasi transaksi melalui API. Tidak ada bukti pada implementasi yang ditinjau bahwa aplikasi telah terhubung ke payment gateway atau sistem perbankan eksternal.

Untuk penggunaan produksi, tarif, kebijakan denda, otorisasi operator, rekonsiliasi, dan integrasi penyedia pembayaran perlu ditinjau sesuai kebijakan institusi.