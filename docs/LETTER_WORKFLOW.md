# Rancangan Alur Surat

Dokumen ini adalah rancangan awal. Status, role, dan urutan approval harus
divalidasi melalui diskusi dengan sekolah.

## Batas kewenangan chatbot

Chatbot boleh:

- membantu mengisi pengajuan;
- memvalidasi kelengkapan format;
- membuat nomor pengajuan;
- menampilkan status yang diizinkan;
- mengirim notifikasi.

Chatbot tidak boleh:

- menyetujui atau menolak surat;
- menandatangani surat;
- mengubah status atas nama guru;
- membuka data pemohon lain.

## Status usulan

```text
DRAFT
SUBMITTED
UNDER_REVIEW
NEEDS_REVISION
WAITING_APPROVAL
APPROVED
REJECTED
COMPLETED
CANCELLED
```

## Alur usulan

```text
Pemohon mengisi data
        ↓
SUBMITTED
        ↓
Tata Usaha memeriksa kelengkapan
        ↓
UNDER_REVIEW
        ├── NEEDS_REVISION
        └── WAITING_APPROVAL
                ├── APPROVED
                └── REJECTED
                        ↓
                    COMPLETED
```

## Audit trail wajib

Setiap perubahan status menyimpan:

- ID pengajuan;
- status sebelumnya;
- status baru;
- pengguna yang mengubah;
- role pengguna;
- catatan;
- waktu perubahan.

## Pertanyaan untuk sosialisasi sekolah

1. Jenis surat apa saja yang dilayani?
2. Siapa yang memverifikasi setiap jenis surat?
3. Siapa yang berwenang menyetujui?
4. Apakah wali kelas selalu terlibat?
5. Apakah kepala sekolah terlibat pada jenis tertentu?
6. Bukti atau lampiran apa yang diperlukan?
7. Berapa target waktu pelayanan?
8. Siapa yang boleh membaca alasan izin?
9. Berapa lama data disimpan?
10. Apakah hasil akhirnya berupa surat digital atau status proses saja?
