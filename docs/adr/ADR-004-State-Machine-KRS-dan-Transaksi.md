# ADR-004: State Machine KRS dan Manajemen Transaksi Persetujuan

## Status
Diterapkan.

## Konteks
Siklus hidup Kartu Rencana Studi (KRS) membutuhkan transisi status yang ketat antara Mahasiswa dan Dosen Pembimbing Akademik (Dosen PA), serta jaminan integritas data saat proses submit, revisi, dan persetujuan.

## Keputusan
1. Mendefinisikan enum `KRSStatus` (`DRAFT`, `SUBMITTED`, `APPROVED`, `REVISION`) dan `KRSStateMachine` dengan matriks transisi legal:
   - `DRAFT -> SUBMITTED` (Mahasiswa submit KRS yang tidak kosong dan lolos validasi)
   - `SUBMITTED -> APPROVED` (Dosen PA menyetujui)
   - `SUBMITTED -> REVISION` (Dosen PA meminta revisi)
   - `REVISION -> SUBMITTED` (Mahasiswa memperbaiki dan submit ulang)
2. Seluruh 12 kombinasi transisi lainnya (termasuk `DRAFT -> APPROVED` secara langsung atau perubahan dari `APPROVED`) ditolak sebagai transisi ilegal.
3. Setiap perubahan status dicatat ke tabel audit `krs_transition` (`krs_id`, `from_status`, `to_status`, `changed_by`, `created_at`) dan menaikkan `krs.version` dalam satu transaksi database atomic (`with_for_update()`).
4. Memvalidasi wewenang Dosen PA di backend (`dosen.id == mahasiswa.dosen_pa_id`), menghasilkan HTTP 403 apabila Dosen tidak berwenang dan HTTP 409 apabila Dosen PA belum ditetapkan.
