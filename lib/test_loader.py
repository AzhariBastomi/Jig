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
  - load_flash_tests() -> list[TestItem]  (semua region sekaligus)
  - load_test("flash:boot")              (satu region)

TM81 tasks (format khusus):
  - Disimpan di tasks.json sebagai "tm81:<name>", misal "tm81:ping"
  - Di-expand dari json/tm81_test.json
  - load_tm81_tests() -> list[TestItem]  (semua test sekaligus)
  - load_test("tm81:ping")              (satu test)
"""

import importlib
import inspect
import json
import os
import pkgutil
import tests

from test_base import TestBase
from test_modules import ProgressBarTest, ManualTest, AutoTest

_ROOT          = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_FLASH_JSON    = os.path.join(_ROOT, "json", "flash.json")
_VOLTAGE_JSON  = os.path.join(_ROOT, "json", "voltage.json")
_TM81_JSON     = os.path.join(_ROOT, "json", "tm81_test.json")


# ---------------------------------------------------------------------------
# Flash helpers
# ---------------------------------------------------------------------------

def _read_flash_json() -> dict:
    """Baca flash.json. Return {} jika tidak ada."""
    try:
        with open(_FLASH_JSON) as f:
            return json.load(f)
    except Exception:
        return {}


def _make_flash_item(region: dict):
    """Buat satu ProgressBarTest untuk satu region flash."""
    from tests.flash_test import FlashTest

    name = region.get("name", "unknown")
    desc = region.get("description", f"Flash region '{name}'")

    # Buat subclass anonim agar setiap instance punya REGION sendiri
    cls      = type(f"_FlashTest_{name}", (FlashTest,), {
        "TITLE":       f"Flash {name}",
        "COMMAND":     f"FLASH_{name.upper()}",
        "DESCRIPTION": desc,
        "REGION":      region,
    })
    instance = cls()

    return ProgressBarTest(
        title       = f"Flash {name}",
        command     = f"FLASH_{name.upper()}",
        description = desc,
        run_fn      = instance.run,
        steps       = getattr(cls, "STEPS",   10),
        step_ms     = getattr(cls, "STEP_MS", 300),
    )


def load_flash_tests() -> list:
    """
    Baca flash.json dan kembalikan list TestItem — satu per region.
    Pasangan module_name untuk tasks.json: "flash:<name>".
    """
    cfg = _read_flash_json()
    return [_make_flash_item(r) for r in cfg.get("regions", [])]


def flash_module_names() -> list[str]:
    """Kembalikan ["flash:boot", "flash:app", ...] sesuai urutan di flash.json."""
    cfg = _read_flash_json()
    return [f"flash:{r['name']}" for r in cfg.get("regions", [])]


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


def _make_tm81_item(entry: dict):
    """Buat AutoTest untuk satu entry di tm81_test.json."""
    import importlib as _imp
    import sys as _sys

    name        = entry.get("name", "unknown")
    label       = entry.get("label", name)
    desc        = entry.get("description", "")
    cmd_class   = entry.get("command_class", "")
    ttype       = entry.get("type", "auto").lower()

    def _run_fn():
        try:
            # Pastikan root project ada di sys.path agar commands/ bisa diimport
            if _ROOT not in _sys.path:
                _sys.path.insert(0, _ROOT)
            mod_path, cls_name = cmd_class.rsplit(".", 1)
            mod  = _imp.import_module(mod_path)
            cls  = getattr(mod, cls_name)
            return cls().execute()
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"NG:{e}"

    kw = dict(title=label, command=f"TM81_{name.upper()}",
              description=desc, run_fn=_run_fn)

    if ttype == "manual":
        return ManualTest(**kw)
    else:
        return AutoTest(**kw)


def load_tm81_tests() -> list:
    """Baca tm81_test.json dan kembalikan list TestItem — satu per entry."""
    cfg = _read_tm81_json()
    return [_make_tm81_item(e) for e in cfg.get("tests", [])]


def tm81_module_names() -> list:
    """Kembalikan ["tm81:ping", "tm81:get_version", ...] sesuai urutan di tm81_test.json."""
    cfg = _read_tm81_json()
    return [f"tm81:{e['name']}" for e in cfg.get("tests", [])]


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
        if name in ("flash_test", "voltage_test", "tm81_test", "crc_comm_test"):
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
        entry_name = module_name[len("tm81:"):]
        cfg = _read_tm81_json()
        for e in cfg.get("tests", []):
            if e.get("name") == entry_name:
                return _make_tm81_item(e)
        raise KeyError(f"TM81 test '{entry_name}' tidak ditemukan di tm81_test.json")

    if module_name.startswith("voltage:"):
        entry_name = module_name[len("voltage:"):]
        cfg = _read_voltage_json()
        for v in cfg.get("voltages", []):
            if v.get("name") == entry_name:
                return _make_voltage_item(v)
        raise KeyError(f"Voltage entry '{entry_name}' tidak ditemukan di voltage.json")

    if module_name.startswith("flash:"):
        region_name = module_name[len("flash:"):]
        cfg = _read_flash_json()
        for r in cfg.get("regions", []):
            if r.get("name") == region_name:
                return _make_flash_item(r)
        raise KeyError(f"Flash region '{region_name}' tidak ditemukan di flash.json")

    mod = importlib.import_module(f"tests.{module_name}")
    cls = _find_test_class(mod)
    return _make_item(cls if cls is not None else mod)
