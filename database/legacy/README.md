# Legacy SQL

Letakkan dump lama secara lokal dengan nama:

```text
database/legacy/databasesekolah.sql
```

Dump ini tidak boleh di-commit karena memuat tabel `surat_izin` dengan data
pribadi. Importer hanya membaca:

- `classrooms`
- `teachers`
- `subjects`
- `schedules`

Importer sengaja tidak membaca `surat_izin`, `chatbot_logs`, atau data transaksi
lain.

Snapshot yang telah diperiksa memuat:

- 32 kelas
- 50 guru
- 19 subjek/kegiatan
- 975 jadwal

Komentar internal SQL menyebut perkiraan 825 jadwal, tetapi jumlah tuple aktual
pada `INSERT INTO schedules` adalah 975.
