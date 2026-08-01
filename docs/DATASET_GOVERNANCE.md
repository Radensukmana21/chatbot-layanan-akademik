# Dataset Governance

## Pemisahan data

```text
dataset/
├── raw/         # hasil pengumpulan; tidak di-commit
├── reviewed/    # sudah dianonimkan dan dilabeli; tidak di-commit
└── splits/
    ├── train/
    ├── validation/
    └── test/
```

## Gold test set

Gold test set dibuat sebelum training ulang dan tidak boleh digunakan untuk:

- training;
- pemilihan contoh tambahan;
- penyetelan preprocessing;
- penentuan aturan berbasis kata.

Setiap perubahan gold test set harus dicatat.

## Pencegahan leakage

Kalimat dari responden atau template yang sama tidak boleh tersebar ke train dan
test. Variasi dekat seperti:

- "jadwal 8a hari senin"
- "jadwal kelas 8a senin"
- "senin kelas 8a jadwalnya apa"

harus diperlakukan sebagai satu kelompok ketika melakukan split.

## Metadata model

Setiap model terlatih wajib mempunyai:

- tanggal training;
- hash dataset;
- daftar label;
- versi preprocessing;
- parameter model;
- hasil accuracy, macro precision, macro recall, macro F1;
- F1 per intent;
- confusion matrix;
- threshold fallback;
- catatan error analysis.

## Retraining

Interaksi confidence rendah hanya menjadi kandidat review. Label prediksi chatbot
tidak boleh langsung dianggap sebagai label benar.
