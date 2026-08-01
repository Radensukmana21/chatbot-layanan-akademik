\# Intent: jadwal\_pelajaran



\## Tujuan



Melayani pertanyaan pengguna mengenai jadwal pelajaran berdasarkan kelas

dan hari tertentu.



\## Jenis layanan



Informasi akademik bersifat read-only.



Chatbot hanya membaca data dari database dan tidak boleh membuat,

mengubah, atau menghapus jadwal.



\## Intent ID



jadwal\_pelajaran



\## Entitas wajib



\- kelas

\- hari



\## Entitas opsional



\- mata\_pelajaran

\- jam\_ke



\## Contoh pertanyaan yang termasuk



1\. Jadwal kelas 8A hari Senin apa?

2\. Besok kelas 7B belajar apa?

3\. Hari Jumat kelas 9C ada pelajaran apa?

4\. Jadwal matematika kelas 8A kapan?

5\. Pelajaran pertama kelas 7A hari Selasa apa?

6\. Hari Rabu kelas 8B ada olahraga tidak?

7\. Kelas 9A hari Kamis pulang jam berapa?

8\. Tolong tampilkan jadwal kelas 7C hari Senin.

9\. Jadwal belajar 8A hari ini apa?

10\. Senin kelas 9B belajar apa saja?



\## Contoh pertanyaan yang tidak termasuk



1\. Jadwal ujian matematika kapan?

&#x20;  - Intent: jadwal\_ujian



2\. Siapa guru matematika kelas 8A?

&#x20;  - Intent: informasi\_guru



3\. Kegiatan sekolah hari Senin apa?

&#x20;  - Intent: jadwal\_kegiatan



4\. Ekskul basket latihan hari apa?

&#x20;  - Intent: informasi\_ekstrakurikuler



5\. Saya ingin mengajukan surat izin.

&#x20;  - Intent: ajukan\_surat\_izin



6\. Siapa presiden Indonesia?

&#x20;  - Intent: di\_luar\_cakupan



\## Pertanyaan ambigu



\### Contoh 1



Pengguna:



Jadwal matematika kapan?



Respons:



Apakah yang dimaksud jadwal pelajaran matematika atau jadwal ujian

matematika?



\### Contoh 2



Pengguna:



Jadwal kelas 8A.



Respons:



Jadwal kelas 8A untuk hari apa?



\### Contoh 3



Pengguna:



Jadwal hari Senin.



Respons:



Jadwal hari Senin untuk kelas berapa?



\## Aturan klarifikasi



1\. Jika kelas tidak ditemukan, chatbot harus meminta kelas.

2\. Jika hari tidak ditemukan, chatbot harus meminta hari.

3\. Jika kelas dan hari tidak ditemukan, chatbot harus meminta keduanya.

4\. Jika pertanyaan dapat merujuk pada jadwal pelajaran atau jadwal ujian,

&#x20;  chatbot harus meminta klarifikasi.

5\. Chatbot tidak boleh menebak kelas pengguna.

6\. Chatbot tidak boleh menampilkan jadwal kelas lain tanpa permintaan jelas.



\## Format kelas yang diterima



Contoh:



\- 7A

\- 7 A

\- kelas 7A

\- VII A

\- delapan B

\- kelas sembilan C



Format internal harus dinormalisasi menjadi:



\- 7A

\- 7B

\- 8A

\- 8B

\- 9A

\- 9B



Daftar kelas sebenarnya harus mengikuti data resmi sekolah.



\## Format hari yang diterima



\- Senin

\- Selasa

\- Rabu

\- Kamis

\- Jumat

\- Sabtu



Variasi yang dapat dinormalisasi:



\- senen → Senin

\- slasa → Selasa

\- rebo → Rabu

\- kamis → Kamis

\- jumat → Jumat

\- sabtu → Sabtu



\## Hari relatif



Kata berikut dapat dikonversi menggunakan zona waktu Asia/Jakarta:



\- hari ini

\- besok

\- lusa



Jika hasil konversi jatuh pada hari ketika tidak ada jadwal, chatbot harus

menyampaikan bahwa tidak ada jadwal yang tersedia.



\## Sumber data



Database:



academic\_school



Data minimum yang diperlukan:



\- kelas

\- hari

\- jam\_mulai

\- jam\_selesai

\- mata\_pelajaran

\- nama\_guru

\- ruang, jika tersedia



\## Format respons berhasil



Contoh:



Jadwal kelas 8A hari Senin:



1\. 07.00–07.40 — Matematika — Ibu Siti

2\. 07.40–08.20 — Matematika — Ibu Siti

3\. 08.20–09.00 — Bahasa Indonesia — Bapak Dedi



Data terakhir diperbarui: 1 Agustus 2026.



\## Respons data tidak ditemukan



Maaf, jadwal kelas 8A untuk hari Senin belum tersedia. Silakan hubungi

petugas sekolah jika informasi tersebut seharusnya sudah tersedia.



\## Respons kelas tidak valid



Saya belum menemukan kelas "8Z". Silakan masukkan kelas yang terdaftar,

misalnya 7A, 8B, atau 9C.



\## Respons hari tidak valid



Saya belum mengenali nama hari tersebut. Silakan gunakan Senin sampai Sabtu.



\## Larangan



Chatbot tidak boleh:



\- membuat jadwal yang tidak ada di database;

\- menebak nama guru;

\- menampilkan data dari kelas yang berbeda;

\- menganggap jadwal ujian sebagai jadwal pelajaran;

\- menjawab hanya berdasarkan pola dataset tanpa melakukan query database;

\- menampilkan pesan error database kepada pengguna.



\## Penanganan error



Jika database tidak dapat diakses:



Maaf, informasi jadwal sedang tidak dapat diakses. Silakan coba kembali

beberapa saat lagi.



Detail teknis error hanya dicatat di log aplikasi.



\## Expected action



query\_lesson\_schedule



\## Handler



lesson\_schedule\_handler



\## Decision mode



ml\_rule\_db



Alurnya:



1\. Model mengenali intent.

2\. Entity extractor mencari kelas dan hari.

3\. Conversation engine meminta data yang kurang.

4\. Rule dan validation layer memvalidasi entitas.

5\. Repository melakukan query database.

6\. Response builder menyusun jawaban.



\## Kriteria kelulusan



Intent dianggap berfungsi apabila:



1\. Pertanyaan normal dikenali dengan benar.

2\. Kelas dan hari dapat diekstrak.

3\. Data yang kurang menghasilkan pertanyaan klarifikasi.

4\. Pertanyaan jadwal ujian tidak masuk jadwal pelajaran.

5\. Pertanyaan di luar domain tidak dipaksakan ke intent ini.

6\. Jadwal yang ditampilkan sama dengan database.

7\. Data kosong menghasilkan fallback yang jelas.

8\. Gangguan database tidak membocorkan error teknis.

9\. Seluruh test untuk intent ini lulus.

