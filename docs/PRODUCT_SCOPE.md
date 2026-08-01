# Product Scope

## Layanan utama

Cakupan awal mengikuti lima use case inti pada laporan tugas akhir:

| Layanan | Aktor utama | Jenis operasi | Status |
|---|---|---|---|
| Jadwal pelajaran | Siswa | Baca data | Dipertahankan |
| Informasi guru | Siswa | Baca data | Dipertahankan |
| Informasi ekstrakurikuler | Siswa | Baca data | Dipertahankan |
| Pengajuan surat izin | Siswa/orang tua | Membuat transaksi | Dirancang ulang |
| Cek status surat izin | Siswa/orang tua | Baca transaksi terbatas | Dirancang ulang |

## Backlog setelah layanan utama stabil

- Jadwal ujian.
- Jadwal kegiatan.
- Informasi prestasi.

Ketiga domain ini ada pada dataset prototipe, tetapi tidak dimasukkan ke milestone
awal sampai handler, sumber data, dan test-nya tersedia.

## Di luar cakupan awal

- Pengetahuan umum di luar layanan sekolah.
- Jawaban generatif berbasis LLM.
- Interaksi suara.
- Persetujuan surat otomatis oleh chatbot.
- Tanda tangan digital resmi sebelum SOP sekolah disepakati.
- Promosi model otomatis tanpa review.
- Docker sebagai syarat menjalankan proyek.

## Aktor

- Siswa atau orang tua.
- Petugas tata usaha.
- Wali kelas atau guru berwenang.
- Administrator sistem.
- Kepala sekolah hanya jika SOP jenis surat mewajibkannya.
