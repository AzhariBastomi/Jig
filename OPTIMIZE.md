# Jig — Optimization TODO

---

## 🔴 HIGH

### 1. `_do_start()` — HTTP `new_session()` dipanggil di main thread
`_reset_db_session()` → `_new_db_session(force_new=True)` → `uploader.new_session()` adalah
HTTP POST ke Flask server. Jika server lambat atau down, UI freeze selama `timeout` detik (5s).

**Fix:** pindahkan `_new_db_session(force_new=True)` ke background thread, delay `run_all()`
hingga session siap (via `threading.Event` atau callback).

---

## 🟡 MEDIUM

### 2. `serial_comm.py` + `serial_manager.py` — masih pakai `print()`
TX/RX debug output (`[TM81 TX]`, `[TM81 RX]`, `[serial_manager]`) masih `print()`,
tidak masuk ke logging system. Tidak bisa dikontrol level-nya (DEBUG/INFO).

**Fix:** ganti semua `print()` dengan `_log.debug()` menggunakan logger per-modul.

### 3. `_on_device_change()` — bisa double-fire
`<Return>` dan `<FocusOut>` keduanya memanggil `_on_device_change()`. Di Windows, jika user
tekan Enter lalu klik area lain, kedua event bisa firing → 2 background thread spawn bersamaan.

**Fix:** tambahkan debounce sederhana (flag `_device_changing`) atau unbind FocusOut sementara.

### 4. `sys.path.insert` boilerplate di ui/ dan controllers/
Setiap file sub-package (`ui/dialogs.py`, `ui/test_list_panel.py`,
`controllers/keepalive.py`, `controllers/test_controller.py`) menambahkan `lib/` ke sys.path
secara mandiri. Redundant karena `main.py` sudah melakukannya sebelum import.

**Fix:** hapus blok sys.path dari sub-packages. Jadikan `lib/` sebagai package proper
dengan `__init__.py` dan tambahkan ke `PYTHONPATH` lewat script runner.

---

## 🟢 LOW

### 5. `keepalive.py` — akses `sm._CONN_DEFS` (private API)
`_try_connect()` membaca `sm._CONN_DEFS` langsung. Jika `serial_manager.py` mengubah nama
internal ini, `keepalive` gagal tanpa error yang jelas.

**Fix:** tambahkan fungsi publik `get_device_name(connection)` di `serial_manager.py`.

### 6. Tidak ada mock serial untuk unit test
Semua test butuh hardware fisik. Tidak bisa jalankan CI atau test offline.

**Fix:** buat `MockSerialComm` yang simulate response OK/NG untuk test tanpa device.
