# Jig — Arsitektur & Pola OOP

Dokumen ini menjelaskan pola desain (design pattern) dan prinsip OOP yang
diterapkan di codebase, di mana lokasinya, dan kenapa dipilih. Untuk referensi
lengkap semua function/class per file, lihat `docs/FUNCTIONS.md`. Untuk daftar
fitur end-user, lihat `docs/FITUR.md`.

---

## 1. Factory Pattern

Dipakai di beberapa tempat untuk menghilangkan blok `if/elif` yang menentukan
"kelas apa yang harus dibuat" berdasarkan sebuah string kunci.

### `test_modules.build_test_item(type_key, **kwargs)`

```python
TEST_TYPE_REGISTRY = {cls.type_key: cls for cls in (ProgressBarTest, ManualTest, AutoTest)}

def build_test_item(type_key: str, **kwargs) -> TestItem:
    cls = TEST_TYPE_REGISTRY.get(type_key, AutoTest)
    return cls(**kwargs)
```

Dipakai oleh `lib/test_loader.py` di 5 tempat (TM81, TM81 OTA, BEXA, class-based
test biasa) — dulu masing-masing punya `if ttype == "progress": ... elif ttype
== "manual": ... else: ...` sendiri-sendiri. Menambah `TestType` baru sekarang
= menambah 1 subclass + 1 baris di `TEST_TYPE_REGISTRY`, bukan mengubah 5 tempat.

### `row_behavior.get_behavior(type_key)`

Sama polanya, tapi untuk memilih strategi tampilan (lihat Strategy/Polymorphism
di bawah).

### `validation_rules.build_rule(raw)`

Mengubah rule mentah dari JSON (`1`, `"nonzero_hex"`) jadi objek `ValidationRule`
yang tepat.

### `TestController._runner_registry`

Dict `{"progress": self._run_progress, "manual": self._run_manual, "auto":
self._run_auto}` — dipakai sebagai fallback untuk item tanpa `run_fn` (test
bawaan/demo). Menggantikan `if t == TestType.PROGRESS: ... elif ...`.

---

## 2. Strategy Pattern

Objek yang perilakunya bisa "disuntik" dari luar, bukan di-hardcode di dalam
class.

### `TestItem.run_fn` / `TestItem.validate_fn`

Sudah ada sejak awal — tiap `TestItem` menyimpan callable `run_fn` (cara
menjalankan test) dan `validate_fn` (cara mengecek sebelum jalan) sebagai
atribut. `TestController` dan `TestRowWidget` tinggal memanggil
`item.run_fn()` / `item.validate_fn()` tanpa tahu isinya.

### `lib/validation_rules.py` — `ValidationRule` hierarchy

```python
class ValidationRule:
    def check(self, value: str) -> bool: ...
    def default_message(self, param: str) -> str: ...

class MinLengthRule(ValidationRule): ...
class NonzeroHexRule(ValidationRule): ...
```

`test_loader._validate_fn` dulu punya:

```python
if isinstance(rule, int):
    ...
elif rule == "nonzero_hex":
    ...
```

Sekarang tinggal:

```python
rule = build_rule(raw_rule)
if not rule.check(val):
    return f"NG:{validation_message(param, rule)}"
```

Menambah jenis rule baru = menambah 1 class + 1 baris di `build_rule()`, tanpa
menyentuh loop validasi.

---

## 3. Polymorphism

### `TestItem` → `ProgressBarTest` / `ManualTest` / `AutoTest`

Tiap subclass mendeklarasikan `type_key` dan `is_manual` sendiri. Kode luar
(widget, controller, loader) tidak pernah menulis
`if item.test_type == TestType.MANUAL` lagi — cukup baca `item.is_manual` atau
`item.type_key`.

### `RowBehavior` → `ProgressBehavior` / `ManualBehavior`

`TestRowWidget` dulu punya `if/elif` di 5 method (`_build_control`,
`set_running`, `set_result`, `reset`, `refresh_validation`) yang semuanya
bercabang berdasarkan `test_type`. Sekarang `TestRowWidget` cuma pegang satu
`self._behavior` (dipilih via `get_behavior()`) dan memanggil method yang sama
di semua kasus — subclass mana yang menjawab, `TestRowWidget` tidak peduli:

```python
def set_result(self, result, error="", ok_msg=""):
    ...
    self._behavior.set_result(self, result, ok_brief, ok_detail, err_brief, err_detail, err_full)
```

---

## 4. State Pattern (versi ringan)

`ui/test_row_widget.py`:

```python
@dataclass(frozen=True)
class ResultState:
    badge_text: str
    badge_bg_key: str

RESULT_STATES = {
    TestResult.PENDING: ResultState("---", "pending"),
    TestResult.RUNNING: ResultState("...", "running"),
    TestResult.OK:      ResultState(" OK ", "ok"),
    TestResult.NG:      ResultState(" NG ", "ng"),
}
```

Badge (teks + warna) jadi satu sumber data per `TestResult`, dipakai baik saat
widget pertama dibangun maupun saat `_update_badge()` dipanggil ulang — bukan
dua dict paralel yang diakses manual.

---

## 5. Template Method Pattern

### `JsonTestSource` (lib/test_loader.py)

TM81, TM81 OTA, dan BEXA disimpan dalam format JSON yang sama:
`{"label": ..., "tests": [{"name":, "command_class":, "type": ...}]}`, dan
butuh logic yang identik: baca file, filter `disabled`, resolve
`command_class` secara dinamis, derive `label()`/`module_names()`. Logic itu
sekarang hidup sekali di base class `JsonTestSource`; subclass
(`TM81TestSource`, `TM81OtaTestSource`, `BexaTestSource`) cukup override
`make_item(entry)` untuk bagian yang memang beda.

```python
class JsonTestSource:
    def read_json(self) -> dict: ...
    def is_enabled(self, entry) -> bool: ...
    def label(self) -> str: ...
    def module_names(self) -> list: ...
    def load_all(self) -> list: ...
    def load_one(self, entry_name): ...
    def make_item(self, entry):
        raise NotImplementedError   # wajib di-override
```

Semua fungsi publik lama (`load_tm81_tests()`, `tm81_label()`, dst.) tetap ada
dengan nama & signature yang sama — jadi tidak ada satu pun caller (`main.py`,
`ui/dialogs/add_test.py`) yang perlu berubah.

**Kenapa Flash dan Voltage TIDAK ikut masuk hierarchy ini:** bentuk datanya
beda cukup jauh (flash: multi-project + region, tidak ada konsep
`disabled`/`command_class` dinamis; voltage: selalu manual, tanpa
command_class sama sekali). Memaksakan keduanya ikut `JsonTestSource` akan
menghasilkan override yang janggal di hampir semua method — abstraksi yang
dipaksakan seperti itu justru lebih buruk daripada duplikasi kecil yang ada
sekarang. Prinsipnya: pola dipakai kalau memang mengurangi duplikasi nyata,
bukan dipakai supaya "kelihatan OOP".

---

## 6. Encapsulation

### `TestRowWidget.show_retry(attempt, total)`

Sebelumnya `TestController` menulis langsung ke widget privat milik row:

```python
row._status_lbl.config(text=f"Retry {a}/{n}...", fg=COLORS["running"])
```

Ini melanggar enkapsulasi — controller (logic) tidak seharusnya tahu row
punya atribut `_status_lbl` atau bagaimana cara mewarnainya. Sekarang:

```python
row.show_retry(a, n)
```

`TestRowWidget` yang memutuskan sendiri bagaimana menampilkan retry-nya.

---

## 7. Single Responsibility — memecah `App` (main.py)

`App` di `main.py` sebelumnya menangani: UI building, event handling, task
persistence, DB session, keepalive, debug console — semuanya sebagai method
dalam satu class besar (God Object). Dua tanggung jawab yang paling berdiri
sendiri diekstrak:

| Class baru | Tanggung jawab | Menggantikan |
|---|---|---|
| `lib/task_store.TaskStore` | Baca/tulis `tasks.json` — murni file I/O | `App._save_tasks()` / `_load_tasks()` |
| `ui/debug_console_manager.DebugConsoleManager` | Buka/fokus/tutup window DebugConsole | `App._debug_consoles` (dict) + 4 method |

`App` sekarang meng-compose kedua objek ini di `__init__` dan delegasi — tidak
lagi mengimplementasikan logicnya sendiri.

**Yang belum dipecah (di luar scope sesi ini):** `App._build()` (widget-building
inti), sequential-run logic (`_do_start`/`_do_stop`/`_on_seq_done`), dan DB
session logic (`_new_db_session`/`_finalize_db_session`) masih jadi method
`App`. Ini sengaja tidak disentuh dulu karena risikonya lebih tinggi (tidak
bisa di-test visual di sandbox tanpa display) — kalau mau dilanjutkan, kandidat
berikutnya adalah `SequenceRunner` (Start/Stop/status) dan `DbSessionManager`
(REST API session TM81) sebagai class terpisah dari `App`.

---

*Terakhir diupdate: 2026-07-24*
