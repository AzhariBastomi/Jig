# Jig — Optimization TODO

---

## 🔴 HIGH

### 1. Server mati → UI freeze + per-test retry storm
**Skenario:** server Flask tidak jalan saat Start ditekan.

- `_do_start()` → `new_session()` → `urllib.urlopen(timeout=5)` → **freeze 5 detik** di main thread
- Setelah timeout, test tetap jalan (tidak crash), tapi `_session_id = None`
- Setiap test selesai → `_ensure_session()` → `new_session()` lagi → **timeout 5 detik lagi per test**
- Jika ada 10 test: potensi 10 × 5 = **50 detik overhead** (per-test retry ke server mati)
- Semua failure hanya muncul di log (silent dari sisi UI)

**Fix:**
1. Pindahkan `_new_db_session(force_new=True)` ke background thread agar tidak freeze UI
2. Jika `new_session()` gagal, set flag `_server_unavailable = True` di uploader → skip semua `upload()` + `_ensure_session()` berikutnya tanpa retry
3. Tampilkan status server di UI (opsional)

---

## 🟡 MEDIUM

### 2. STLink tidak punya auto-reconnect seperti CH340
Error yang muncul saat STLink tercabut:
```
WARNING  serial_comm: Reader error: ClearCommError failed (PermissionError(13, ...))
```

Perbedaan handling saat ini:
- **CH340** → dijaga `KeepaliveManager` (ping tiap 5s, deteksi error, `_disconnect()` + `_try_connect()` otomatis) ✅
- **STLink** → tidak ada keepalive → reader mati → `_conns["stlink"]` zombie → **tidak pernah reconnect** ❌

Selain itu, `serial_manager` tidak register `on_disconnect` callback di `comm` manapun,
sehingga saat reader mati, `_conns[name]` tetap pegang object yang sudah mati.

Selain itu, **STLink tidak di-scan ulang jika baru dihubungkan setelah app sudah jalan**:
- **CH340** → `KeepaliveManager._run()` deteksi "tidak terhubung" → `_try_connect()` scan port → connect ✅
- **STLink** → `_auto_connect()` hanya jalan sekali saat startup (500ms setelah launch) → kalau STLink baru colok setelahnya, tidak ada yang scan ❌

**Fix:**
1. Di `serial_manager.connect()`, setelah `_conns[name] = comm`, tambahkan:
   ```python
   comm.on_disconnect(lambda n=name: _conns.pop(n, None))
   ```
   Sehingga `_conns` langsung bersih saat reader mati (berlaku semua koneksi).
2. Buat mekanisme auto-reconnect + late-plug untuk STLink — opsi paling simpel: background thread periodik (misal tiap 10s) yang scan dan connect semua koneksi yang belum terhubung, mirip `_try_connect()` di keepalive.

### 3. `serial_comm.py` + `serial_manager.py` — masih pakai `print()`
TX/RX debug output (`[TM81 TX]`, `[TM81 RX]`, `[serial_manager]`) masih `print()`,
tidak masuk ke logging system. Tidak bisa dikontrol level-nya (DEBUG/INFO).

**Fix:** ganti semua `print()` dengan `_log.debug()` menggunakan logger per-modul.

### 4. `_on_device_change()` — bisa double-fire
`<Return>` dan `<FocusOut>` keduanya memanggil `_on_device_change()`. Di Windows, jika user
tekan Enter lalu klik area lain, kedua event bisa firing → 2 background thread spawn bersamaan.

**Fix:** tambahkan debounce sederhana (flag `_device_changing`) atau unbind FocusOut sementara.

### 5. `sys.path.insert` boilerplate di ui/ dan controllers/
Setiap file sub-package (`ui/dialogs.py`, `ui/test_list_panel.py`,
`controllers/keepalive.py`, `controllers/test_controller.py`) menambahkan `lib/` ke sys.path
secara mandiri. Redundant karena `main.py` sudah melakukannya sebelum import.

**Fix:** hapus blok sys.path dari sub-packages. Jadikan `lib/` sebagai package proper
dengan `__init__.py` dan tambahkan ke `PYTHONPATH` lewat script runner.

---

## 🟢 LOW

### 6. `keepalive.py` — akses `sm._CONN_DEFS` (private API)
`_try_connect()` membaca `sm._CONN_DEFS` langsung. Jika `serial_manager.py` mengubah nama
internal ini, `keepalive` gagal tanpa error yang jelas.

**Fix:** tambahkan fungsi publik `get_device_name(connection)` di `serial_manager.py`.

### 7. Tidak ada mock serial untuk unit test
Semua test butuh hardware fisik. Tidak bisa jalankan CI atau test offline.

**Fix:** buat `MockSerialComm` yang simulate response OK/NG untuk test tanpa device.
