# Project Charter

## Nama proyek

**Chatbot Layanan Akademik**

## Latar belakang

Prototipe tugas akhir telah membuktikan bahwa chatbot dapat menggabungkan
klasifikasi intent, rule-based engine, conversation state, dan basis data akademik.
Penyempurnaan ini berfokus pada reliabilitas fungsi, kualitas data, keamanan proses
administrasi, dan kesiapan pengujian bersama sekolah.

## Definisi selesai

Proyek tidak dianggap selesai hanya karena model menghasilkan prediksi. Proyek
dianggap selesai ketika:

- ruang lingkup layanan telah disepakati;
- setiap intent memiliki definisi dan handler yang jelas;
- model diuji pada data independen;
- pertanyaan ambigu meminta klarifikasi;
- pertanyaan di luar domain tidak dipaksa menjadi intent akademik;
- semua fungsi utama memiliki automated test;
- alur surat memiliki role, approval, dan audit trail;
- data pribadi tidak bocor;
- instalasi dapat diulang dari repository;
- UAT bersama perwakilan sekolah telah dilaksanakan.

## Prinsip

1. Tidak mengarang informasi akademik.
2. Tidak mengambil keputusan administratif.
3. Kegagalan harus aman dan dapat dijelaskan.
4. Dataset harus ditinjau manusia.
5. Model baru tidak dipromosikan otomatis.
6. Fungsi yang stabil lebih penting daripada banyaknya fitur.
7. Semua perubahan penting dicatat melalui Git.
