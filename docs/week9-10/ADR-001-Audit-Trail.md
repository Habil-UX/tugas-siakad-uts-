# ADR-001: Strategi Database Trigger untuk Audit Trail Nilai

## Status
Accepted

## Konteks
Perubahan nilai mahasiswa membutuhkan mekanisme pencatatan yang dapat menunjukkan nilai sebelum perubahan, nilai sesudah perubahan, identitas pengguna, waktu perubahan, dan alasan perubahan.

Pencatatan yang hanya dilakukan melalui aplikasi berisiko tidak berjalan apabila perubahan dilakukan melalui jalur database lain.

## Keputusan
Menggunakan Database Trigger SQLite pada tabel `riwayat_nilai`.

Trigger `trg_grade_history_update` dijalankan setelah perubahan kolom `skala_nilai_id`.

Informasi perubahan disimpan dalam tabel `grade_history`.

Metadata pengubah dan alasan perubahan disimpan sementara pada tabel `grade_audit_context`.

## Alasan
1. Pencatatan dilakukan secara otomatis oleh database.
2. Riwayat perubahan tersimpan secara terstruktur.
3. Pencatatan berlangsung dalam transaksi yang sama dengan perubahan nilai.
4. Riwayat dapat ditampilkan melalui View `v_grade_history`.

## Konsekuensi
- Perubahan nilai menghasilkan catatan audit otomatis.
- Aplikasi harus menyimpan metadata sebelum menjalankan UPDATE.
- Implementasi trigger saat ini menggunakan sintaks SQLite.
- Perubahan langsung melalui database tanpa metadata aplikasi akan menggunakan identitas SYSTEM dan alasan default.