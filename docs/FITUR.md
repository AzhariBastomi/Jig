# Jig — Daftar Fitur

## UI & Layout

- **Debug windows grid 2 kolom** — saat debug console dibuka, window ditile otomatis dalam grid 2 kolom agar semua terlihat rapi (tidak menumpuk)
- **Dialog auto-close** — AddTest, Display Settings, Flash Settings, OTA Settings otomatis tutup saat user klik di luar area dialog (menggunakan `bind_all` + cek koordinat, bukan FocusOut)

---

## Add Test Dialog

- **Multi-project flash** — menampilkan satu baris per flash project (TM81, BEXA, dll.) yang terdaftar di `flash.json`
- **Label dari JSON** — nama module derive dari field `label` di JSON (`tm81_test.json`, `tm81_ota.json`), fallback ke nama file
- **Auto-close setelah Add** — setelah klik "+ Add", dialog langsung menutup

---

## Flash

- **Multi-project** — config di `flash.json` mendukung beberapa project (tm81, bexa) dengan region masing-masing
- **Format module** `flash:proj:region` — contoh: `flash:tm81:boot`, `flash:bexa:app`
- **Region opsional** — region dengan `"optional": true` hanya muncul di list jika field `file` sudah diisi (contoh: SN di BEXA)
- **Flash Settings per project** — dialog hanya menampilkan field `file` per region sesuai project yang aktif
- **Browse ingat direktori** — Browse di Flash Settings langsung buka ke folder file yang sebelumnya dipilih
- **Reload setelah save** — setelah simpan Flash Settings, item flash di test list di-reload otomatis

---

## OTA (TM81 OTA)

- **Rename dari tm81_flash → tm81_ota** — nama JSON, prefix module, dan label semua diupdate
- **Fixed params di commissioning.json** — `connection`, `chunk_size`, `fill_with_ff`, `bl_boot_wait_s` dipindah ke `commissioning.json["ota"]`; tidak perlu diatur user
- **OTA Settings simpel** — dialog hanya berisi satu field: file firmware (`fw_version`)
- **Browse dengan suppress auto-close** — saat filedialog terbuka, auto-close dinonaktifkan sementara

---

## Serial & Koneksi

- **Auto-reconnect** — saat startup, jika ada port yang belum terhubung, retry otomatis setiap 5 detik
- **Skip port yang sudah connected** — retry hanya untuk port yang belum berhasil

---

## Keepalive

- **Hanya untuk project TM81** — keepalive hanya distart saat project yang dipilih adalah `tm81`, tidak untuk project lain

---

## Clear / Reset

- **Clear per project** — tombol Clear mereset config JSON yang terkait dengan add test yang aktif (file flash, fw_version OTA, dll.), bukan semua config

---

## Config

- **`flash.json` multi-project** — struktur `projects[proj_name][regions]` menggantikan flat list region sebelumnya
- **`commissioning.json`** — ditambah section `ota` untuk fixed params OTA
- **Label dari JSON** — semua label test module dibaca dari field `label` di masing-masing JSON config

---

## Tasks / Persistensi

- **Migration guard** — `tasks.json` dengan format lama (`flash:boot`, `tm81_flash:`) dideteksi dan dilewati dengan warning agar tidak crash

---

*Terakhir diupdate: 2026-07-23*
