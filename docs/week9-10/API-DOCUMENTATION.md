# API DOCUMENTATION
## GRADE MANAGEMENT

Base URL:

```text
http://127.0.0.1:8000
```

Prefix:

```text
/api/grades
```

Seluruh endpoint dapat diuji melalui Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## 1. Input Nilai Mahasiswa

**Endpoint**

```http
POST /api/grades/input
```

**Request Body**

```json
{
  "nim": "12345678",
  "matakuliah_id": 1,
  "semester": 1,
  "nilai_huruf": "A",
  "presensi_persen": 90,
  "changed_by": "admin"
}
```

**Validasi**

- Mahasiswa harus terdaftar.
- Mata kuliah harus tersedia.
- Presensi minimal 75%.
- Nilai harus sesuai skala A, B, C, D, atau E.
- Kombinasi mahasiswa, mata kuliah, dan semester tidak boleh duplikat.

**Kemungkinan HTTP Status**

- 200: Berhasil.
- 400: Validasi gagal.
- 404: Mahasiswa atau mata kuliah tidak ditemukan.
- 409: Nilai sudah tersedia.

## 2. Update Nilai Mahasiswa

**Endpoint**

```http
PUT /api/grades/update/{grade_id}
```

**Request Body**

```json
{
  "nilai_huruf": "A",
  "changed_by": "admin",
  "reason": "Koreksi nilai mahasiswa"
}
```

**Validasi**

- Grade ID harus tersedia.
- Skala nilai baru harus valid.
- Identitas pengubah wajib diisi.
- Alasan perubahan minimal lima karakter.

Perubahan nilai akan memicu Database Trigger untuk mencatat riwayat perubahan.

**Kemungkinan HTTP Status**

- 200: Berhasil.
- 400: Skala nilai tidak valid.
- 404: Data nilai tidak ditemukan.
- 500: Skala nilai lama tidak ditemukan.

## 3. Riwayat Perubahan Nilai

**Endpoint**

```http
GET /api/grades/history/{nim}
```

Endpoint mengambil riwayat perubahan nilai berdasarkan NIM melalui database view `v_grade_history`.

Informasi yang disediakan meliputi:
- history_id
- nim
- nama_mahasiswa
- kode_mk
- nama_mk
- semester
- grade_id
- nilai_lama
- nilai_baru
- changed_by
- changed_at
- reason

## 4. Perhitungan IPS

**Endpoint**

```http
GET /api/grades/ips/{nim}/{semester}
```

Contoh:

```http
GET /api/grades/ips/12345678/1
```

Menghasilkan perhitungan Indeks Prestasi Semester berdasarkan mata kuliah mahasiswa pada semester yang diminta.

## 5. Perhitungan IPK

**Endpoint**

```http
GET /api/grades/ipk/{nim}
```

Contoh:

```http
GET /api/grades/ipk/12345678
```

Menghasilkan:
- NIM.
- IPK.
- Total SKS.
- Total SKS lulus.
- Total mutu.
- Jumlah mata kuliah.

## 6. Transkrip Akademik JSON

**Endpoint**

```http
GET /api/grades/transcript/{nim}
```

Menghasilkan data transkrip akademik mahasiswa dalam format JSON.

Informasi mencakup identitas mahasiswa, program studi, daftar mata kuliah, nilai, SKS, status kelulusan, IPS setiap semester, IPK, dan predikat akademik sesuai data yang tersedia.

## 7. Download Transkrip PDF

**Endpoint**

```http
GET /api/grades/transcript/{nim}/pdf
```

Contoh:

```http
GET /api/grades/transcript/12345678/pdf
```

Endpoint menghasilkan dokumen PDF menggunakan ReportLab.

Response:

```text
Content-Type: application/pdf
Content-Disposition: attachment
```

Nama file:

```text
transkrip_12345678.pdf
```

## 8. Mekanisme Audit Trail

Alur perubahan nilai:

1. Permintaan update diterima API.
2. Grade Service melakukan validasi.
3. Metadata perubahan disimpan pada `grade_audit_context`.
4. Nilai pada `riwayat_nilai` diperbarui.
5. Trigger `trg_grade_history_update` dijalankan.
6. Riwayat perubahan dimasukkan ke `grade_history`.
7. Metadata audit dihapus.
8. Transaksi database diselesaikan.

## 9. Pengujian API

Pengujian dilakukan melalui:
- FastAPI TestClient.
- Pytest.
- Validasi request dan response.
- Pengujian kondisi normal dan kesalahan.
- Pengujian transaksi database.

Dokumentasi pengujian keseluruhan tersedia pada:

`docs/FINAL-TEST-REPORT.md`