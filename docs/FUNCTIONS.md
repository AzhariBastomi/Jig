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

| Function | Deskripsi |
|---|---|
| `_maybe_open_debug_console()` | Buka debug window otomatis saat startup jika `config.json debug.enabled = 1`; layout grid 2 kolom |
| `_toggle_debug_console()` | Klik tombol 🐛 Debug — tampilkan menu pilihan window per serial port + extras |
| `_open_named_debug(key, title, ...)` | Buka (atau fokus) satu DebugConsole window beridentitas `key` |
| `_update_debug_btn()` | Update warna tombol Debug (biru = ada window terbuka, abu = semua tutup) |

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

| Function | Deskripsi |
|---|---|
| `_save_tasks()` | Simpan state (test list, project, preset, station) ke `tasks.json` |
| `_load_tasks()` | Load state dari `tasks.json` saat startup; skip format lama dengan warning |

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

## lib/test_loader.py (fungsi utama)

| Function | Deskripsi |
|---|---|
| `load_test(module_name)` | Load satu TestItem dari module name; mendukung format `flash:proj:region`, `tm81:`, `tm81_ota:`, `voltage:`, dll. |
| `discover_tests()` | Scan folder `tests/` untuk modul custom |
| `update_context(ctx)` | Update context global (device_id, station) yang dibaca test saat runtime |
| `flash_project_names()` | Daftar nama project dari `flash.json["projects"]` |
| `flash_project_label(proj_name)` | Label tampilan project flash (dari field `label` di JSON) |
| `flash_module_names(proj_name)` | List module name untuk semua region project (`flash:tm81:boot`, dll.) |
| `load_flash_tests_named(proj_name)` | Load semua TestItem + module_name untuk region yang aktif (skip opsional + file kosong) |
| `tm81_label()` | Label dari `tm81_test.json["label"]`, fallback ke nama file |
| `tm81_ota_label()` | Label dari `tm81_ota.json["label"]`, fallback ke nama file |
| `tm81_module_names()` | List module name TM81 test |
| `tm81_ota_module_names()` | List module name TM81 OTA step |
| `voltage_module_names()` | List module name voltage test |
| `_region_active(r)` | Return False jika region `optional=True` AND `file` kosong |

---

## lib/project.py

| Function | Deskripsi |
|---|---|
| `module_project(module_name)` | Return project string (`"tm81"`, `"flash"`, `"ota"`, dll.) dari module name, atau None |
| `detect_project(test_names)` | Deteksi project dari list module names yang dimuat |

---

## controllers/

| Class / Function | Deskripsi |
|---|---|
| `TestController.run_all(rows, done_callback, scroll_fn)` | Jalankan semua test secara sekuensial di background thread |
| `TestController.stop_now(rows)` | Hentikan test yang sedang berjalan, set status SKIP untuk yang belum |
| `TestController.is_seq_running()` | Return True jika test sedang berjalan |
| `KeepaliveManager.start()` | Mulai keepalive ping ke TM81 di background thread |
| `KeepaliveManager.stop()` | Hentikan keepalive |

---

*Terakhir diupdate: 2026-07-23*
