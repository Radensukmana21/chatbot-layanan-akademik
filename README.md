# Chatbot Layanan Akademik

Penyempurnaan chatbot layanan akademik SMPN 1 Dayeuhkolot berbasis **FastAPI,
Natural Language Processing, dan MySQL**. Repository ini disusun ulang secara
bersih dari hasil prototipe tugas akhir agar setiap fungsi dapat diuji, dipelihara,
dan dikembangkan menuju pilot sekolah.

> Status saat ini: **fondasi pengembangan**. Repository belum dinyatakan siap
> produksi dan belum boleh digunakan untuk persetujuan surat secara operasional.

## Tujuan

Sistem diarahkan untuk mendukung lima layanan utama:

1. Melihat jadwal pelajaran.
2. Melihat informasi guru.
3. Melihat informasi ekstrakurikuler.
4. Mengajukan surat izin.
5. Mengecek status surat izin.

Tiga domain yang pernah terdapat pada dataset lama—jadwal ujian, jadwal kegiatan,
dan informasi prestasi—dicatat sebagai backlog sampai lima layanan utama stabil.

## Keputusan teknis awal

- Backend: FastAPI dan Python.
- Database: MySQL melalui Laragon.
- NLP: baseline Naive Bayes, Linear SVM, lalu hybrid hanya jika hasil uji mendukung.
- Frontend: widget JavaScript akan ditambahkan setelah kontrak API stabil.
- Docker: tidak menjadi syarat proyek utama.
- Auto-retrain: tidak boleh mempromosikan model tanpa review manusia.
- Persetujuan surat: wajib dilakukan pengguna yang berwenang, bukan chatbot.

## Struktur repository

```text
chatbot-layanan-akademik/
├── app/                    # aplikasi FastAPI
├── artifacts/models/       # model terlatih lokal, tidak di-commit
├── database/               # dokumentasi skema, migration, dan seed
├── dataset/                # raw, reviewed, dan split dataset
├── docs/                   # scope, katalog intent, dan rencana kerja
├── scripts/                # setup, run, test, pemeriksaan environment
├── tests/                  # automated tests
├── .env.example
├── requirements.txt
└── README.md
```

## Persiapan Windows dan Laragon

1. Jalankan **MySQL** dari Laragon.
2. Pastikan Python 3.11 atau lebih baru tersedia.
3. Buka PowerShell pada folder repository.
4. Jalankan:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
Copy-Item .env.example .env
```

5. Sesuaikan nama database dan kredensial pada `.env`.
6. Jalankan API:

```powershell
.\scripts\run.ps1
```

API akan tersedia pada:

```text
http://127.0.0.1:9000
http://127.0.0.1:9000/docs
```

## Endpoint awal

```text
GET /health
GET /readiness
```

`/health` memastikan proses API hidup. `/readiness` memeriksa apakah konfigurasi
dua database sudah tersedia dan dapat dihubungi tanpa menampilkan password.

## Menjalankan test

```powershell
.\scripts\test.ps1
```

atau:

```powershell
pytest
```

## Pekerjaan pertama

Jangan langsung melatih ulang model. Urutan awal:

1. Tinjau `docs/PRODUCT_SCOPE.md`.
2. Tinjau dan lengkapi `docs/intent_catalog.csv`.
3. Jalankan kasus pada `docs/baseline_test_cases.csv` terhadap prototipe lama.
4. Catat akar masalah: model, rule, database, alur percakapan, atau frontend.
5. Bentuk gold test set sebelum menambah data training.
6. Audit dataset lama menggunakan status KEEP, RELABEL, atau DROP.
7. Kumpulkan data alami baru berdasarkan skenario.

Panduan lengkap tersedia pada `docs/DATA_COLLECTION_GUIDE.md`.

## Membuat repository GitHub

```powershell
git init -b main
git add .
git commit -m "chore: initialize academic chatbot foundation"
git remote add origin <URL_REPOSITORY_GITHUB>
git push -u origin main
```

Nama repository yang disarankan: **`chatbot-layanan-akademik`**.
