# Jig — Referensi Function

## main.py — `class App`

### UI / Layout

| Function | Deskripsi |
|---|---|
| `_build()` | Bangun layout utama: top bar, input area, action bar, test list panel |
| `_refresh_project_label()` | Update label project di top bar (`[TM81]`, `[FLASH]`, dll.) |
| `_refresh_dynamic_buttons()` | Tampilkan/sembunyikan tombol settings di top bar sesuai test yang dimuat (Commissioning, Flash Settings, OTA Settings) |
| `_update_start_btn()` | Enable/disable tombol Start — aktif jika ada test + SN diisi (SN hanya wajib untuk TM81 test) |
| `_apply_display(preset, w, h)` | Terapkan preset layar baru — resize window, rebuild layout, reload test list |

### Serial / Port

| Function | Deskripsi |
|---|---|
| `_auto_connect()` | Scan semua port dari `config.json`, coba connect tiap port; retry otomatis setiap 5 detik selama ada yang belum terhubung |

### Run / Stop

| Function | Deskripsi |
|---|---|
| `_toggle_run()` | Toggle Start / Stop |
| `_do_start()` | Reset semua row, buat DB session baru, jalankan semua test secara sekuensial |
| `_do_stop()` | Hentikan test yang sedang berjalan |
| `_on_seq_done(_)` | Callback setelah semua test selesai — update status bar dan finalize DB session |

### Clear

| Function | Deskripsi |
|---|---|
| `_clear_all()` | Hapus semua test dari list + reset project config JSON yang terkait |
| `_reset_project_config(project)` | Reset field user di JSON sesuai project: `flash` → kosongkan semua `file` di region aktif; `ota` → kosongkan `fw_version` |

### Add Test / Project

| Function | Deskripsi |
|---|---|
| `_open_add_test()` | Buka AddTestDialog |
| `_add_test(item, module_name)` | Tambah satu test item ke list; deteksi project; start/stop keepalive sesuai project |
| `_get_active_flash_project()` | Deteksi flash project aktif dari test_names (format `flash:proj:region`) |

### Flash / OTA

| Function | Deskripsi |
|---|---|
| `_open_flash_settings()` | Buka FlashSettingsDialog sesuai project flash yang aktif |
| `_reload_flash_tests()` | Reload semua item `flash:` dari `flash.json` setelah Flash Settings disimpan |
| `_open_ota_settings()` | Buka OTASettingsDialog |
| `_open_commissioning()` | Buka CommissioningDialog (TM81) |

### Debug Console

Logic sebenarnya ada di `DebugConsoleManager` (lihat bagian `ui/debug_console_manager.py`
di bawah) — `App` cuma jadi jembatan tipis ke tombol UI, tidak lagi menyimpan
dict window atau logic buka/tutup sendiri.

| Function | Deskripsi |
|---|---|
| `_maybe_open_debug_console()` | Delegasi ke `DebugConsoleManager.maybe_autostart()` |
| `_toggle_debug_console()` | Delegasi ke `DebugConsoleManager.build_menu(self._debug_btn)` |
| `_update_debug_btn()` | Update warna tombol Debug berdasar `DebugConsoleManager.has_any_open()` |

### Dialog

| Function | Deskripsi |
|---|---|
| `_open_display_settings()` | Buka DisplaySettingsDialog |

### DB Session

| Function | Deskripsi |
|---|---|
| `_new_db_session(force_new)` | Init LocalServerUploader; jika `force_new=False` cari session terbuka, jika `True` buat baru |
| `_reset_db_session()` | Tutup session lama lalu buat session baru |
| `_find_open_session_server(url, device_id)` | Cari session yang belum selesai di REST API |
| `_finalize_db_session(result)` | Tandai session selesai (OK/NG/None) via REST API, dijalankan di background thread |
| `_on_device_change()` | Dipanggil saat SN berubah — update context dan siapkan DB session (background thread) |
| `_on_station_change()` | Dipanggil saat Station berubah — update context dan simpan ke tasks.json |

### Persistensi

Baca/tulis file `tasks.json` sendiri sudah dipindah ke class `TaskStore`
(`lib/task_store.py`, lihat di bawah) — `App` cuma menyusun/membaca dict-nya.

| Function | Deskripsi |
|---|---|
| `_save_tasks()` | Susun dict state (test list, project, preset, station) lalu `TaskStore.save(dict)` |
| `_load_tasks()` | `TaskStore.load()` lalu terjemahkan hasilnya jadi state App (test list, project, preset, keepalive) |

---

## ui/dialogs/

### `AddTestDialog`

| Function | Deskripsi |
|---|---|
| `__init__(parent, on_add, current_project)` | Bangun dialog, posisikan di tengah parent, pasang auto-close via `bind_all` |
| `_build()` | Render satu baris per module: Flash (per project), Voltage, TM81, TM81 OTA, modul custom |
| `_btn_state(proj)` | Return `"normal"` / `"disabled"` sesuai project yang aktif |
| `_on_global_click(event)` | Auto-close jika klik di luar batas dialog |
| `_add(module_name)` | Tambah satu test + tutup dialog |
| `_add_all_flash(proj_name)` | Tambah semua region flash satu project + tutup dialog |
| `_add_all_voltage()` | Tambah semua voltage test + tutup dialog |
| `_add_all_tm81()` | Tambah semua TM81 test + tutup dialog |
| `_add_all_tm81_ota()` | Tambah semua TM81 OTA step + tutup dialog |

### `FlashSettingsDialog`

| Function | Deskripsi |
|---|---|
| `__init__(parent, flash_project, on_save)` | Load `flash.json`, bangun form per region, pasang auto-close |
| `_build()` | Render satu card per region: label, field `file`, tombol Browse |
| `_browse(var)` | Buka filedialog; ingat direktori terakhir; suppress auto-close selama browse |
| `_on_global_click(event)` | Auto-close jika klik di luar, di-suppress saat filedialog terbuka |
| `_save()` | Tulis nilai `file` tiap region ke `flash.json` |
| `_on_save()` | Simpan + panggil callback `on_save` + tutup dialog |

### `OTASettingsDialog`

| Function | Deskripsi |
|---|---|
| `__init__(parent)` | Load `tm81_ota.json` dan `flash.json`, bangun form, pasang auto-close |
| `_build()` | Render field `fw_version` + Browse |
| `_browse()` | Buka filedialog di `flash_dir`; suppress auto-close selama browse |
| `_on_global_click(event)` | Auto-close jika klik di luar, di-suppress saat filedialog terbuka |
| `_save()` | Tulis `fw_version` ke `tm81_ota.json` |
| `_on_save()` | Validasi + simpan + tutup dialog |

### `DisplaySettingsDialog`

| Function | Deskripsi |
|---|---|
| `__init__(parent, current_preset, on_apply)` | Bangun dialog pilihan preset layar, pasang auto-close |
| `_build()` | Render radio button per preset + field custom W×H |
| `_update_custom_state()` | Enable/disable field custom sesuai pilihan preset |
| `_on_global_click(event)` | Auto-close jika klik di luar batas dialog |
| `_apply()` | Panggil callback `on_apply` + tutup dialog |

---

## lib/test_loader.py

### `JsonTestSource` — base class (Template Method Pattern)

TM81, TM81 OTA, dan BEXA sama-sama disimpan sebagai
`{"label": ..., "tests": [{"name":, "command_class":, "type": ...}]}` dan butuh
logic yang sama: baca JSON, filter entry `disabled`, resolve `command_class`
secara dinamis, derive label & daftar module_names. Logic itu hidup sekali di
`JsonTestSource`; subclass cukup override `make_item(entry)`.

| Method | Deskripsi |
|---|---|
| `read_json()` | Baca file di `self.json_path`, return `{}` kalau gagal |
| `is_enabled(entry)` | True kalau `"name"` ada dan `disabled` != true (override di `TM81OtaTestSource`: tidak ada konsep disabled) |
| `label()` | Label dari `cfg["label"]`, fallback ke nama file |
| `module_names()` | List `"<prefix>:<name>"` untuk entry yang enabled |
| `load_all()` | List `TestItem` untuk semua entry yang enabled |
| `load_one(entry_name)` | Satu `TestItem`; raise `KeyError` kalau tidak ada / disabled |
| `resolve_command_class(class_path)` *(static)* | Import class dinamis dari string `"pkg.mod.Class"` — return `(cls, error_message)` |
| `make_item(entry)` | **Override wajib di subclass** — bangun satu `TestItem` dari satu entry |

**Subclass:**

| Class | Beda dengan base |
|---|---|
| `TM81TestSource` | Tiap entry butuh `commissioning` (merge `tm81_test.json` + `commissioning.json`) untuk resolve params `"@key"`; dihitung sekali per `load_all()`/`load_one()`, dipakai semua entry lewat `self._commissioning` |
| `TM81OtaTestSource` | Tiap entry butuh `fw_path`/`chunk_size`/dll dari `commissioning.json["ota"]` + `flash.json` + `tm81_ota.json["fw_version"]` sendiri; disimpan di `self._cfg`. `is_enabled()` di-override (tidak ada field `disabled`) |
| `BexaTestSource` | Paling sederhana — tidak ada context/commissioning tambahan |

Instance module-level: `_tm81_source`, `_tm81_ota_source`, `_bexa_source` — dipakai
oleh fungsi publik di bawah (semua tetap dengan nama & signature yang sama seperti
sebelumnya, jadi tidak ada caller yang perlu berubah):

| Function | Delegasi ke |
|---|---|
| `load_tm81_tests()` / `tm81_module_names()` / `tm81_label()` | `_tm81_source` |
| `load_tm81_ota_tests()` / `tm81_ota_module_names()` / `tm81_ota_label()` | `_tm81_ota_source` |
| `load_bexa_tests()` / `bexa_module_names()` / `bexa_label()` | `_bexa_source` |

### Fungsi lain

| Function | Deskripsi |
|---|---|
| `load_test(module_name)` | Load satu TestItem dari module name; mendukung format `flash:proj:region`, `tm81:`, `tm81_ota:`, `bexa:`, `voltage:`, dll. |
| `discover_tests()` | Scan folder `tests/` untuk modul custom |
| `update_context(ctx)` | Update context global (device_id, station) yang dibaca test saat runtime |
| `flash_project_names()` | Daftar nama project dari `flash.json["projects"]` |
| `flash_project_label(proj_name)` | Label tampilan project flash (dari field `label` di JSON) |
| `flash_module_names(proj_name)` | List module name untuk semua region project (`flash:tm81:boot`, dll.) |
| `load_flash_tests_named(proj_name)` | Load semua TestItem + module_name untuk region yang aktif (skip opsional + file kosong) |
| `voltage_module_names()` | List module name voltage test |
| `_region_active(r)` | Return False jika region `optional=True` AND `file` kosong |

---

## lib/test_modules.py

### `TestItem` hierarchy (Polymorphism)

`TestItem` (base) → `ProgressBarTest` / `ManualTest` / `AutoTest`. Tiap subclass
mendeklarasikan atribut dirinya sendiri — kode luar (widget/controller/loader)
tidak perlu tanya "kamu tipe apa", tinggal baca atribut ini:

| Atribut/Method | Deskripsi |
|---|---|
| `type_key` | String kunci registrasi (`"auto"` / `"manual"` / `"progress"`) — dipakai `build_test_item()` dan `ui.row_behavior.get_behavior()` |
| `is_manual` | `True` hanya di `ManualTest` — dipakai controller (`_seq_worker`) tanpa perlu cek `TestType` |
| `reset()` | Kembalikan result ke PENDING, kosongkan last_error |
| `is_done()` | True kalau result OK/NG |

### Factory Pattern

| Function | Deskripsi |
|---|---|
| `TEST_TYPE_REGISTRY` | Dict `type_key -> class`, dibangun otomatis dari `cls.type_key` tiap subclass |
| `build_test_item(type_key, **kwargs)` | Instansiasi subclass yang tepat; fallback ke `AutoTest` kalau `type_key` tak dikenal |

---

## lib/validation_rules.py (Strategy Pattern)

Rule validasi dari `"validate"` di `tm81_test.json` (mis. `{"device_id": 1}`,
`{"dev_addr": "nonzero_hex"}`) diterjemahkan jadi objek `ValidationRule` — loop
validasi di `test_loader.py` cukup panggil `rule.check(value)`, tidak perlu tahu
jenis rule-nya.

| Class/Function | Deskripsi |
|---|---|
| `ValidationRule.check(value)` | Interface — True kalau valid |
| `ValidationRule.default_message(param)` | Interface — pesan NG default |
| `MinLengthRule(n)` | Rule lama: nilai int di JSON → panjang string minimal `n` |
| `NonzeroHexRule()` | Rule lama: string `"nonzero_hex"` → nilai hex tidak boleh 0 |
| `build_rule(raw)` | Factory — ubah rule mentah dari JSON jadi objek `ValidationRule` |
| `CUSTOM_MESSAGES` | Dict override pesan per-parameter (mis. `"device_id"` → pesan yang lebih ramah) |
| `validation_message(param, rule)` | Pesan NG final — custom kalau ada di `CUSTOM_MESSAGES`, default kalau tidak |

---

## ui/row_behavior.py (Strategy + Polymorphism + Factory)

Perilaku UI per `TestType` (bangun tombol, respons running/selesai/reset) yang
dulu jadi if/elif panjang di `TestRowWidget`, sekarang jadi class terpisah.

| Class | Deskripsi |
|---|---|
| `RowBehavior` (base) | Default — dipakai `AutoTest`: satu tombol Run, tanpa progress bar |
| `ProgressBehavior` | Tombol Run + progress bar (dipakai flashing, sensor calibration) |
| `ManualBehavior` | Tombol OK/NG, tidak ada Run (`supports_validation = False`) |
| `get_behavior(type_key)` | Factory — pilih instance behavior yang cocok dari `BEHAVIOR_REGISTRY` |

Method yang di-override tiap subclass: `build_control(row)`, `build_progress_area(row, ...)`,
`set_running(row)`, `set_result(row, ...)`, `reset(row)`.

---

## ui/test_row_widget.py — class `TestRowWidget`

| Function | Deskripsi |
|---|---|
| `show_retry(attempt, total)` | Update status text jadi "Retry n/total..." — dipanggil controller, tidak lagi akses `_status_lbl` langsung |
| `refresh_validation()` | Cek `validate_fn` tanpa menjalankan test — enable/disable tombol Run real-time (dipanggil saat field device_id berubah / Commissioning Settings disimpan) |
| `ResultState` / `RESULT_STATES` | State Pattern ringan — badge (teks+warna) per `TestResult`, satu sumber data dipakai `_build()` dan `_update_badge()` |

---

## ui/debug_console_manager.py — class `DebugConsoleManager`

Dulu jadi dict `self._debug_consoles` + 4 method di `App` (God Object). Sekarang
berdiri sendiri — `App` cuma compose satu instance dan delegasi.

| Method | Deskripsi |
|---|---|
| `open_or_focus(key, title, ...)` | Buka (atau fokus) satu window DebugConsole beridentitas `key` |
| `maybe_autostart()` | Buka window otomatis saat startup jika `config.json debug.enabled = 1`; layout grid 2 kolom |
| `build_menu(anchor_btn)` | Bangun & tampilkan menu popup pilihan window, anchor ke tombol 🐛 Debug |
| `has_any_open()` | True kalau ada window yang masih terbuka — dipakai `App._update_debug_btn()` |

---

## lib/task_store.py — class `TaskStore`

Baca/tulis `tasks.json` — murni file I/O, tidak tahu apa-apa soal Tkinter atau
`TestItem`. Dulu jadi bagian `App._save_tasks()`/`_load_tasks()` (God Object).

| Method | Deskripsi |
|---|---|
| `load()` | Return dict data tasks.json (`{}` kalau tidak ada/rusak/versi lebih baru dari yang didukung); format lama (list) dinormalisasi jadi `{"tests": [...]}` |
| `save(data)` | Simpan dict ke `tasks.json`, key `"version"` otomatis ditambahkan |

---

## lib/project.py

| Function | Deskripsi |
|---|---|
| `module_project(module_name)` | Return project string (`"tm81"`, `"flash"`, `"ota"`, dll.) dari module name, atau None |
| `detect_project(test_names)` | Deteksi project dari list module names yang dimuat |

---

## controllers/

`TestController.run_test()` dan `_seq_worker()` tidak lagi cek `TestType` lewat
if/elif — dispatch fallback (item tanpa `run_fn`, mis. test bawaan demo) lewat
`_runner_registry` (dict `type_key -> method`), dan cek manual lewat `item.is_manual`.

| Class / Function | Deskripsi |
|---|---|
| `TestController._runner_registry` | Dict `{"progress": _run_progress, "manual": _run_manual, "auto": _run_auto}` — Factory/Strategy registry |
| `TestController.run_all(rows, done_callback, scroll_fn)` | Jalankan semua test secara sekuensial di background thread |
| `TestController.stop_now(rows)` | Hentikan test yang sedang berjalan, set status SKIP untuk yang belum |
| `TestController.is_seq_running()` | Return True jika test sedang berjalan |
| `KeepaliveManager.start()` | Mulai keepalive ping ke TM81 di background thread |
| `KeepaliveManager.stop()` | Hentikan keepalive |

---

## Ringkasan Pola OOP yang Diterapkan

Detail lengkap tiap pattern (di mana, kenapa, dan contoh kode) ada di
`docs/ARSITEKTUR.md`. Ringkasan lokasinya:

| Pattern | Lokasi |
|---|---|
| **Factory** | `test_modules.build_test_item()` + `TEST_TYPE_REGISTRY`; `row_behavior.get_behavior()` + `BEHAVIOR_REGISTRY`; `validation_rules.build_rule()`; `TestController._runner_registry` |
| **Strategy** | `TestItem.run_fn` / `validate_fn` (callable disuntik ke objek); `validation_rules.ValidationRule` hierarchy (`MinLengthRule`, `NonzeroHexRule`) |
| **Polymorphism** | `TestItem` → `ProgressBarTest`/`ManualTest`/`AutoTest` (`type_key`, `is_manual`); `RowBehavior` → `ProgressBehavior`/`ManualBehavior` |
| **State** (ringan) | `ResultState`/`RESULT_STATES` di `ui/test_row_widget.py` |
| **Template Method** | `JsonTestSource` (base) → `TM81TestSource`/`TM81OtaTestSource`/`BexaTestSource` di `lib/test_loader.py` |
| **Encapsulation fix** | `TestRowWidget.show_retry()` — controller tidak lagi akses widget privat langsung |
| **Single Responsibility** | `TaskStore` (I/O tasks.json) dan `DebugConsoleManager` (window debug) diekstrak dari `App` (god object) di `main.py` |

---

*Terakhir diupdate: 2026-07-24*
