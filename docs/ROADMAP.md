# Roadmap

## Foundation

- Membuat repository bersih.
- Menyamakan port API pada 9000.
- Menyiapkan konfigurasi dua database.
- Menambahkan health check dan automated test.
- Menonaktifkan auto-retrain secara default.

## Requirements and Baseline

- Menyetujui product scope.
- Menyelesaikan katalog intent.
- Menjalankan baseline test terhadap prototipe.
- Mengelompokkan akar masalah.
- Menetapkan kontrak response API.

## Dataset

- Membuat gold test set lebih dahulu.
- Mengaudit dataset lama: KEEP, RELABEL, DROP.
- Mengumpulkan pertanyaan alami berdasarkan skenario.
- Menghilangkan data pribadi.
- Memisahkan train, validation, dan test berdasarkan sumber.

## Model

- Membuat preprocessing yang dapat diuji.
- Melatih Naive Bayes.
- Melatih Linear SVM.
- Membandingkan keduanya dengan hybrid.
- Menetapkan threshold fallback dan clarification.
- Menyimpan metadata, dataset hash, dan laporan evaluasi.

## Information Services

- Menyelesaikan jadwal pelajaran.
- Menyelesaikan informasi guru.
- Menyelesaikan ekstrakurikuler.
- Menambahkan validasi data dan response formatter.
- Menambahkan integration test.

## Letter Workflow

- Validasi SOP bersama sekolah.
- Mendesain role dan permission.
- Membuat nomor pengajuan dan kode verifikasi.
- Membuat dashboard petugas.
- Membuat approval dan audit trail.
- Menguji akses data pribadi.

## Pilot and Handover

- Melakukan UAT terbatas.
- Memperbaiki bug kritis dan tinggi.
- Menyusun backup dan restore.
- Menyusun panduan operator.
- Melakukan sosialisasi.
- Menentukan jadwal evaluasi setelah pilot.
