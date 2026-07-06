# Jig — Optimization TODO

Status saat ini cukup solid untuk production jig. List ini mencatat
area yang perlu diperbaiki sebelum bisa dianggap benar-benar production-ready.

---

## 🔴 HIGH — Potensi bug / race condition

### 1. `lib/serial_comm.py` — `_cb_data` tidak thread-safe
**File:** `lib/serial_comm.py` → class `SerialComm`

`_cb_data` adalah list Python biasa yang di-modify dari dua thread berbeda:
- Main thread: `on_data(fn)` (tambah) dan `_cb_data.remove(fn)` (hapus, di dalam `xfer()`)
- Reader thread: iterasi `_cb_data` di `_on_frame()`

Tanpa lock, ini bisa menyebabkan `RuntimeError: list changed size during iteration`
atau data yang tiba di callback salah.

**Fix:** tambahkan `threading.Lock` di `SerialComm.__init__` dan wrap semua
akses `_cb_data` dengan lock tersebut.

---

### 2. `lib/serial_comm.py` — Double disconnect callback
**File:** `lib/serial_comm.py` → `SerialComm._reader()` dan `SerialComm.disconnect()`

Ketika koneksi putus (port dicabut), `_reader()` keluar dari loop dan
memanggil `_cb_disconnect`. Tapi `disconnect()` juga memanggil `_cb_disconnect`.
Hasilnya callback disconnect dipanggil dua kali.

**Fix:** tambahkan flag `_disconnected` agar callback hanya fired sekali.

---

## 🟡 MEDIUM — Performance / maintainability

### 3. `lib/serial_comm.py` — Reader baca 1 byte per call
**File:** `lib/serial_comm.py` → `SerialComm._reader()`

```python
b = self._port.read(1)  # ← sangat tidak efisien
```

Pada baudrate 115200, ini menghasilkan ribuan syscall per detik, memboroskan
CPU dan bisa miss data jika buffer penuh. Solusi: baca dalam chunk
(`read(self._port.in_waiting or 1)`) lalu feed byte per byte ke parser.

---

### 4. `lib/test_loader.py` — Import modul command setiap kali test run
**File:** `lib/test_loader.py` → `_make_tm81_item()._run_fn()`

```python
def _run_fn():
    mod = importlib.import_module(mod_path)  # ← dipanggil setiap run
    cls = getattr(mod, cls_name)
    ...
```

`importlib` sudah cache module, jadi ini tidak terlalu mahal — tapi
`getattr` dan `rsplit` tetap jalan setiap kali. Lebih bersih kalau
class di-resolve saat `_make_tm81_item()` dipanggil (load time),
bukan saat test dijalankan.

---

### 5. `commands/tm81/*.py` — `sys.path.insert` jalan di module-level
**File:** semua 35 file di `commands/tm81/`

Blok ini ada di top-level setiap file:
```python
import sys as _sys, os as _os
_sys.path.insert(0, ...)
_sys.path.insert(0, ...)
```

Artinya setiap kali file di-import oleh GUI (35 file = 70 kali
`sys.path.insert`), path yang sama ditambahkan berulang-ulang.
Tidak kritis, tapi berantakan.

**Fix:** pindahkan ke dalam `if __name__ == "__main__":` saja.
Ketika dijalankan via GUI, `sys.path` sudah benar dari `main.py`.

---

### 6. `main.py` — Terlalu monolitik (989 baris)
**File:** `main.py`

Satu file berisi: `App`, `TestListPanel`, `DisplaySettingsDialog`,
`AddTestDialog`, `TestController`. Sulit dibaca dan di-maintain.

**Fix yang disarankan:**
```
ui/
  test_list_panel.py   ← TestListPanel
  dialogs.py           ← DisplaySettingsDialog, AddTestDialog
controllers/
  test_controller.py   ← TestController
main.py                ← App saja + entry point
```

---

## 🟢 LOW — Nice to have

### 7. `config.py` — `ROW_HEIGHT` tidak lagi dipakai
**File:** `config.py` baris 29

```python
ROW_HEIGHT = 60  # ← sisa dari layout table lama, bisa dihapus
```

---

### 8. `test_row_widget.py` — `wraplength` status label hardcoded
**File:** `test_row_widget.py` → `_build()`

```python
self._status_lbl = tk.Label(..., wraplength=int(220 * s))
```

Nilai `220` tidak mengikuti lebar widget sebenarnya. Kalau window
di-resize, teks bisa terpotong atau wrap terlalu awal.

**Fix:** bind `<Configure>` pada label atau content frame untuk
update `wraplength` secara dinamis.

---

### 9. `json/tm81_test.json` — Tidak ada validasi required params
**File:** `json/tm81_test.json`, `lib/test_loader.py`

Command seperti `dev_set_id` punya required param `device_id`. Saat ini
jika tidak diisi, command langsung return `NG:device_id kosong`.
Lebih baik test_loader memvalidasi required params sebelum run dan
menampilkan pesan yang jelas di UI.

---

### 10. Tidak ada mock serial untuk unit test
Saat ini semua test memerlukan hardware fisik (device TM81 + CH340).
Menambahkan `MockSerialComm` yang bisa reply dengan data preset
memungkinkan test parsing logic, retry logic, dan command classes
tanpa device.

---

## ✅ Sudah OK (tidak perlu diubah)

- Arsitektur command pattern (`TM81Command` base class) — bersih dan extensible
- `TM81Parser` byte constants (`ACK=0x11`, `NAK=0x0F`, dll) — benar
- Card layout di `test_row_widget.py` — scalable dan mudah dibaca
- Dark/light mode detection via OS settings — sudah cross-platform
- `test_loader.py` factory pattern untuk flash/voltage/tm81 — solid
- `if __main__` per command + per test file — berguna untuk debug
