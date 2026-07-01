"""
flash_test.py - Generic flash test, satu instance per region di flash.json.

Tidak dipakai langsung — dibuat oleh test_loader via "flash:<name>" format.
Bisa juga diinstansiasi manual untuk CLI:
    python flash_test.py boot
    python flash_test.py app
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import json
from test_base import TestBase
from flasher import Stm32Flasher, Stm32Config
from stlink_path import find_flash_tool

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_flash_json() -> dict:
    path = os.path.join(_ROOT, "json", "flash.json")
    with open(path) as f:
        return json.load(f)


class FlashTest(TestBase):
    """
    Base class flash test. Instance per region dibuat via factory.
    Jangan pakai langsung — set REGION dulu atau pakai for_region().
    """
    TITLE       = "Flash"
    TYPE        = "progress"
    COMMAND     = "FLASH"
    DESCRIPTION = ""
    STEPS       = 10
    STEP_MS     = 300

    # Di-set oleh factory (dict dari flash.json regions[i])
    REGION: dict = {}

    def run(self) -> str:
        region = self.REGION
        if not region:
            return "NG:Region tidak dikonfigurasi"

        try:
            tool = find_flash_tool()
        except FileNotFoundError as e:
            return f"NG:{e}"

        try:
            cfg_data  = _load_flash_json()
            flash_dir = os.path.join(_ROOT, cfg_data.get("flash_dir", "file_flash_fota"))
        except Exception as e:
            return f"NG:Gagal baca flash.json: {e}"

        fw_file = region.get("file", "")
        if not fw_file:
            return f"NG:field 'file' kosong untuk region {region.get('name')!r}"

        fw_path = os.path.join(flash_dir, fw_file)
        if not os.path.isfile(fw_path):
            return f"NG:file tidak ada: {fw_path}"

        address = region.get("address", "0x08000000")
        reset   = region.get("reset", True)
        cfg     = Stm32Config(stlink_bin=tool, flash_addr=address, reset=reset)
        result  = Stm32Flasher(cfg).flash(fw_path, progress_cb=self.report_progress)

        return "OK" if result.ok else f"NG:{result.message}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    region_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not region_name:
        print("Usage: python flash_test.py <region_name>")
        print("       region_name = nama region di flash.json (misal: boot, app)")
        sys.exit(1)

    try:
        data = _load_flash_json()
    except FileNotFoundError:
        print("flash.json tidak ditemukan di root project"); sys.exit(1)

    region = next((r for r in data.get("regions", []) if r.get("name") == region_name), None)
    if not region:
        names = [r.get("name") for r in data.get("regions", [])]
        print(f"Region {region_name!r} tidak ditemukan. Tersedia: {names}")
        sys.exit(1)

    # Buat instance dinamis dengan REGION yang sudah di-set
    cls      = type("_FlashTest", (FlashTest,), {"REGION": region})
    instance = cls()
    instance.set_progress_cb(lambda p: print(f"  Progress: {p:.0f}%", end="\r"))

    print(f"Flash region '{region_name}' @ {region.get('address')} ...")
    result = instance.run()
    print(f"\n[Flash {region_name}] -> {result}")
