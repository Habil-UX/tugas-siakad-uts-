# ADR-007: Strategi Validasi Pembayaran SPP, Webhook Idempotent, dan Pembatasan KRS

## Status
Diterapkan.

## Konteks
Modul Keuangan SPP (Minggu 11) harus mengelola tagihan semester (`billing`), transaksi pembayaran (`payment`), konfirmasi payment gateway via webhook, serta memblokir pengisian KRS bagi mahasiswa yang menunggak.

## Keputusan
1. **Idempotent Semester Billing Generator**: `generate_semester_billing` memeriksa keberadaan tagihan `(nim, semester_akademik, tahun_akademik)` sebelum membuat tagihan baru sehingga aman dijalankan ulang oleh cron job / scheduler.
2. **Atomic Payment Processing**: `process_payment` menggunakan transaksi database dengan row lock (`with_for_update()`), memvalidasi nominal terhadap sisa tagihan, memperbarui status `billing` (`unpaid` / `partial` / `paid` / `overdue`), dan mencatat pengiriman bukti bayar (receipt) ke `notification_log`.
3. **Webhook Security & Idempotency**: `handle_webhook` memverifikasi signature HMAC-SHA256 atas payload kanonik menggunakan `WEBHOOK_SECRET`. Nomor transaksi gateway disimpan pada kolom `payment.reference_number` (`UNIQUE`) sehingga pengiriman ulang webhook yang sama bersifat idempotent (`200 OK`, `"idempotent": True`) tanpa menggandakan pembayaran.
4. **Integrasi Pembatasan KRS**: `KRSManager._check_payment_arrears` memeriksa secara langsung di database apakah mahasiswa memiliki tagihan berstatus `overdue` (melewati `due_date` dengan sisa tagihan > 0). Jika ada, `add_course` dan `submit_krs` ditolak di backend dengan HTTP 403, dan otomatis dibuka kembali segera setelah tagihan dilunasi.
