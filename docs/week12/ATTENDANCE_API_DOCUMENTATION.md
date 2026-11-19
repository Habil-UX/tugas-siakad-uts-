# DOKUMENTASI REST API MODUL PRESENSI QR CODE (`ATTENDANCE_API_DOCUMENTATION.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 12  
**Base URL:** `http://127.0.0.1:8000`

---

## 1. Daftar Endpoint Modul Presensi (Minggu 12)

| Method | Path Endpoint | Role / Otorisasi | Content-Type Respons | Deskripsi |
|---|---|---|---|---|
| `GET` | `/attendance/qr/{schedule_id}` | `dosen`, `admin` | `image/png` | Menghasilkan gambar PNG QR Code presensi (berlaku maks 15 menit) beserta HTTP header countdown (`X-Attendance-Expires-In`, `X-Attendance-JTI`, `X-Attendance-Phase`). |
| `POST` | `/attendance/qr/{schedule_id}/generate` | `dosen`, `admin` | `application/json` | Menerbitkan QR baru (fase `NORMAL` atau `LATE` keterlambatan), mencabut token lama jika `revoke_previous=true`, dan mengembalikan token JWT + data PNG Base64 + countdown. |
| `POST` | `/attendance/scan` | `mahasiswa`, `admin` | `application/json` | Memvalidasi scan QR mahasiswa (`token`, `nim`) terhadap signature HS256, expiration, `jti`, hari kuliah, KRS `APPROVED`, anti-duplikat, rate limit, dan menyimpan status `HADIR` ($\le 15$m) atau `TERLAMBAT` ($15\text{–}30$m). |
| `GET` | `/attendance/session/{session_id}/records` | Publik / Dosen | `application/json` | Menampilkan daftar mahasiswa yang telah berhasil melakukan presensi pada sesi kuliah tertentu. |
| `POST` | `/attendance/session/{session_id}/close` | `dosen`, `admin` | `application/json` | Menutup sesi presensi (`session_status = "CLOSED"`). |
| `GET` | `/attendance/report` | `dosen`, `admin` | `application/json` | Laporan presensi per mahasiswa per mata kuliah beserta indikator warning kehadiran $<75\%$. |
| `GET` | `/attendance/report/export` | `dosen`, `admin` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Mengunduh laporan presensi dan status warning dalam format file Microsoft Excel (`.xlsx`). |
| `GET` | `/attendance/ai-insights` | `dosen`, `admin` | `application/json` | Menganalisis data presensi aktual dari database untuk mendeteksi pola absensi hari/jam, early warning $<75\%$, dan rekomendasi tindakan. |
| `POST` | `/attendance/ai-insights` | `dosen`, `admin` | `application/json` | Menganalisis array JSON `attendance_records` atau filter jadwal menggunakan `AIAttendanceAnalyzer`. |
| `GET` | `/attendance-ui` | Browser UI | `text/html` | Halaman antarmuka web responsif untuk Dosen (Generate QR, Countdown, Laporan, Excel, AI Insights) dan Mahasiswa (Kamera QR Scanner + Manual Fallback). |

---

## 2. Detail Kontrak Request & Response

### 2.1. `GET /attendance/qr/{schedule_id}`
- **Query Parameters Opsional:**
  - `valid_minutes` (`int`, default `15`, rentang `1..15`)
  - `session_date` (`YYYY-MM-DD`, default tanggal hari ini di `Asia/Jakarta`)
  - `phase` (`NORMAL` atau `LATE`)
- **Headers Respons:**
  - `Content-Type: image/png`
  - `X-Attendance-Token: <jwt_token_hs256>`
  - `X-Attendance-Session-Id: <session_id>`
  - `X-Attendance-JTI: <unique_uuid_hex>`
  - `X-Attendance-Expires-At: <iso8601_timestamp>`
  - `X-Attendance-Expires-In: <remaining_seconds>`

### 2.2. `POST /attendance/scan`
- **Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "nim": "2026TIF-0101"
}
```
- **Response Sukses (`200 OK`):**
```json
{
  "success": true,
  "status": "hadir",
  "attendance_status": "HADIR",
  "message": "Presensi berhasil dicatat dengan status HADIR (10.0 menit sejak kuliah dimulai)",
  "record_id": 1,
  "session_id": 1,
  "schedule_id": 1,
  "nim": "2026TIF-0101",
  "nama_mahasiswa": "Andi Pratama",
  "kode_mk": "IF401",
  "nama_mk": "Kecerdasan Buatan",
  "scanned_at": "2026-11-16T08:10:00",
  "elapsed_minutes": 10.0
}
```
- **Kode Error:**
  - `400 Bad Request`: Token expired, signature tidak valid, token sudah dicabut, bukan hari jadwal kuliah, atau melewati batas 30 menit sejak waktu mulai kuliah.
  - `403 Forbidden`: Mahasiswa tidak terdaftar di mata kuliah pada KRS `APPROVED`, mencoba scan QR kelas lain, atau mencoba memalsukan NIM mahasiswa lain.
  - `404 Not Found`: Mahasiswa atau jadwal kuliah tidak ditemukan.
  - `409 Conflict`: Mahasiswa sudah melakukan presensi pada sesi ini (duplikat).
  - `429 Too Many Requests`: Melebihi batas rate limit (maksimal 5 percobaan scan dalam 60 detik).
