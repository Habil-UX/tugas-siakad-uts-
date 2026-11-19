# DATABASE MIGRATION — MINGGU 11

## 1. Ringkasan

Migrasi Minggu 11 menambahkan tiga tabel untuk pengelolaan keuangan:
- `payment_method`
- `billing`
- `payment`

Informasi revision:
- Revision ID: `9fb882e2b5ae`
- Down revision: `0f9e48bbab1f`
- Message: `add finance billing payment tables`

Migrasi dijalankan menggunakan Alembic pada database SQLite proyek.

## 2. Relasi Tabel

```text
calon_mahasiswa
      |
      | calon_mahasiswa.nim
      v
   billing
      |
      | billing.id
      v
   payment  ------> payment_method
                    payment_method.id
```

Foreign key:
- `billing.nim` → `calon_mahasiswa.nim`
- `payment.billing_id` → `billing.id`
- `payment.payment_method_id` → `payment_method.id`

## 3. Constraint

### payment_method
- Primary key: `id`.
- `code` unik.

### billing
- Primary key: `id`.
- Unique constraint `uq_billing_mahasiswa_semester` pada `nim`, `semester_akademik`, dan `tahun_akademik`.
- Check constraint `amount > 0`.
- Check constraint status hanya `unpaid`, `partial`, `paid`, atau `overdue`.

### payment
- Primary key: `id`.
- Unique constraint pada `reference_number`.
- Check constraint `amount > 0`.
- Check constraint status hanya `pending`, `success`, atau `failed`.

## 4. Index

Migrasi menambahkan index untuk:
- `payment_method.id`
- `billing.id`
- `billing.nim`
- `payment.id`
- `payment.billing_id`

## 5. Perintah Migrasi

Periksa versi migrasi saat ini:

```powershell
alembic current
```

Lihat riwayat migrasi:

```powershell
alembic history
```

Terapkan seluruh migrasi sampai head:

```powershell
alembic upgrade head
```

Setelah migrasi, periksa tabel:

```powershell
@'
from sqlalchemy import inspect
from app.database import engine

inspector = inspect(engine)

for table in [
    "billing",
    "payment",
    "payment_method",
    "calon_mahasiswa",
    "grade_history",
    "riwayat_nilai",
    "krs",
    "prerequisite",
]:
    print(f"{table}: {table in inspector.get_table_names()}")
'@ | python
```

## 6. Backup

Sebelum menjalankan migrasi pada database yang berisi data penting, buat backup file database terlebih dahulu.

Contoh PowerShell untuk SQLite lokal:

```powershell
Copy-Item .\pmb.db ".\pmb_backup_$(Get-Date -Format yyyyMMdd_HHmmss).db"
```

Pastikan file database yang digunakan oleh aplikasi memang `pmb.db` sebelum menjalankan perintah tersebut.

## 7. Catatan

Migrasi yang tercatat telah dijalankan dan `alembic current` sebelumnya menunjukkan `9fb882e2b5ae (head)`. Pemeriksaan tabel juga sebelumnya menunjukkan tabel keuangan dan tabel akademik yang diperiksa tersedia.

Jangan menghapus atau mengubah revisi migrasi lama secara manual tanpa memeriksa riwayat Alembic dan kondisi database.