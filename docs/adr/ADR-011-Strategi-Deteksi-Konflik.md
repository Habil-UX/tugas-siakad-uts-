
# ADR-011: Strategi Deteksi Konflik Jadwal

## Status
Diterapkan.

## Konteks
Sistem perlu mencegah penggunaan waktu, ruangan, atau dosen yang saling bertabrakan.

Jadwal yang berakhir tepat ketika jadwal berikutnya dimulai tetap diperbolehkan.

## Keputusan
Menggunakan interval waktu setengah terbuka `[start, end)`.

Dua interval beririsan apabila:

`existing_start < new_end AND new_start < existing_end`

Pemeriksaan dilakukan pada hari yang sama dan dikombinasikan dengan identitas ruangan serta dosen untuk menentukan jenis konflik.

## Konsekuensi
- Jadwal 08.00–10.00 dan 10.00–12.00 tidak dianggap bentrok.
- Konflik waktu, ruangan, dan dosen dapat dijelaskan secara terpisah kepada pemanggil layanan.
- Pengujian perlu mencakup interval tumpang tindih, interval berurutan, hari berbeda, ruangan sama, dan dosen sama.
