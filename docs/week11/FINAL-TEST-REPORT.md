## HASIL PENGUJIAN FINAL MINGGU 11

Pengujian akhir dilakukan menggunakan Pytest dan Pytest-Cov setelah seluruh modul Billing Management, Payment Management, dan router PMB diperbarui.

### Perintah pengujian

```powershell
pytest -q
```

### Perintah pengukuran code coverage

```powershell
pytest --cov=app --cov-report=term-missing --cov-report=html
```

### Hasil pengujian akhir

| Komponen | Hasil |
|---|---:|
| Total test | 304 |
| Test passed | 304 |
| Test failed | 0 |
| Total statements | 1.598 |
| Missed statements | 0 |
| Code coverage | 100% |
| Waktu pengujian | 19,77 detik |

### Coverage Modul Keuangan

| Modul | Coverage |
|---|---:|
| Billing Service | 100% |
| Payment Service | 100% |
| Billing Router | 100% |
| Payment Router | 100% |
| Finance Schema | 100% |
| Finance Models | 100% |

### Kesimpulan

Berdasarkan hasil pengujian otomatis terakhir, seluruh 304 test berhasil dijalankan tanpa kegagalan. Seluruh 1.598 statement yang dihitung oleh Coverage berhasil dieksekusi, dengan 0 missed statements dan code coverage keseluruhan sebesar 100%.

Laporan HTML berhasil dibuat pada direktori `htmlcov/`.

Hasil ini menunjukkan bahwa seluruh statement aplikasi yang termasuk dalam pengukuran coverage telah tercakup dalam rangkaian pengujian. Pengujian otomatis ini tidak dengan sendirinya menjamin seluruh kemungkinan kesalahan runtime, keamanan, atau integrasi eksternal telah tertangani.