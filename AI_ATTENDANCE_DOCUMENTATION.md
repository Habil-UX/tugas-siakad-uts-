# DOKUMENTASI AI ATTENDANCE INSIGHTS (`AI_ATTENDANCE_DOCUMENTATION.md`)
**Proyek:** Sistem Informasi Akademik Terintegrasi (SIAKAD) — Minggu 12  
**File Implementasi:** `app/services/ai_attendance_analyzer.py`

---

## 1. Transparansi Metodologi Analisis

Sesuai ketentuan rekayasa perangkat lunak yang jujur dan transparan, `AIAttendanceAnalyzer` menggunakan **mesin analisis statistik dan aturan deterministik lokal (*Deterministic Statistical & Rule-Based Pattern Detection Engine*)** — **bukan** pemanggilan API LLM eksternal berbayar, sehingga:
1. Tidak memerlukan API key berbayar.
2. Hasil perhitungan 100% deterministik, dapat diaudit, dan bebas dari halusinasi data (*zero hallucination*).
3. Setiap *insight* wajib menyertakan bukti kuantitatif (`evidence`) berupa ukuran sampel (`sample_sessions` / `sample_records`), jumlah ketidakhadiran (`absent_count`), dan tingkat ketidakhadiran (`absence_rate`).

---

## 2. Rumus & Aturan Deteksi Pola

1. **Perhitungan Persentase Kehadiran Mahasiswa:**
   $$\text{Attendance Rate (\%)} = \frac{\text{Jumlah Hadir} + \text{Jumlah Terlambat}}{\text{Total Sesi Berlangsung}} \times 100\%$$
   - Sesi yang belum berlangsung atau masih di masa depan **tidak** dimasukkan ke dalam penyebut (`Total Sesi Berlangsung`).
2. **Syarat Minimum Ukuran Sampel (`min_sessions`):**
   - Default `min_sessions = 2`. Pola ketidakhadiran maupun status risiko tidak disimpulkan apabila jumlah sesi yang telah berlangsung masih lebih kecil dari `min_sessions`.
3. **Deteksi Pola Hari (`type = "attendance_pattern"`):**
   - Mengelompokkan riwayat presensi per `(mahasiswa, hari)`.
   - Jika pada hari tertentu `sample_sessions >= min_sessions` dan `absence_rate >= 35.0%`, sistem menghasilkan insight:
     `"Sering tidak hadir pada hari <Hari>"` beserta rekomendasi konseling akademik.
4. **Deteksi Pola Jam Kuliah (`type = "time_slot_pattern"`):**
   - Mengelompokkan riwayat presensi per `(mata_kuliah, jam_mulai)`.
   - Jika pada jam kuliah tertentu (misal `07:00`) `absence_rate >= 30.0%`, sistem menghasilkan insight:
     `"Kelas <MK> di jam <Jam> memiliki tingkat ketidakhadiran tinggi (<X>%)"` beserta rekomendasi evaluasi/reschedule jadwal.
5. **Early Warning Mahasiswa Berisiko (`type = "early_warning"`):**
   - Mengidentifikasi seluruh mahasiswa dengan `attendance_rate < 75.0%` dan merangkum jumlah mahasiswa berisiko yang terancam tidak memenuhi syarat mengikuti ujian akhir (sesuai aturan presensi minimal 75% pada Modul Nilai Minggu 9–10).

---

## 3. Contoh Output JSON Aktual

```json
{
  "methodology": "Deterministic Statistical & Rule-Based Attendance Pattern Analyzer (Local Engine, Tanpa API LLM Eksternal)",
  "calculation_basis": "Persentase Kehadiran = (Hadir + Terlambat) / Total Sesi Berlangsung * 100%",
  "min_sample_sessions": 2,
  "summary": {
    "total_records_analyzed": 8,
    "total_students_analyzed": 2,
    "at_risk_students_count": 1,
    "early_warning": "1 mahasiswa berisiko tidak memenuhi syarat presensi (<75%)"
  },
  "insights": [
    {
      "type": "attendance_pattern",
      "student": "Mahasiswa X",
      "nim": "2026001",
      "pattern": "Sering tidak hadir pada hari Senin",
      "evidence": {
        "day": "Monday",
        "day_id": "Senin",
        "absent_count": 2,
        "sample_sessions": 4,
        "absence_rate": 50.0
      }
    },
    {
      "type": "time_slot_pattern",
      "course": "IF401",
      "pattern": "Kelas IF401 di jam 07:00 memiliki tingkat ketidakhadiran tinggi (37.5%)",
      "evidence": {
        "course": "IF401",
        "time_slot": "07:00",
        "absent_count": 3,
        "sample_records": 8,
        "absence_rate": 37.5
      }
    }
  ],
  "actions": [
    {
      "priority": "high",
      "target": "Mahasiswa X",
      "recommendation": "Mahasiswa Mahasiswa X (2026001) sering tidak hadir pada hari Senin (50.0% dari 4 sesi) -> hubungi mahasiswa untuk konseling akademik"
    },
    {
      "priority": "medium",
      "target": "IF401",
      "recommendation": "Kelas IF401 di jam 07:00 memiliki absen rate 37.5% (3/8 presensi) -> pertimbangkan evaluasi atau reschedule jadwal"
    }
  ]
}
```
