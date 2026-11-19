# AI USAGE DOCUMENTATION & PROMPT ENGINEERING LOG (MINGGU 1–12 / UTS)
**Proyek:** Perancangan & Implementasi Sistem Informasi Akademik (SIAKAD — SEVIMA Mini)  
**Cakupan:** Desain UML (Minggu 1–2 / UTS) yang Sinkron 100% dengan Implementasi Aktual (Minggu 3–12)

---

## 1. Koleksi 7 Prompt Terbaik (Prompt Pack)

### Prompt 1 — Class Diagram Generator (Hierarki User & 6 Modul Inti SIAKAD)
```text
Anda adalah Senior Software Architect. Buat UML Class Diagram dalam format Mermaid untuk Sistem Informasi Akademik (SIAKAD) yang mencakup:
1. Hierarki User (base class User/AppUser dengan turunan CalonMahasiswa, Mahasiswa, Dosen, Admin).
2. Class inti lintas modul:
   - Modul PMB: ProgramStudi, JalurMasuk, NimSequence, PMBService
   - Modul KRS: Course (Matakuliah), CoursePrerequisite, Enrollment (KRS), EnrollmentItem (KRSDetail), KrsTransition, KRSManager
   - Modul Jadwal: Schedule (JadwalKuliah), Ruangan, ScheduleSubject & ScheduleObserver (StudentObserver, LecturerObserver, AdminObserver)
   - Modul Nilai: Grade (RiwayatNilai), SkalaNilai, GradeHistory, GPACalculator
   - Modul Keuangan: Billing, Payment, PaymentMethod
   - Modul Presensi QR: AttendanceSession, AttendanceQRToken, AttendanceRecord
3. Gunakan visibility modifier (+ public, - private, # protected) pada setiap atribut dan method.
4. Gunakan relasi yang presisi: inheritance (<|--), composition (*--) untuk siklus hidup terikat kuat, dan aggregation (o--) untuk referensi longgar, lengkap dengan kardinalitas (1, 0..*, 1..*).
```

### Prompt 2 — Audit & Refactor Class Diagram ke Prinsip SOLID (Anti-God Object)
```text
Audit class diagram SIAKAD berikut terhadap 5 prinsip SOLID (SRP, OCP, LSP, ISP, DIP).
Identifikasi potensi pelanggaran "God Object" pada class KRSManager dan SchedulingService, lalu refactor dengan:
1. Memisahkan aturan validasi KRS dari KRSManager ke dalam hierarki Chain of Responsibility (abstract class Validator -> SKSValidator, PrerequisiteValidator, ConflictValidator, DuplicateValidator) agar mematuhi Single Responsibility Principle (SRP) dan Open/Closed Principle (OCP).
2. Memisahkan logika pengiriman notifikasi perubahan jadwal dari SchedulingService ke dalam interface ScheduleObserver (StudentObserver, LecturerObserver, AdminObserver) yang dikelola oleh ScheduleSubject agar mematuhi Dependency Inversion Principle (DIP).
```

### Prompt 3 — Use Case Diagram dengan Relasi `<<include>>` dan `<<extend>>`
```text
Buat Use Case Diagram dalam format Mermaid untuk sistem akademik SIAKAD dengan 5 aktor:
1. Calon Mahasiswa
2. Mahasiswa Aktif
3. Dosen / Dosen PA
4. Admin Akademik & Keuangan
5. Sistem PMB & Payment Gateway
Cakup seluruh use case dari pendaftaran PMB, pengisian & approval KRS, pengelolaan jadwal & resolusi konflik, input/edit nilai & unduh transkrip PDF, pembayaran SPP via webhook, hingga presensi QR Code. Tandai secara eksplisit relasi <<include>> (kewajiban validasi) dan <<extend>> (fitur rekomendasi AI CSP).
```

### Prompt 4 — Sequence Diagram Modul PMB & Thread-Safe NIM Generator (Dengan Alternate Flow)
```text
Buat Sequence Diagram Mermaid untuk proses Pendaftaran Mahasiswa Baru (PMB) hingga Approval & Generate NIM:
- Aktor: Calon Mahasiswa, Admin Akademik.
- Komponen: PMBRouter, PydanticValidator, PMBService, SQLite/SQLAlchemy Database.
- Wajib menyertakan Alternate Flow (alt/else):
  1. Format nomor telepon bukan format Indonesia -> HTTP 400 Bad Request.
  2. Email sudah terdaftar -> HTTP 409 Conflict.
  3. Pendaftar sudah pernah di-approve sebelumnya (Idempotent request) -> HTTP 200 OK mengembalikan NIM existing tanpa increment sequence.
  4. Pendaftar berstatus pending -> transaksi BEGIN IMMEDIATE + row lock pada nim_sequences -> generate NIM format [TAHUN][KODE_PRODI]-[4_DIGIT].
```

### Prompt 5 — Sequence Diagram Validasi KRS, Chain of Responsibility & State Machine Approval
```text
Buat Sequence Diagram Mermaid untuk proses pengisian, validasi, submit, dan persetujuan KRS:
1. Mahasiswa memanggil POST /api/krs/add -> KRSManager memeriksa tunggakan SPP overdue (tolak HTTP 403 jika menunggak).
2. Eksekusi berantai Chain of Responsibility:
   - SKSValidator (total SKS <= 24)
   - PrerequisiteValidator (query NOT EXISTS memeriksa kelulusan prasyarat nilai >= C / bobot >= 2.0 di semester sebelumnya)
   - ConflictValidator (cek irisan interval waktu [start, end) pada JadwalKuliah aktif)
   - DuplicateValidator (cegah pengambilan MK ganda)
3. Mahasiswa submit KRS (DRAFT -> SUBMITTED, tolak HTTP 400 jika KRS kosong).
4. Dosen PA melakukan approve/revise (validasi kepemilikan Dosen PA: 409 jika belum ada PA, 403 jika bukan PA mahasiswa tersebut, 200 OK jika valid dalam satu transaksi atomic).
```

### Prompt 6 — Sequence Diagram Presensi QR Code Dinamis (JWT HS256 & Replay Prevention)
```text
Buat Sequence Diagram untuk skenario Modul Presensi QR Code (Minggu 12):
1. Dosen pengampu meminta pembuatan QR Code (GET /attendance/qr/{schedule_id}) -> sistem memverifikasi kepemilikan jadwal, membuka AttendanceSession, menandatangani token JWT HS256 (berlaku 15 menit dengan klaim jti unik), dan mengembalikan gambar PNG.
2. Mahasiswa memindai QR (POST /attendance/scan) -> sistem memeriksa persistent rate limit (maks 5x/60 detik), anti-spoofing NIM, signature & expiration JWT, pendaftaran mahasiswa pada KRS APPROVED, serta menghitung status HADIR (<=15 menit sejak jam_mulai), TERLAMBAT (15-30 menit), atau DITOLAK (>30 menit).
```

### Prompt 7 — Sinkronisasi Desain UML dengan Skema Database & Implementasi FastAPI
```text
Verifikasi konsistensi antara Class Diagram dan Sequence Diagram dengan kode implementasi aktual SQLAlchemy 2.0 dan FastAPI (Minggu 3-12):
Pastikan seluruh nama atribut, tipe data, metode layanan, kode status HTTP (200, 201, 400, 401, 403, 404, 409, 429), serta constraint database (UniqueConstraint, CheckConstraint, ForeignKey) pada diagram UML sama persis dengan kode sumber di direktori app/.
```

---

## 2. Perbandingan Hasil AI Awal (*Before Revision*) vs Revisi Manual (*After Revision*)

| No | Aspek Desain UML | Hasil Awal AI (*Before Revision*) | Hasil Revisi Manual & Arsitektur (*After Revision*) | Alasan Teknis Mengapa Revisi Diperlukan |
|---:|---|---|---|---|
| 1 | **Pencegahan *God Object* (Prinsip SRP & OCP)** | AI menggabungkan seluruh fungsi akademik (`register_pmb`, `add_krs`, `check_sks`, `check_prereq`, `check_conflict`, `input_grade`, `pay_spp`) ke dalam satu class raksasa `AcademicSystem` dengan 24+ method. | Dipecah menjadi layanan modular per domain (`PMBService`, `KRSManager`, `SchedulingService`, `GradeService`, `GPACalculator`, `BillingService`, `PaymentService`, `AttendanceService`) dan rantai objek `Validator` terpisah. | Mematuhi **Single Responsibility Principle (SRP)** dan **Open/Closed Principle (OCP)**: penambahan aturan validasi baru cukup menambah subclass `Validator` tanpa memodifikasi `KRSManager`. |
| 2 | **Ketepatan Relasi *Composition* (`*--`) vs *Aggregation* (`o--`)** | AI menggunakan panah asosiasi biasa (`-->`) untuk semua relasi antarkelas tanpa membedakan siklus hidup objek (*lifecycle dependency*). | - **Composition (`*--`):** `KRS *-- KRSDetail`, `KRS *-- KrsTransition`, `AttendanceSession *-- AttendanceQRToken`, `Grade *-- GradeHistory` (anak dihapus jika induk dihapus).<br>- **Aggregation (`o--`):** `ProgramStudi o-- CalonMahasiswa`, `Ruangan o-- JadwalKuliah`, `Dosen o-- Mahasiswa`. | Memperjelas semantik *ownership* di level OOP dan menyelaraskannya dengan konfigurasi `cascade="all, delete-orphan"` pada SQLAlchemy ORM. |
| 3 | **Hierarki & Transisi Status `CalonMahasiswa` ke `Mahasiswa`** | AI memisahkan tabel `CalonMahasiswa` dan `Mahasiswa` tanpa relasi, sehingga data pendaftar harus disalin manual saat lulus seleksi. | `Mahasiswa` dirancang sebagai spesialisasi dari `CalonMahasiswa` yang telah berstatus `approved` dan memiliki `nim` unik (hasil generator `NimSequence`) serta `dosen_pa_id`. | Menghindari duplikasi data profil dan menjamin sifat *idempotent* pada saat `PUT /api/pmb/approve/{id}` dipanggil berulang. |
| 4 | **Kelengkapan *Alternate Flow* pada Sequence Diagram** | AI hanya menggambar *Happy Path* (semua request dianggap valid dan langsung `200 OK`). | Ditambahkan blok `alt / else` lengkap untuk seluruh *error handling*: Email duplikat (`409`), Telepon invalid (`400`), Tunggakan SPP (`403`), SKS `> 24` (`400`), Prasyarat `< C` (`400`), Bukan Dosen PA (`403`), dan QR Expired (`400`). | Sequence diagram tanpa *alternate flow* tidak dapat dijadikan acuan pengujian *edge cases* dan kontrak HTTP status code pada REST API. |
| 5 | **Konsistensi Aturan Nilai `D` (Lulus) vs `C` (Prasyarat)** | AI menyamakan batas kelulusan mata kuliah dan batas kelulusan prasyarat pada nilai `C (2.0)`. | `GPACalculator.MINIMUM_LULUS = 1.0` (nilai `D` dihitung lulus pada IPK/Transkrip), sedangkan `PrerequisiteValidator.MIN_PREREQ_BOBOT = 2.0` (prasyarat wajib minimal `C`). | Menyelaraskan desain class diagram dengan aturan akademik nyata di mana nilai `D` lulus mata kuliah tetapi belum cukup menjadi prasyarat mata kuliah lanjutan. |

---

## 3. Dokumentasi Siklus OPAR (Observation, Problem, Action, Result)

1. **Observation:** Output diagram pertama dari AI cenderung bersifat monolitik (*God Class*), tidak mencantumkan *visibility modifier* (`+`, `-`, `#`), dan mengabaikan skenario kegagalan validasi pada Sequence Diagram.
2. **Problem:** Desain monolitik melanggar prinsip SOLID dan menyulitkan pengujian unit (*unit testing*) secara terisolasi, sedangkan ketiadaan *alternate flow* membuat pengembang harus menebak kode status HTTP saat validasi gagal.
3. **Action:** Melakukan 4 iterasi prompt terarah untuk menerapkan pola *Chain of Responsibility* pada validasi KRS, *State Machine* pada alur status KRS, *Observer Pattern* pada notifikasi perubahan jadwal, serta menambahkan blok `alt/else` untuk setiap kondisi error.
4. **Result:** Dihasilkan 3 paket diagram UML (Class Diagram, Use Case Diagram, dan Sequence Diagram) yang 100% sinkron dengan implementasi aktual SIAKAD Minggu 3–12 yang telah terbukti lulus **365 automated tests (97% code coverage)**.
