# Expense Ledger CLI

Pencatat pengeluaran lokal untuk satu mata uang. Catat tanggal, kategori, jumlah dan anggaran bulanan; tampilkan ringkasan serta ekspor/impor CSV. Python 3.10+ dan standard library.

```console
python ledger.py --db catatan.db add --date 2026-10-27 --category Makan --amount 12.345
python ledger.py --db catatan.db budget --month 2026-10 --amount 100
python ledger.py --db catatan.db summary --month 2026-10
python ledger.py --db catatan.db export pengeluaran.csv
python ledger.py --db salinan.db import pengeluaran.csv
python -m unittest -v
```

Jumlah dihitung dengan `Decimal`, dibulatkan ke dua desimal dengan ROUND_HALF_UP dan disimpan sebagai integer satuan terkecil. Contoh `12.345` menjadi `12.35`. Nilai nol, negatif, non-finite dan angka terlalu besar ditolak; sisa anggaran boleh negatif. Tanggal memakai YYYY-MM-DD, bulan YYYY-MM. Tidak ada konversi mata uang. Simpan data pribadi secara lokal dan jangan mengunggah database/CSV.

CSV memakai header `day,category,amount`, maksimum 10000 baris impor, dan seluruh impor divalidasi sebelum transaksi. Ekspor membuat file baru tanpa menimpa; kategori yang dimulai karakter formula diberi awalan apostrof untuk mengurangi risiko formula spreadsheet. Format impor menghapus awalan apostrof tersebut, jadi gunakan CSV ekspor program atau sesuaikan formatnya. Ekspor tidak atomik apabila proses terhenti. Impor ulang menambahkan baris lagi; tidak ada deduplikasi. Anggaran tidak disertakan dalam CSV.

Database asing atau schema berbeda ditolak. Pemeriksaan path bukan sandbox untuk hardlink/race filesystem; gunakan direktori tepercaya. Tidak ada enkripsi, sinkronisasi, kategori terpisah, edit/hapus transaksi, atau dukungan multi-mata uang. Backup data secara terpisah.

Owner/maintainer: Muhammad Zidane Naufal Azzam (ZidaneNaufal1). Implementasi, tes dan dokumentasi dibantu Ciel/OpenAI Codex. Tidak ada klaim nasihat keuangan, pengguna eksternal atau pemahaman manual yang telah diverifikasi. Lisensi MIT.

## English summary

A local single-currency expense ledger with Decimal half-up rounding, SQLite, monthly budgets and CSV round-trip. Imports append entries, exports never overwrite, and budgets are not exported. Developed with Ciel/OpenAI Codex assistance.
