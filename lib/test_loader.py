"""
test_loader.py - Discover dan load test modules dari folder tests/.

Mendukung dua gaya penulisan test:

  1. CLASS-BASED (dianjurkan):
        from test_base import TestBase
        class SumTest(TestBase):
            TITLE   = "Penjumlahan"
            TYPE    = "auto"
            COMMAND = "TEST_SUM"
            def run(self): return "OK"

  2. FUNCTIONAL (lama, tetap kompatibel):
        TITLE   = "Penjumlahan"
        TYPE    = "auto"
        COMMAND = "TEST_SUM"
        def run(): return "OK"

Flash tasks (format khusus):
  - Disimpan di tasks.json sebagai "flash:<region_name>", misal "flash:boot"
  - Di-expand dari flash.json: satu region = satu row task terpisah

TM81 tasks (format khusus):
  - Disimpan di tasks.json sebagai "tm81:<name>", misal "tm81:ping"
  - Di-expand dari commands/tm81/config/tm81_test.json

TM81 Flash tasks (format khusus, sama dengan TM81):
  - Disimpan di tasks.json sebagai "tm81_ota:<name>", misal "tm81_ota:write_fw"
  - Di-expand dari commands/tm81/config/tm81_ota.json -> tests
  - Setiap langkah = satu row; write_fw memakai ProgressBarTest
  - load_tm81_ota_tests() -> list[TestItem]  (semua 4 langkah sekaligus)
  - load_test("tm81_ota:write_fw")           (satu langkah)
"""

import importlib
import inspect
import json
import logging
import os
import pkgutil
import threading
import tests

_log = logging.getLogger("test_loader")

from test_base import TestBase
from test_modules import ProgressBarTest, ManualTest, AutoTest

# ---------------------------------------------------------------------------
# Shared context — diisi oleh app sebelum test dijalankan.
# Thread-safe: gunakan get_context() / update_context() untuk akses dari thread.
# ---------------------------------------------------------------------------
context: dict = {}
_context_lock = threading.Lock()


def get_context(key: str, default: str = "") -> str:
    """Thread-safe getter untuk context."""
    with _context_lock:
        return context.get(key, default)


def update_context(data: dict) -> None:
    """Thread-safe update untuk context."""
    with _context_lock:
        context.update(data)

_ROOT               = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_FLASH_JSON         = os.path.join(_ROOT, "config", "flash.json")
_VOLTAGE_JSON       = os.path.join(_ROOT, "config", "voltage.json")
_TM81_JSON          = os.path.join(_ROOT, "commands", "tm81", "config", "tm81_test.json")
_TM81_OTA_JSON      = os.path.join(_ROOT, "commands", "tm81", "config", "tm81_ota.json")
_COMMISSIONING_JSON = os.path.join(_ROOT, "commands", "tm81", "config", "commissioning.json")
_BEXA_JSON          = os.path.join(_ROOT, "commands", "bexa",  "config", "bexa_test.json")


# ---------------------------------------------------------------------------
# Flash helpers  (multi-project: flash.json["projects"])
# ---------------------------------------------------------------------------

def _read_flash_json() -> dict:
    """Baca flash.json. Return {} jika tidak ada."""
    try:
        with open(_FLASH_JSON) as f:
            return json.load(f)
    except Exception:
        return {}


def flash_project_names() -> list[str]:
    """Return list nama project flash, misal ['tm81', 'bexa']."""
    return list(_read_flash_json().get("projects", {}).keys())


def flash_project_label(proj_name: str) -> str:
    """Return label tampilan untuk project flash, misal 'TM81' atau 'BEXA'."""
    proj = _read_flash_json().get("projects", {}).get(proj_name, {})
    return proj.get("label", proj_name.upper())


def _get_flash_regions(proj_name: str) -> list:
    """Return list region untuk project tertentu."""
    return _read_flash_json().get("projects", {}).get(proj_name, {}).get("regions", [])


def _region_active(r: dict) -> bool:
    """Region muncul di list kecuali optional=true dan file kosong."""
    if r.get("optional") and not r.get("file", "").strip():
        return False
    return True


def _make_flash_item(region: dict, proj_name: str = ""):
    """Buat satu ProgressBarTest untuk satu region flash."""
    from tests.flash_test import FlashTest

    name      = region.get("name", "unknown")
    base_desc = region.get("description", f"Flash region '{name}'")
    fw_file   = region.get("file", "").strip()
    address   = region.get("address", "0x08000000").strip()
    fw_label  = os.path.basename(fw_file) if fw_file else "⚠ file belum diset"
    desc      = f"{base_desc}  •  {fw_label}  @  {address}"
    cmd_tag   = f"{proj_name.upper()}_{name.upper()}" if proj_name else name.upper()

    cls      = type(f"_FlashTest_{proj_name}_{name}", (FlashTest,), {
        "TITLE":       f"Flash {name}",
        "COMMAND":     f"FLASH_{cmd_tag}",
        "DESCRIPTION": desc,
        "REGION":      region,
    })
    instance = cls()

    return ProgressBarTest(
        title       = f"Flash {name}",
        command     = f"FLASH_{cmd_tag}",
        description = desc,
        run_fn      = instance.run,
        steps       = getattr(cls, "STEPS",   10),
        step_ms     = getattr(cls, "STEP_MS", 300),
    )


def flash_module_names(proj_name: str) -> list[str]:
    """Return ['flash:tm81:boot', 'flash:tm81:app'] untuk semua region project (termasuk belum dikonfigurasi)."""
    return [f"flash:{proj_name}:{r['name']}" for r in _get_flash_regions(proj_name)]


def load_flash_tests_named(proj_name: str) -> list[tuple]:
    """Return [(TestItem, 'flash:proj:name'), ...] hanya region yang aktif (_region_active)."""
    return [
        (_make_flash_item(r, proj_name), f"flash:{proj_name}:{r['name']}")
        for r in _get_flash_regions(proj_name)
        if _region_active(r)
    ]


def load_flash_tests(proj_name: str) -> list:
    """Return list TestItem untuk project flash tertentu (region aktif saja)."""
    return [item for item, _ in load_flash_tests_named(proj_name)]


# ---------------------------------------------------------------------------
# Voltage helpers
# ---------------------------------------------------------------------------

def _read_voltage_json() -> dict:
    """Baca voltage.json. Return {} jika tidak ada."""
    try:
        with open(_VOLTAGE_JSON) as f:
            return json.load(f)
    except Exception:
        return {}


def _make_voltage_item(entry: dict):
    """Buat satu ManualTest untuk satu entry voltage."""
    name  = entry.get("name", "unknown")
    label = entry.get("label", name)
    desc  = entry.get("description", f"Cek tegangan {label}")
    cmd   = entry.get("command", f"VOLT_{name.upper()}")

    # Selalu manual — operator cek pakai multimeter, klik OK/NG sendiri
    return ManualTest(title=f"Voltage {label}", command=cmd,
                      description=desc, run_fn=None)


def load_voltage_tests() -> list:
    """Baca voltage.json dan kembalikan list TestItem — satu per entry."""
    cfg = _read_voltage_json()
    return [_make_voltage_item(v) for v in cfg.get("voltages", [])]


def voltage_module_names() -> list[str]:
    """Kembalikan ["voltage:3v3", "voltage:1v8", ...] sesuai urutan di voltage.json."""
    cfg = _read_voltage_json()
    return [f"voltage:{v['name']}" for v in cfg.get("voltages", [])]


# ---------------------------------------------------------------------------
# TM81 helpers
# ---------------------------------------------------------------------------

def _read_tm81_json() -> dict:
    """Baca tm81_test.json. Return {} jika tidak ada."""
    try:
        with open(_TM81_JSON) as f:
            return json.load(f)
    except Exception:
        return {}


def _read_commissioning_json() -> dict:
    """
    Baca commissioning.json (ditulis oleh CommissioningDialog).
    Return {} jika file belum ada.
    Strukturnya sama dengan bagian 'commissioning' di tm81_test.json.
    """
    try:
        with open(_COMMISSIONING_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _merge_commissioning(base: dict) -> dict:
    """
    Gabungkan commissioning.json (prioritas lebih tinggi) ke atas commissioning
    dari tm81_test.json. Return dict yang sudah di-merge.
    """
    ext = _read_commissioning_json()
    if not ext:
        return base
    merged = dict(base)
    for key, val in ext.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            # Merge per-key, skip _doc fields
            merged[key] = {
                **merged.get(key, {}),
                **{k: v for k, v in val.items() if not k.startswith("_")},
            }
        else:
            merged[key] = val
    return merged


def _make_tm81_item(entry: dict, commissioning: dict = None):
    """Buat AutoTest untuk satu entry di tm81_test.json.

    commissioning — dict dari section 'commissioning' di tm81_test.json.
    Params priority: commissioning[name] < entry['params'] < context['@key'].
    """
    import importlib as _imp
    import sys as _sys

    name        = entry.get("name", "unknown")
    label       = entry.get("label", name)
    desc        = entry.get("description", "")
    cmd_class   = entry.get("command_class", "")
    ttype       = entry.get("type", "auto").lower()

    # Params di-resolve saat runtime:
    # 1. commissioning[name]  — nilai per-batch dari dalam test JSON itu sendiri
    # 2. entry["params"]      — override statis (opsional, jarang perlu)
    # 3. "@key" → context[key] — nilai per-device dari UI
    _commissioning = commissioning or {}
    static_params  = entry.get("params", {})

    def _resolve_params() -> dict:
        # Base: commissioning[name], skip field "_doc"
        params = {k: v for k, v in _commissioning.get(name, {}).items()
                  if not k.startswith("_")}
        # Override dengan static_params dari entry
        params.update(static_params)
        # Resolve "@key" → context[key]
        for k, v in list(params.items()):
            if isinstance(v, str) and v.startswith("@"):
                params[k] = get_context(v[1:])
        return params

    # Resolve class sekarang (load time), bukan saat test run
    _cmd_cls   = None
    _load_err  = ""
    if cmd_class:
        try:
            if _ROOT not in _sys.path:
                _sys.path.insert(0, _ROOT)
            _mod_path, _cls_name = cmd_class.rsplit(".", 1)
            _mod      = _imp.import_module(_mod_path)
            _cmd_cls  = getattr(_mod, _cls_name)
        except Exception as _e:
            _load_err = str(_e)

    def _run_fn():
        if _cmd_cls is None:
            return f"NG:{_load_err or 'command_class tidak diset'}"
        try:
            params = _resolve_params()
            _log.info("[TEST] %s", label)
            return _cmd_cls(params=params).execute()
        except Exception as e:
            _log.exception("[TEST] %s exception:", label)
            return f"NG:{e}"

    kw = dict(title=label, command=f"TM81_{name.upper()}",
              description=desc, run_fn=_run_fn,
              no_retry=entry.get("no_retry", False))

    if ttype == "manual":
        return ManualTest(**kw)
    else:
        return AutoTest(**kw)


def _tm81_enabled(entry: dict) -> bool:
    """Entry diaktifkan jika: 'name' ada (bukan '_name') dan 'disabled' != true."""
    return "name" in entry and not entry.get("disabled", False)


def load_tm81_tests() -> list:
    """Baca tm81_test.json dan kembalikan list TestItem — satu per entry."""
    cfg           = _read_tm81_json()
    commissioning = _merge_commissioning(cfg.get("commissioning", {}))
    return [_make_tm81_item(e, commissioning)
            for e in cfg.get("tests", []) if _tm81_enabled(e)]


def tm81_module_names() -> list:
    """Kembalikan ["tm81:ping", "tm81:get_version", ...] sesuai urutan di tm81_test.json."""
    cfg = _read_tm81_json()
    return [f"tm81:{e['name']}" for e in cfg.get("tests", []) if _tm81_enabled(e)]


def tm81_label() -> str:
    """Derive label dari field 'label' di tm81_test.json, atau fallback ke nama file.
    Contoh: file = tm81_test.json → "TM81 Test" (kecuali ada field label di JSON).
    """
    cfg = _read_tm81_json()
    if cfg.get("label"):
        return cfg["label"]
    stem = os.path.splitext(os.path.basename(_TM81_JSON))[0]
    return stem.replace("_", " ").title()


# ---------------------------------------------------------------------------
# TM81 Flash helpers  (sama sistemnya dengan TM81, prefix "tm81_ota:")
# ---------------------------------------------------------------------------

def _read_tm81_ota_json() -> dict:
    """Baca tm81_ota.json. Return {} jika tidak ada."""
    try:
        with open(_TM81_OTA_JSON) as f:
            return json.load(f)
    except Exception:
        return {}


class _TM81FlashStep(TestBase):
    """
    Wrapper TestBase untuk satu langkah TM81 Flash.
    Memungkinkan TestController meng-inject progress_cb via set_progress_cb()
    (diperlukan untuk tipe 'progress' / ProgressBarTest).
    """
    def __init__(self, cmd_cls, conn: str, params: dict, post_wait: float = 0.0):
        super().__init__()
        self._cmd_cls   = cmd_cls
        self._conn      = conn
        self._params    = params
        self._post_wait = post_wait

    def run(self) -> str:
        import time as _t
        p = dict(self._params)
        if self._progress_cb:
            p["progress_cb"] = self.report_progress

        # Pause keepalive ping selama step OTA berlangsung agar tidak interferensi
        # dengan komunikasi bootloader di serial port yang sama.
        try:
            from controllers.keepalive import pause_global, resume_global
            _ka_available = True
        except ImportError:
            _ka_available = False

        if _ka_available:
            pause_global()
        try:
            result = self._cmd_cls(conn=self._conn, params=p).execute()
        except Exception as e:
            _log.exception("TM81 Flash step exception:")
            return f"NG:{e}"
        finally:
            if _ka_available:
                resume_global()

        if result == "OK" and self._post_wait > 0:
            _t.sleep(self._post_wait)
        return result


def _make_tm81_ota_item(entry: dict, cfg: dict):
    """
    Buat satu TestItem untuk satu langkah TM81 Flash dari tm81_ota.json -> tests.
    Sama polanya dengan _make_tm81_item, tapi inject fw_config dari top-level.
    """
    import importlib as _imp, sys as _sys

    name       = entry.get("name", "unknown")
    label      = entry.get("label", name)
    desc       = entry.get("description", "")
    ttype      = entry.get("type", "auto").lower()
    class_path = entry.get("command_class", "")
    post_wait  = float(entry.get("post_wait_s", 0.0))

    # Fixed OTA params dari commissioning.json["ota"]
    comm_ota   = _read_commissioning_json().get("ota", {})
    conn       = comm_ota.get("connection",    "ch340")
    chunk_size = comm_ota.get("chunk_size",    512)
    fill_ff    = comm_ota.get("fill_with_ff",  False)

    # fw_dir dari flash.json["flash_dir"] (sama folder firmware)
    flash_cfg  = _read_flash_json()
    fw_dir     = os.path.join(_ROOT, flash_cfg.get("flash_dir", "firmware"))

    # fw_version dari tm81_ota.json (user-configurable)
    # Bisa berupa full absolute path (dari OTA Settings dialog) atau nama file relatif ke fw_dir
    fw_version = cfg.get("fw_version", "")
    if not fw_version:
        fw_path = ""
    elif os.path.isabs(fw_version):
        fw_path = fw_version
    else:
        fw_path = os.path.join(fw_dir, fw_version)

    # Untuk step Write Firmware: tambahkan info file ke description
    if "BLWriteFirmware" in class_path or name == "write_fw":
        if not fw_path:
            desc += "\n⚠ Belum ada firmware — buka OTA Settings untuk pilih file"
        elif not os.path.isfile(fw_path):
            desc += f"\n⚠ File tidak ditemukan: {os.path.basename(fw_path)}"
        else:
            size_kb = os.path.getsize(fw_path) / 1024
            desc += f"\nFile: {os.path.basename(fw_path)} ({size_kb:.1f} KB)"

    # Params: fw config (base) + entry["params"] (override, misal skip_set_rdy)
    params = {"fw_path": fw_path, "chunk_size": chunk_size, "fill_with_ff": fill_ff}
    params.update(entry.get("params", {}))

    # Load command class (sama dengan _make_tm81_item)
    _cmd_cls  = None
    _load_err = ""
    if class_path:
        try:
            if _ROOT not in _sys.path:
                _sys.path.insert(0, _ROOT)
            mod_path, cls_name = class_path.rsplit(".", 1)
            mod      = _imp.import_module(mod_path)
            _cmd_cls = getattr(mod, cls_name)
        except Exception as e:
            _load_err = str(e)

    if _cmd_cls is None:
        def _err_fn(): return f"NG:{_load_err or 'command_class tidak diset'}"
        return AutoTest(title=label, command=f"TM81_FLASH_{name.upper()}",
                        description=desc, run_fn=_err_fn)

    # Bungkus dalam _TM81FlashStep agar progress_cb bisa di-inject
    instance = _TM81FlashStep(_cmd_cls, conn, params, post_wait)
    kw = dict(title=label, command=f"TM81_FLASH_{name.upper()}",
              description=desc, run_fn=instance.run)

    if ttype == "progress":
        return ProgressBarTest(**kw,
                               steps=entry.get("steps", 50),
                               step_ms=entry.get("step_ms", 200))
    else:
        return AutoTest(**kw)


def load_tm81_ota_tests() -> list:
    """Baca tm81_ota.json dan kembalikan list TestItem — satu per langkah."""
    cfg = _read_tm81_ota_json()
    return [_make_tm81_ota_item(e, cfg) for e in cfg.get("tests", [])]


def tm81_ota_module_names() -> list[str]:
    """Kembalikan ["tm81_ota:app_goto_bl", "tm81_ota:bl_prepare", ...] sesuai urutan."""
    cfg = _read_tm81_ota_json()
    return [f"tm81_ota:{e['name']}" for e in cfg.get("tests", []) if "name" in e]


def tm81_ota_label() -> str:
    """Derive label tampilan dari field 'label' di tm81_ota.json, atau fallback ke nama file.
    Contoh: file = tm81_ota.json, field label = "TM81 OTA" → return "TM81 OTA".
    """
    cfg = _read_tm81_ota_json()
    if cfg.get("label"):
        return cfg["label"]
    # Fallback: derive dari nama file → "tm81_ota" → "TM81 OTA"
    stem = os.path.splitext(os.path.basename(_TM81_OTA_JSON))[0]
    return stem.replace("_", " ").title()


# ---------------------------------------------------------------------------
# BEXA helpers
# ---------------------------------------------------------------------------

def _read_bexa_json() -> dict:
    """Baca bexa_test.json. Return {} jika tidak ada."""
    try:
        with open(_BEXA_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _bexa_enabled(entry: dict) -> bool:
    return "name" in entry and not entry.get("disabled", False)


def _make_bexa_item(entry: dict):
    """Buat AutoTest atau ManualTest untuk satu entry di bexa_test.json."""
    import importlib as _imp
    import sys as _sys

    name      = entry.get("name", "unknown")
    label     = entry.get("label", name)
    desc      = entry.get("description", "")
    cls_path  = entry.get("command_class", "")
    ttype     = entry.get("type", "auto").lower()

    _cmd_cls  = None
    _load_err = ""
    if cls_path:
        try:
            if _ROOT not in _sys.path:
                _sys.path.insert(0, _ROOT)
            mod_path, cls_name = cls_path.rsplit(".", 1)
            mod      = _imp.import_module(mod_path)
            _cmd_cls = getattr(mod, cls_name)
        except Exception as e:
            _load_err = str(e)

    def _run_fn():
        if _cmd_cls is None:
            return f"NG:{_load_err or 'command_class tidak diset'}"
        try:
            _log.info("[BEXA] %s", label)
            return _cmd_cls().execute()
        except Exception as e:
            _log.exception("[BEXA] %s exception:", label)
            return f"NG:{e}"

    kw = dict(title=label, command=f"BEXA_{name.upper()}",
              description=desc, run_fn=_run_fn,
              no_retry=entry.get("no_retry", False))

    if ttype == "manual":
        return ManualTest(**kw)
    else:
        return AutoTest(**kw)


def load_bexa_tests() -> list:
    """Baca bexa_test.json dan kembalikan list TestItem."""
    cfg = _read_bexa_json()
    return [_make_bexa_item(e) for e in cfg.get("tests", []) if _bexa_enabled(e)]


def bexa_module_names() -> list[str]:
    """Kembalikan ['bexa:config_request', 'bexa:get_bt_info', ...] sesuai urutan."""
    cfg = _read_bexa_json()
    return [f"bexa:{e['name']}" for e in cfg.get("tests", []) if _bexa_enabled(e)]


def bexa_label() -> str:
    """Derive label dari field 'label' di bexa_test.json."""
    cfg = _read_bexa_json()
    if cfg.get("label"):
        return cfg["label"]
    stem = os.path.splitext(os.path.basename(_BEXA_JSON))[0]
    return stem.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_test_class(mod):
    """Cari subclass TestBase di dalam modul. Return class atau None."""
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        if issubclass(obj, TestBase) and obj is not TestBase:
            return obj
    return None


def _make_item(cls_or_mod):
    """Buat TestItem dari class atau modul."""
    title   = getattr(cls_or_mod, "TITLE",       "Unnamed")
    ttype   = getattr(cls_or_mod, "TYPE",         "auto").lower()
    cmd     = getattr(cls_or_mod, "COMMAND",      "UNKNOWN")
    desc    = getattr(cls_or_mod, "DESCRIPTION",  "")
    steps   = getattr(cls_or_mod, "STEPS",        5)
    step_ms = getattr(cls_or_mod, "STEP_MS",      300)

    if inspect.isclass(cls_or_mod):
        instance = cls_or_mod()
        run_fn = instance.run if hasattr(instance, "run") else None
    else:
        raw_run = getattr(cls_or_mod, "run", None)
        run_fn = raw_run if callable(raw_run) else None

    kw = dict(title=title, command=cmd, description=desc, run_fn=run_fn)

    if ttype == "progress":
        return ProgressBarTest(steps=steps, step_ms=step_ms, **kw)
    elif ttype == "manual":
        return ManualTest(**kw)
    else:
        return AutoTest(**kw)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def discover_tests():
    """
    Scan folder tests/ dan kembalikan:
        [(module_name, display_label, cls_or_mod), ...]

    flash_test.py dan voltage_test.py di-skip karena dihandle via expand button di dialog.
    """
    results = []
    for finder, name, _ in pkgutil.iter_modules(tests.__path__):
        if name in ("flash_test", "voltage_test", "tm81_test", "bexa_test", "crc_comm_test"):
            continue
        mod = importlib.import_module(f"tests.{name}")
        cls = _find_test_class(mod)
        target = cls if cls is not None else mod
        label  = getattr(target, "TITLE", name)
        results.append((name, label, target))
    results.sort(key=lambda x: x[1])
    return results


def load_test(module_name: str):
    """
    Load satu test module dan kembalikan TestItem.

    Format khusus:
        "voltage:3v3"  ->  VoltageTest untuk entry "3v3" di voltage.json
        "flash:boot"   ->  FlashTest untuk region "boot" di flash.json
    """
    if module_name.startswith("tm81:"):
        entry_name    = module_name[len("tm81:"):]
        cfg           = _read_tm81_json()
        commissioning = _merge_commissioning(cfg.get("commissioning", {}))
        for e in cfg.get("tests", []):
            if e.get("name") == entry_name:
                if not _tm81_enabled(e):
                    raise KeyError(f"TM81 test '{entry_name}' di-disabled di tm81_test.json")
                return _make_tm81_item(e, commissioning)
        raise KeyError(f"TM81 test '{entry_name}' tidak ditemukan di tm81_test.json")

    if module_name.startswith("voltage:"):
        entry_name = module_name[len("voltage:"):]
        cfg = _read_voltage_json()
        for v in cfg.get("voltages", []):
            if v.get("name") == entry_name:
                return _make_voltage_item(v)
        raise KeyError(f"Voltage entry '{entry_name}' tidak ditemukan di voltage.json")

    if module_name.startswith("flash:"):
        # Format: "flash:proj:region", misal "flash:tm81:boot"
        rest  = module_name[len("flash:"):]
        parts = rest.split(":", 1)
        if len(parts) != 2:
            raise KeyError(f"Format module flash tidak valid: '{module_name}' (harus 'flash:proj:region')")
        proj_name, region_name = parts
        for r in _get_flash_regions(proj_name):
            if r.get("name") == region_name:
                return _make_flash_item(r, proj_name)
        raise KeyError(f"Flash region '{region_name}' tidak ditemukan di project '{proj_name}'")

    if module_name.startswith("tm81_ota:"):
        entry_name = module_name[len("tm81_ota:"):]
        cfg = _read_tm81_ota_json()
        for e in cfg.get("tests", []):
            if e.get("name") == entry_name:
                return _make_tm81_ota_item(e, cfg)
        raise KeyError(f"TM81 Flash step '{entry_name}' tidak ditemukan di tm81_ota.json")

    if module_name.startswith("bexa:"):
        entry_name = module_name[len("bexa:"):]
        cfg = _read_bexa_json()
        for e in cfg.get("tests", []):
            if e.get("name") == entry_name:
                if not _bexa_enabled(e):
                    raise KeyError(f"BEXA test '{entry_name}' di-disabled di bexa_test.json")
                return _make_bexa_item(e)
        raise KeyError(f"BEXA test '{entry_name}' tidak ditemukan di bexa_test.json")

    # Modul biasa dari folder tests/
    mod = importlib.import_module(f"tests.{module_name}")
    cls = _find_test_class(mod)
    return _make_item(cls if cls is not None else mod)
