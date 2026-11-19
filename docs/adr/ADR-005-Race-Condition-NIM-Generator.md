# ADR-005: Penanganan Race Condition dan Idempotensi pada NIM Generator

## Status
Diterapkan & Diverifikasi dengan Multi-Thread Concurrency Test (P4).

## Konteks
Saat calon mahasiswa disetujui (`PUT /api/pmb/approve/{id}`), sistem menghasilkan Nomor Induk Mahasiswa (NIM) dengan format institusional `YYYY + KODE_PRODI + '-' + RUNNING_NUMBER_4_DIGIT` (contoh: `2025001-0001` atau `2025TIF-0001`). Dua atau lebih proses approval paralel berpotensi menghasilkan nomor urut ganda atau kegagalan database lock apabila tidak dilindungi dengan benar.

## Keputusan
1. Menyimpan counter per `(tahun, program_studi_id)` pada tabel `nim_sequences` dengan constraint `UNIQUE(tahun, program_studi_id)` serta constraint `UNIQUE` pada kolom `calon_mahasiswa.nim`.
2. Pada SQLite, mengaktifkan `PRAGMA busy_timeout = 30000` dan akuisisi kunci tulis di awal transaksi (`BEGIN IMMEDIATE`) yang dikombinasikan dengan sinkronisasi lock (`_NIM_LOCK`), `with_for_update()` (untuk kompatibilitas PostgreSQL/MySQL), serta mekanisme retry eksponensial pada `OperationalError` / `IntegrityError`.
3. Menjamin sifat **idempotent** pada `approve_calon_mahasiswa`: apabila pendaftar sudah berstatus `approved` dan telah memiliki `nim`, pemanggilan paralel maupun berulang mengembalikan data mahasiswa tersebut tanpa membuat NIM baru.
4. Diuji secara nyata menggunakan `ThreadPoolExecutor` (8 worker paralel disinkronkan dengan `threading.Barrier(8)`) pada database SQLite berbasis file.
