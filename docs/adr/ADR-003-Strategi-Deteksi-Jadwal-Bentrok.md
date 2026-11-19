# ADR-003: Strategi Deteksi Jadwal Bentrok

## Konteks
Sistem harus mendeteksi jika dua mata kuliah memiliki jadwal yang bertabrakan pada hari dan jam yang sama.

## Keputusan
Menggunakan aturan irisan interval setengah terbuka `[start, end)`.

## Alasan
Dua jadwal dikatakan bentrok jika:
`existing_start < new_end AND new_start < existing_end`
Dan berada di hari yang sama.

Pendekatan ini memastikan bahwa jadwal yang tepat berurutan (misal: MK A selesai jam 10:00, MK B mulai jam 10:00) **tidak** dianggap bentrok.

## Konsekuensi
- Logika ini diterapkan di `ConflictValidator`.
- Memberikan pesan error yang jelas kepada mahasiswa mengenai MK mana yang bentrok.