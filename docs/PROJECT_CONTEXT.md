\# Konteks Penelitian dan Pengembangan



\## Identitas Penelitian



Judul:



Perancangan Chatbot Layanan Akademik Berbasis NLP Menggunakan

Hybrid Intent Classifier pada SMPN 1 Dayeuhkolot.



\## Tujuan Sistem



Membangun chatbot layanan akademik berbasis FastAPI yang dapat

memberikan informasi akademik dan menangani layanan administrasi

sekolah melalui percakapan pengguna.



\## Lima Layanan Utama



1\. Jadwal pelajaran

2\. Informasi guru

3\. Informasi ekstrakurikuler

4\. Pengajuan surat izin

5\. Pemeriksaan status surat



\## Teknologi



\- Python 3.12

\- FastAPI

\- SQLAlchemy 2

\- Alembic

\- MySQL

\- PyMySQL

\- Pydantic

\- Pytest

\- JavaScript widget

\- TF-IDF

\- Support Vector Machine

\- Naive Bayes



\## Arsitektur Database



\### academic\_school



Menyimpan data akademik:



\- academic\_years

\- school\_classes

\- teachers

\- subjects

\- lesson\_schedules

\- extracurriculars

\- extracurricular\_schedules



\### academic\_chatbot



Menyimpan data percakapan:



\- conversations

\- conversation\_messages



\## NLP dan Intent



Dataset legacy memiliki 978 data.



Intent utama:



\- jadwal\_pelajaran

\- informasi\_guru

\- informasi\_ekstrakurikuler

\- ajukan\_surat\_izin

\- cek\_status\_surat



Intent surat legacy `layanan\_surat` dipisahkan menjadi:



\- ajukan\_surat\_izin

\- cek\_status\_surat



Pendekatan sistem:



\- Rule-based extraction untuk entity terstruktur

\- Hybrid intent classifier menggunakan SVM dan Naive Bayes

\- TF-IDF untuk representasi teks

\- Conversation engine untuk percakapan multi-turn



\## Data Akademik yang Sudah Diimpor



Tahun ajaran:



\- 2025/2026



Data:



\- 32 kelas

\- 50 guru

\- 19 mata pelajaran atau aktivitas

\- 975 jadwal pelajaran

\- 8 ekstrakurikuler

\- 8 jadwal ekstrakurikuler



Kelas:



\- 7A sampai 7K

\- 8A sampai 8K

\- 9A sampai 9J



\## Fitur yang Sudah Selesai



\### Infrastruktur



\- FastAPI application

\- Konfigurasi `.env`

\- Database akademik dan chatbot terpisah

\- Health endpoint

\- Readiness endpoint

\- Alembic akademik

\- Alembic chatbot



\### Jadwal Pelajaran



Endpoint:



\- `GET /api/v1/classes/{class\_name}/schedules/{day}`



Chat mendukung:



\- Jadwal kelas 7A hari Senin

\- Jadwal

\- 7

\- A

\- Senin



Entity:



\- class\_name

\- grade

\- class group

\- explicit day

\- relative day



\### Conversation



\- Context disimpan berdasarkan `conversation\_id`

\- Conversation memiliki TTL 30 menit

\- Pesan pengguna dan assistant disimpan

\- Retention pesan dapat dikonfigurasi

\- Redaksi data sensitif tersedia

\- Cleanup pesan kedaluwarsa tersedia



\### Informasi Guru



Endpoint:



\- `GET /api/v1/teachers/search?q=...\&by=name`

\- `GET /api/v1/teachers/search?q=...\&by=subject`



Chat dasar mendukung:



\- Bu Ane mengajar apa?

\- Siapa guru Matematika?



Pengembangan lanjutan ditunda:



\- Guru yang mengajar kelas 7

\- Guru yang mengajar kelas 7A

\- Guru mata pelajaran tertentu pada kelas tertentu

\- Jadwal mengajar seorang guru



\### Informasi Ekstrakurikuler



Model:



\- Extracurricular

\- ExtracurricularSchedule



Data legacy:



\- Pramuka

\- Futsal

\- PMR

\- Paskibra

\- Basket

\- Tari

\- Paduan Suara

\- Karate



Importer ekstrakurikuler bersifat idempotent.



Endpoint yang sedang dibangun:



\- `GET /api/v1/extracurriculars`

\- `GET /api/v1/extracurriculars/search?q=Pramuka`



\## Prinsip Privasi



Informasi guru yang boleh ditampilkan:



\- Nama

\- Mata pelajaran

\- Kelas yang diajar

\- Informasi akademik terkait



Informasi yang tidak ditampilkan:



\- Nomor telepon

\- Alamat

\- Data pribadi lain



Pesan dapat memiliki kebijakan penyimpanan:



\- full

\- redacted

\- metadata\_only



\## Aturan Pengembangan



\- Gunakan tahun ajaran aktif.

\- Hanya gunakan data dengan `is\_active = true`.

\- Importer harus idempotent.

\- Data SQL legacy tidak dimasukkan ke Git.

\- Setiap fitur harus memiliki automated test.

\- Jalankan seluruh test sebelum commit.

\- Jangan memperluas fitur lanjutan sebelum lima layanan utama selesai.

\- Tidak menggunakan Docker.

\- Lingkungan utama adalah Windows 11 dan Laragon.



\## Catatan Windows



Application Control memblokir executable Alembic langsung.



Gunakan:



```powershell

python -m alembic upgrade head

python -m alembic revision --autogenerate -m "message"

