# ADR-002: Optimasi Query Prasyarat dengan NOT EXISTS dan EXPLAIN QUERY PLAN

## Status
Diterapkan & Diverifikasi.

## Konteks
Sistem harus memeriksa apakah mahasiswa telah mengambil dan lulus (nilai >= C / bobot >= 2.0) seluruh mata kuliah prasyarat pada semester sebelumnya sebelum mengizinkan pengambilan mata kuliah lanjutan.

## Keputusan
1. Menggunakan berkas query `SELECT ... JOIN prerequisite WHERE NOT EXISTS (...)` yang memfilter `riwayat_nilai.nim`, `riwayat_nilai.matakuliah_id`, `skala_nilai.bobot >= 2.0`, dan `riwayat_nilai.semester < krs.semester_akademik` (untuk semester > 1).
2. Menambahkan composite index `ix_riwayat_nilai_nim_mk_skala` pada `riwayat_nilai(nim, matakuliah_id, skala_nilai_id)` selain index `ix_prerequisite_matakuliah_id`.
3. Menyediakan fungsi `PrerequisiteValidator.explain_prerequisite_query` dan endpoint `GET /api/krs/explain-prerequisite/{nim}/{matakuliah_id}` untuk mengeksekusi `EXPLAIN QUERY PLAN` secara nyata.

## Bukti Execution Plan (SQLite)
Hasil eksekusi `EXPLAIN QUERY PLAN` menunjukkan penggunaan index:
- `SEARCH prerequisite USING INDEX ix_prerequisite_matakuliah_id (matakuliah_id=?)`
- `SEARCH matakuliah USING INTEGER PRIMARY KEY (rowid=?)`
- `CORRELATED SCALAR SUBQUERY`
  - `SEARCH riwayat_nilai USING INDEX ix_riwayat_nilai_nim_mk_skala (nim=? AND matakuliah_id=?)`
  - `SEARCH skala_nilai USING INTEGER PRIMARY KEY (rowid=?)`

## Konsekuensi
- Menghindari *full table scan* pada tabel `riwayat_nilai` dan `prerequisite`.
- Menyediakan bukti `EXPLAIN QUERY PLAN` yang dapat diuji langsung melalui automated test.
