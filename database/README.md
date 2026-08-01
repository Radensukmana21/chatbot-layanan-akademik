# Database

Repository mempertahankan kompatibilitas awal dengan dua koneksi:

1. `ACADEMIC_DATABASE_URL` untuk data sekolah dan transaksi surat.
2. `CHATBOT_DATABASE_URL` untuk conversation state, log, review queue, dan
   metadata model.

File SQL prototipe lama belum disalin. Skema baru akan dibuat setelah:

- nama tabel dan kolom diaudit;
- data pribadi dipisahkan;
- role dan approval surat disepakati;
- strategi migration ditentukan.

Jangan mengunggah dump database sekolah yang berisi data nyata.
