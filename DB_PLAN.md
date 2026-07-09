# DB_PLAN.md — Jig Database Plan

Dokumen ini mencatat test mana yang **bisa** mengirim data ke database
dan mana yang **tidak bisa** (hasil tidak terstruktur / tidak relevan disimpan).

---

## ✅ Bisa dikirim ke DB

| Test | Alasan | Data yang disimpan |
|------|--------|--------------------|
| `tm81:get_version` | Return versi firmware — berguna untuk audit | result, notes (versi) |
| `tm81:get_id` | Return device ID — cocok disimpan per unit | result, notes (ID) |
| `tm81:rtc_get` | Return timestamp RTC — validasi jam akurat | result, notes (RTC time) |
| `tm81:rtc_set` | Konfirmasi set waktu berhasil | result |
| `tm81:user_get_config` | Return config user — snapshot per unit | result, notes (config) |
| `tm81:user_set_config` | Konfirmasi set config berhasil | result |
| `tm81:user_synch_config` | Konfirmasi sinkronisasi config | result |
| `tm81:user_reset_config` | Konfirmasi reset ke default | result |
| `tm81:sensor_do_get_config` | Return konfigurasi sensor | result, notes (config) |
| `tm81:sensor_data` | Return data sensor (numerik) | result, notes (data), duration_ms |
| `voltage:*` | Hasil pengukuran tegangan — penting untuk QA | result, notes (nilai voltase) |
| `flash:*` | Proses flashing — penting diaudit per unit | result, duration_ms |

---

## ❌ Tidak dikirim ke DB

| Test | Alasan |
|------|--------|
| `tm81:wdt_test` | Menyebabkan device reset — hasil tidak konsisten |
| `tm81:dev_set_id` | Hanya sekali per unit, tidak perlu di log per sesi |
| `tm81:sensor_calibration` | Proses panjang + output tidak standar |
| `tm81:bootloader_*` | Flash via bootloader — terpisah dari test QA |
| `tm81:uart_test` | Hanya loopback internal, bukan data bermakna |
| `connect_test` | Tes koneksi awal — bukan test fungsional |
| `tm81:ping` / keepalive | Dihandle otomatis oleh KeepaliveManager, bukan test task — tidak disimpan |

---

## Schema Database

```
sessions
  id, created_at, station, device_id, project, notes, finished_at, result

test_results
  id, session_id, timestamp, test_name, command, result, duration_ms, notes, raw_response
```

**Satu sesi** = satu device yang ditest dari awal hingga akhir.
**Satu record** = satu test dalam sesi tersebut.

---

## Cara Pakai

### 1. Jalankan server

```bash
pip install flask
python server/app.py
# → http://localhost:5001
```

### 2. Dari GUI (main.py)

Hubungkan `LocalServerUploader` ke `TestController`:

```python
from db_uploader import LocalServerUploader, LocalServerConfig

uploader = LocalServerUploader(
    config=LocalServerConfig(base_url="http://localhost:5001"),
    station="ST-01",
    device_id=self._device_var.get(),
    project=self._project,
)
self._controller._uploader = uploader
```

### 3. API endpoints

```
POST /api/v1/sessions                  # buat sesi
POST /api/v1/sessions/{id}/results     # kirim hasil test
GET  /api/v1/sessions                  # list semua sesi
GET  /api/v1/sessions/{id}             # detail + semua hasil
GET  /api/v1/devices/{device_id}       # riwayat device
GET  /api/v1/stats                     # statistik ringkasan
```

### 4. Tanpa server (SQLite langsung)

```python
from db_uploader import SQLiteUploader

uploader = SQLiteUploader()   # auto-create server/jig.db
self._controller._uploader = uploader
```
