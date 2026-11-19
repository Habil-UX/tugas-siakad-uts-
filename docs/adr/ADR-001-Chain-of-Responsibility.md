# ADR-001: Strategi Chain of Responsibility untuk Validasi KRS

## Status
Diterapkan & Disempurnakan (Audit Minggu 3–11).

## Konteks
Dalam proses penambahan mata kuliah (`add_course`) dan validasi keseluruhan KRS (`validate_krs`), sistem harus memeriksa empat aturan bisnis secara konsisten:
1. `SKSValidator`: Total SKS <= 24 SKS per semester.
2. `PrerequisiteValidator`: Mata kuliah prasyarat telah lulus dengan nilai minimal C (bobot >= 2.0) pada semester sebelumnya.
3. `ConflictValidator`: Tidak ada jadwal mata kuliah yang beririsan pada hari dan jam yang sama.
4. `DuplicateValidator`: Tidak ada pengambilan mata kuliah yang sama dua kali pada KRS yang sama.

## Keputusan
Menggunakan **Chain of Responsibility Pattern** melalui base class abstrak `Validator` dan `ValidationResult`, yang dirakit menggunakan fungsi `build_chain(stop_on_first_error: bool = True)`.

Urutan rantai:
`SKSValidator -> PrerequisiteValidator -> ConflictValidator -> DuplicateValidator`.

Sistem mendukung dua strategi eksplisit:
1. **Fail-Fast (`stop_on_first_error=True`)**: Rantai berhenti pada pelanggaran pertama. Digunakan pada operasi interaktif `add_course(nim, kode_mk)` agar menghemat query database apabila batas SKS sudah terlampaui.
2. **Collect-All (`stop_on_first_error=False`)**: Rantai mengeksekusi seluruh validator (`validate_all(context)`) dan mengumpulkan seluruh pesan kesalahan. Digunakan pada pemeriksaan menyeluruh `validate_krs(nim)`.

Selain itu, `ConflictValidator` mengecualikan pembandingan mata kuliah dengan dirinya sendiri (`detail.matakuliah_id == new_mk.id`) sehingga pendaftaran mata kuliah ganda ditangkap secara akurat oleh `DuplicateValidator`.

## Konsekuensi
- Pemisahan tanggung jawab (Single Responsibility Principle) untuk setiap aturan bisnis.
- Fleksibilitas memilih mode *fail-fast* atau *collect-all* sesuai konteks pemanggilan.
