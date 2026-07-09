# Jig — Optimization TODO

---

## 🔴 HIGH — Potensi bug / race condition

### 1. ~~`lib/serial_comm.py` — `_cb_data` tidak thread-safe~~ ✅ DONE

### 2. ~~`lib/serial_comm.py` — Double disconnect callback~~ ✅ DONE

### 3. `test_loader.context` — dict shared antar thread tanpa lock
`test_loader.context` diakses dari main thread (UI trace) dan background thread
(worker `_run_with_fn`). Bisa race condition saat device_id diupdate sambil worker
sedang membaca.

**Fix:** ganti dengan `threading.local()` atau tambahkan `threading.Lock`.

### 4. DB I/O di main thread
`_new_db_session()` dan `_find_open_session_sqlite()` melakukan query SQLite di
main thread (dipanggil dari `_on_device_change` — UI callback). Jika DB lambat,
UI bisa freeze sebentar.

**Fix:** jalankan `_new_db_session()` di background thread via `threading.Thread`.

---

## 🟡 MEDIUM — Performance / maintainability

### 5. ~~`lib/serial_comm.py` — Reader baca 1 byte per call~~ ✅ DONE

### 6. ~~`commands/tm81/*.py` — `sys.path.insert` jalan di module-level~~ ✅ DONE

### 7. `main.py` — Terlalu monolitik (~1300 baris)
**Disarankan (next sprint):**
```
ui/
  test_list_panel.py
  dialogs.py
controllers/
  test_controller.py
  keepalive.py
main.py   ← App saja + entry point
```

### 8. ~~`main.py` — `_auto_connect` Tkinter thread safety~~ ✅ DONE
Log calls di-schedule via `self.after(0, ...)`.

### 9. `server/app.py` — Flask dev server single-threaded
Flask built-in server tidak cocok untuk concurrent requests. Jika beberapa PC
kirim data bersamaan (multi-station setup), bisa bottleneck.

**Fix:** tambahkan `threaded=True` atau pakai `waitress`:
```bash
pip install waitress
python -m waitress --port=5001 server.app:app
```

### 10. Session `finished_at` tidak di-set untuk individual test run
`_finalize_db_session()` hanya dipanggil di `_on_seq_done()` (sequential run).
Kalau user run test satu-satu via tombol Run, session tidak pernah ditutup
(`finished_at` tetap NULL selamanya).

**Fix:** finalize session saat app close (`protocol("WM_DELETE_WINDOW", ...)`)
atau saat Start sequential run dimulai (sudah dilakukan di `_reset_db_session`).

---

## 🟢 LOW — Nice to have

### 11. ~~`config.py` — `ROW_HEIGHT` tidak lagi dipakai~~ ✅ DONE

### 12. ~~`test_row_widget.py` — `wraplength` status label hardcoded~~ ✅ DONE

### 13. ~~`lib/test_loader.py` — Resolve class command saat load, bukan saat run~~ ✅ DONE

### 14. ~~`requirements.txt` — Encoding UTF-16~~ ✅ DONE

### 15. `json/tm81_test.json` — Tidak ada validasi required params
Command seperti `dev_set_id` butuh `device_id`. Kalau kosong baru ketahuan saat run.

### 16. ~~`tasks.json` — Tidak ada version field~~ ✅ DONE
`"version": 2` + field `"project"` ditambahkan.

### 17. Tidak ada mock serial untuk unit test
Semua test butuh hardware fisik. Tambahkan `MockSerialComm`.

### 18. ~~Logging masih pakai `print()`~~ ✅ DONE
Semua output ke `logging` module. KeepaliveManager pakai logger `keepalive` terpisah.

### 19. Validasi input SN field
SN bisa dikosongkan atau diisi spasi → session tersimpan dengan `device_id=""`.
Sebaiknya disable tombol Run/Start jika SN kosong, atau tampilkan warning.

---

## ✅ Sudah OK / Selesai

- Arsitektur command pattern (`TM81Command` base class)
- Card layout di `test_row_widget.py`
- `test_loader.py` factory pattern
- `if __main__` per command + per test file
- Thread-safety `_cb_data` di `serial_comm.py`
- `KeepaliveManager` — background ping TM81, auto reconnect on error
- Project lock di `AddTestDialog` (tm81/flash tidak bisa dicampur)
- Flask + SQLite server di `server/` — REST API
- `SQLiteUploader` + `LocalServerUploader` di `lib/db_uploader.py`
- DB session: resume jika SN sama, buat baru jika SN beda
- `DB_PLAN.md` — dokumentasi test mana yang dikirim ke DB
- `json/config.json` — `keepalive` + `database` section
- `.gitignore` — `server/jig.db`, `jig.db-shm`, `jig.db-wal`
