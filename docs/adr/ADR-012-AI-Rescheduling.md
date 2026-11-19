# ADR-012: AI-Powered Rescheduling
## Context
Admin membutuhkan saran jadwal alternatif saat terjadi bentrok.
## Decision
Menggunakan pendekatan Constraint Satisfaction Problem (CSP) untuk mengecek ketersediaan slot kosong (ruangan & dosen), lalu mengembalikan maksimal 3 alternatif terbaik.
## Consequences
- Rekomendasi bersifat *read-only* (tidak langsung mengubah database).
- Admin harus mengonfirmasi perubahan secara manual.