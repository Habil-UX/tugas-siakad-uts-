# ADR-010: Observer Pattern untuk Notifikasi Perubahan Jadwal

## Status
Diterapkan & Dikonsolidasikan (menggabungkan catatan dari draft `ADR-011-Observer-Pattern.md`).

## Konteks
Perubahan jadwal harus segera diberitahukan kepada pihak yang terdampak, yaitu mahasiswa, dosen, dan admin akademik, tanpa membuat *service* utama (`SchedulingService`) bergantung langsung pada logika maupun kanal pengiriman pesan setiap penerima.

## Keputusan
Menggunakan **Observer Pattern** dengan komponen berikut:
- `ScheduleSubject` bertindak sebagai *Publisher / Subject*.
- `StudentObserver` bertindak sebagai *Subscriber* untuk mahasiswa terdampak.
- `LecturerObserver` bertindak sebagai *Subscriber* untuk dosen pengampu.
- `AdminObserver` bertindak sebagai *Subscriber* untuk admin akademik.
- `NotificationManager` mengelola pencatatan dan pengiriman notifikasi setelah transaksi database berhasil.

Pada implementasi ini, notifikasi dicatat secara persisten ke tabel database `notification_log` dan disimulasikan melalui log aplikasi.

## Konsekuensi
- **Loose Coupling:** Publisher (`SchedulingService` / `ScheduleSubject`) tidak perlu mengetahui detail internal setiap observer.
- **Extensibility:** Jika di masa depan ingin menambahkan kanal notifikasi baru (seperti WhatsApp, Email, SMS, atau Push Notification), cukup membuat class Observer baru tanpa mengubah kode `SchedulingService`.
- **Auditability:** Setiap notifikasi perubahan jadwal tercatat di tabel `notification_log` beserta tipe penerima dan pesan.
- Pengiriman eksternal nyata (WhatsApp/Email/SMS/Push) memerlukan integrasi provider pihak ketiga secara terpisah; log simulasi dan tabel database berfungsi sebagai bukti pemicuan internal.

## Riwayat Keputusan
- **Versi Awal (`ADR-010`):** Spesifikasi lengkap Observer Pattern untuk notifikasi perubahan jadwal.
- **Konsolidasi (`ADR-011-Observer-Pattern.md` $\rightarrow$ `ADR-010`):** Menggabungkan poin *loose coupling* dan contoh ekstensi kanal WhatsApp dari `ADR-011-Observer-Pattern.md` ke dalam dokumen utama ini sekaligus menghilangkan duplikasi nomor dengan `ADR-011-Strategi-Deteksi-Konflik.md`.
