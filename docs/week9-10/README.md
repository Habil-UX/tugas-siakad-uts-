# DOKUMENTASI MINGGU 9–10
## GRADE MANAGEMENT DAN AUDIT TRAIL

## 1. Deskripsi

Modul Grade Management merupakan pengembangan Sistem Informasi Akademik untuk mengelola nilai mahasiswa, menghitung Indeks Prestasi Semester (IPS), menghitung Indeks Prestasi Kumulatif (IPK), dan menghasilkan transkrip akademik.

Modul ini menerapkan mekanisme Audit Trail untuk mencatat perubahan nilai secara otomatis sehingga perubahan dapat ditelusuri berdasarkan nilai lama, nilai baru, identitas pengubah, waktu perubahan, dan alasan perubahan.

## 2. Fitur Utama

### 2.1 Input Nilai

- Memasukkan nilai mahasiswa berdasarkan NIM dan mata kuliah.
- Memvalidasi keberadaan mahasiswa.
- Memvalidasi keberadaan mata kuliah.
- Memastikan presensi minimal 75%.
- Memvalidasi skala nilai.
- Mencegah duplikasi nilai berdasarkan mahasiswa, mata kuliah, dan semester.

### 2.2 Update Nilai

- Memperbarui nilai mahasiswa.
- Memvalidasi nilai baru.
- Mencatat identitas pengubah.
- Mencatat alasan perubahan.
- Menggunakan transaksi database.
- Memperbarui versi data nilai.

### 2.3 Audit Trail

Sistem menggunakan Database Trigger untuk mencatat perubahan nilai secara otomatis ke tabel `grade_history`.

Informasi yang dicatat:
- Grade ID.
- Nilai lama.
- Nilai baru.
- Identitas pengubah.
- Waktu perubahan.
- Alasan perubahan.

### 2.4 Perhitungan IPS dan IPK

Sistem menyediakan perhitungan IPS berdasarkan semester dan IPK berdasarkan keseluruhan riwayat akademik.

Perhitungan menggunakan bobot nilai mata kuliah.

Batas kelulusan yang digunakan adalah bobot minimal 2.0.

### 2.5 Transkrip Akademik

Sistem menghasilkan transkrip akademik dalam format JSON dan PDF.

Informasi yang disediakan:
- Identitas mahasiswa.
- NIM.
- Program studi.
- Daftar mata kuliah.
- Semester.
- SKS.
- Nilai huruf.
- Bobot nilai.
- Status kelulusan.
- Total SKS.
- Total SKS lulus.
- IPK.
- Predikat akademik.

## 3. Teknologi

- Python 3.11.
- FastAPI.
- SQLAlchemy 2.0.
- SQLite.
- Alembic.
- Pydantic.
- ReportLab.
- Pytest.
- Pytest-Cov.

## 4. Struktur Database

### 4.1 Tabel grade_history

Menyimpan catatan perubahan nilai mahasiswa.

Kolom:
- id
- grade_id
- old_value
- new_value
- changed_by
- changed_at
- reason

### 4.2 Tabel grade_audit_context

Menyimpan metadata perubahan sebelum proses UPDATE.

Kolom:
- grade_id
- changed_by
- reason

### 4.3 Trigger trg_grade_history_update

Trigger dijalankan setelah perubahan kolom `skala_nilai_id` pada tabel `riwayat_nilai`.

Trigger melakukan:
1. Mendeteksi perubahan nilai.
2. Mengambil nilai sebelumnya dan nilai terbaru.
3. Mengambil metadata pengubah.
4. Menyimpan catatan ke `grade_history`.
5. Menghapus metadata yang telah digunakan.

### 4.4 View v_grade_history

View menggabungkan informasi riwayat perubahan nilai dengan data mahasiswa dan mata kuliah.

## 5. API Endpoint

| Method | Endpoint | Fungsi |
|---|---|---|
| POST | `/api/grades/input` | Input nilai |
| PUT | `/api/grades/update/{grade_id}` | Update nilai |
| GET | `/api/grades/history/{nim}` | Riwayat perubahan nilai |
| GET | `/api/grades/ips/{nim}/{semester}` | Menghitung IPS |
| GET | `/api/grades/ipk/{nim}` | Menghitung IPK |
| GET | `/api/grades/transcript/{nim}` | Transkrip JSON |
| GET | `/api/grades/transcript/{nim}/pdf` | Download transkrip PDF |

## 6. Mekanisme Audit Trail

Alur perubahan nilai:

1. Pengguna mengirim permintaan perubahan nilai.
2. Sistem memvalidasi data.
3. Sistem menyimpan metadata pengubah dan alasan perubahan.
4. Sistem memperbarui nilai pada `riwayat_nilai`.
5. Database Trigger mendeteksi perubahan.
6. Trigger memasukkan catatan ke `grade_history`.
7. Metadata perubahan dihapus.
8. Transaksi diselesaikan.

## 7. Lokasi Implementasi

| Komponen | Lokasi |
|---|---|
| Grade Router | `app/routers/grades.py` |
| Grade Service | `app/services/grade_service.py` |
| Transcript Service | `app/services/transcript_service.py` |
| GPA Calculator | `app/services/gpa_calculator.py` |
| Grade Schema | `app/schemas/grade.py` |
| Grade History Model | `app/models/grade_history.py` |
| PDF Generator | `app/utils/pdf_generator.py` |
| Database Migration | `alembic/versions/` |

## 8. Pengujian

Pengujian dilakukan menggunakan Pytest dan Pytest-Cov.

Perintah:

```powershell
pytest --cov=app --cov-report=term-missing --cov-report=html
```

Hasil verifikasi akhir proyek:

- Code coverage: 100%.
- Missed statements: 0.
- Test failed: 0.

Rincian jumlah pengujian tersedia dalam `docs/FINAL-TEST-REPORT.md`.

## 9. Dokumentasi Pendukung

- `ADR-001-Audit-Trail.md`
- `API-DOCUMENTATION.md`
- `audit-trail-flow.mmd`

## 10. Kesimpulan

Modul Minggu 9–10 meningkatkan kemampuan pengelolaan data akademik melalui mekanisme Grade Management dan Audit Trail.

Penggunaan Database Trigger memungkinkan pencatatan perubahan nilai secara otomatis, sedangkan Transcript Service dan GPA Calculator mendukung penyajian informasi akademik mahasiswa.

Modul ini menjadi bagian dari integrasi Sistem Informasi Akademik secara keseluruhan.