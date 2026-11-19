# API DOCUMENTATION — MINGGU 11
## BILLING MANAGEMENT, PAYMENT PROCESSING, WEBHOOK & AI FINANCIAL REPORT

Base URL pengembangan:
```text
http://127.0.0.1:8000
```

---

## 1. Billing Management (`/api/billing`)

### 1.1 Generate Tagihan SPP per Mahasiswa
- **Endpoint**: `POST /api/billing/generate`
- **Body**:
```json
{
  "nim": "2026110001",
  "semester": 1,
  "tahun": "2026/2027",
  "semester_start_date": "2026-08-01"
}
```

### 1.2 Generate Tagihan SPP Semester Massal (Idempotent)
- **Endpoint**: `POST /api/billing/generate-semester`
- **Body**:
```json
{
  "semester": 1,
  "tahun": "2026/2027",
  "semester_start_date": "2026-08-01"
}
```
Membuat tagihan SPP untuk seluruh mahasiswa aktif (`status = approved`) berdasarkan tarif program studi (Teknik: Rp5.000.000, Ekonomi: Rp4.000.000, atau kolom `program_studi.tarif_spp`). Jika dijalankan berulang, mahasiswa yang sudah memiliki tagihan pada semester tersebut akan dilewati (`skipped_count`) tanpa membuat duplikat.

### 1.3 Menghitung Denda Keterlambatan
- **Endpoint**: `GET /api/billing/{billing_id}/late-fee?as_of_date=2026-11-15`

### 1.4 Memperbarui Status Tagihan
- **Endpoint**: `PUT /api/billing/{billing_id}/status?as_of_date=2026-11-15`

### 1.5 Menjalankan Job Reminder Tunggakan Otomatis
- **Endpoint**: `POST /api/billing/reminders/run`

### 1.6 Data Dashboard Keuangan & AI Financial Report JSON
- **Dashboard Keuangan**: `GET /api/billing/dashboard` (UI HTML: `GET /finance-dashboard`)
- **AI Financial Report**: `GET /api/billing/ai-report`

---

## 2. Payment Processing & Webhook Simulation (`/api/payments`)

### 2.1 Proses Pembayaran Langsung (`process_payment`)
- **Endpoint**: `POST /api/payments/process`
- **Body**:
```json
{
  "billing_id": 1,
  "amount": "2500000.00",
  "method": "BANK_TRANSFER",
  "reference_number": "PAY-2026-001"
}
```

### 2.2 Simulasi Payment Gateway Webhook (`handle_webhook`) & Pengujian dengan `curl`

1. **Generate HMAC-SHA256 Signature untuk Payload Simulasi**:
```bash
curl -X POST http://127.0.0.1:8000/api/payments/webhook/simulate-signature \
  -H "Content-Type: application/json" \
  -d '{"amount":"2500000.00","billing_id":1,"method":"VIRTUAL_ACCOUNT","status":"paid","transaction_id":"WH-2026-001"}'
```

2. **Kirim Notifikasi Webhook ke `/api/payments/webhook`**:
```bash
curl -X POST http://127.0.0.1:8000/api/payments/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: <SIGNATURE_HASIL_LANGKAH_1>" \
  -d '{"amount":"2500000.00","billing_id":1,"method":"VIRTUAL_ACCOUNT","status":"paid","transaction_id":"WH-2026-001"}'
```
- Jika signature tidak valid, endpoint menolak dengan `401 Unauthorized`.
- Jika `transaction_id` dikirim berulang, endpoint mengembalikan `200 OK` dengan `"idempotent": true` tanpa menduplikasi transaksi pembayaran.
