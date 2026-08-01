# Panduan Pengumpulan Data

## Urutan yang benar

1. Selesaikan definisi intent.
2. Buat gold test set.
3. Audit dataset lama.
4. Kumpulkan data baru.
5. Review dan label data.
6. Baru lakukan training.

## Metode pengumpulan

Jangan meminta responden membuat variasi berdasarkan nama intent. Berikan skenario
nyata agar bahasa yang terkumpul alami.

Contoh skenario:

- Anda ingin mengetahui pelajaran kelas 8A besok.
- Anda ingin mengetahui siapa wali kelas 7B.
- Anda ingin mengetahui jadwal ekstrakurikuler basket.
- Anda ingin mengajukan izin tidak masuk karena sakit.
- Anda ingin memeriksa pengajuan surat yang pernah dibuat.
- Anda menanyakan sesuatu yang tidak berhubungan dengan sekolah.

## Target awal pengumpulan

Target ini digunakan untuk memulai audit, bukan jaminan bahwa model sudah cukup:

- 50 pertanyaan unik per intent informasi utama.
- 75 pertanyaan untuk pengajuan surat.
- 75 pertanyaan untuk cek status surat.
- 100 pertanyaan di luar domain.
- 30 pertanyaan ambigu.
- 30 pertanyaan yang mengandung typo atau singkatan.

Jumlah akhir ditentukan dari learning curve dan error analysis.

## Data yang dilarang masuk GitHub

- Nama siswa asli.
- NIS/NISN.
- Nomor telepon asli.
- Alamat.
- Alasan kesehatan yang dapat mengidentifikasi individu.
- Password, token, dan credential database.

## Format raw collection

Kolom minimum:

```text
response_id
scenario_id
user_role
utterance
collected_at
consent
notes
```

Label intent belum harus ditentukan oleh responden. Label diberikan reviewer.

## Review

Setiap data diberi salah satu keputusan:

- KEEP: alami dan labelnya jelas.
- RELABEL: kalimat berguna, tetapi label lama salah.
- DROP: duplikat, tidak alami, terlalu ambigu, atau mengandung data pribadi.

Idealnya data penting ditinjau dua orang. Perbedaan label diselesaikan melalui
pedoman intent, bukan tebakan.
