# Audit Awal Prototipe Tugas Akhir

Sumber audit: arsip `chatbot-hybrid-api-main.zip` yang diterima sebelum repository
ini dibuat.

## Komponen yang dapat dipertahankan sebagai referensi

- FastAPI.
- SQLAlchemy dan dua koneksi basis data.
- Hybrid SVM dan Naive Bayes.
- TF-IDF.
- Rule engine untuk jadwal, guru, dan ekstrakurikuler.
- Conversation state untuk surat izin.
- Widget JavaScript.
- Log interaksi dan konsep retraining.

## Dataset lama

Dataset CSV berisi 978 baris:

| Intent | Jumlah |
|---|---:|
| layanan_surat | 389 |
| jadwal_pelajaran | 211 |
| informasi_guru | 105 |
| informasi_prestasi | 95 |
| jadwal_ujian | 69 |
| jadwal_kegiatan | 63 |
| informasi_ekstrakurikuler | 46 |

Temuan awal:

- distribusi kelas tidak seimbang;
- pengajuan dan cek status masih bercampur pada `layanan_surat`;
- beberapa pola kalimat sangat mirip;
- tiga intent dataset belum menjadi bagian lima use case inti;
- belum ada gold test set independen.

## Temuan source

- `scripts/train_model.py` kosong.
- `scripts/retrain_manual.py` kosong.
- test entity extractor masih berupa script cetak dan import-nya tidak sesuai
  package `app`.
- README menjalankan Uvicorn tanpa port, tetapi dokumentasi mengarah ke 9000.
- CORS menggunakan wildcard.
- auto-retrain aktif terjadwal pada prototipe.
- filter out-of-scope menggunakan pencarian substring sederhana.
- pengecekan status surat menggunakan nomor telepon.
- status pengajuan awal hanya `pending`.

## Kebijakan migrasi

Kode lama tidak disalin langsung. Setiap modul dipindahkan hanya setelah:

1. perilakunya didefinisikan;
2. test ditulis;
3. data input dan output ditetapkan;
4. risiko privasi diperiksa;
5. kode lulus test.
