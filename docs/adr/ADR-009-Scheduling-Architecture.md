# ADR-009: Scheduling Architecture
## Context
Sistem membutuhkan pengelolaan jadwal kuliah yang mendeteksi bentrok (ruangan, dosen, waktu) serta memvalidasi kapasitas ruangan.
## Decision
Menggunakan `SchedulingService` yang memisahkan logika CRUD, validasi bentrok (`ConflictDetector`), dan validasi kapasitas.
## Consequences
- Kode lebih modular (Single Responsibility Principle).
- Deteksi bentrok menggunakan pendekatan Pairwise \(O(N^2)\) untuk list jadwal di hari yang sama. Hal ini dipilih karena jumlah jadwal per hari relatif kecil. Jika data membesar, dapat dioptimasi dengan Interval Tree.