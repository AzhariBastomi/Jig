"""
tests/tm81_flash_test.py — OTA Flash via IrDA (TM81 Bootloader)

Tidak dipakai langsung — di-load via test_loader dengan format "tm81_flash".
Konfigurasi dibaca dari json/tm81_flash.json.

Type: PROGRESS (progress bar per-chunk)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import json
import serial_manager as sm
from test_base import TestBase

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_cfg() -> dict:
    path = os.path.join(_ROOT, "json", "tm81_flash.json")
    with open(path) as f:
        return json.load(f)


class TM81FlashTest(TestBase):
    TITLE       = "OTA Flash TM81 (IrDA)"
    TYPE        = "progress"
    COMMAND     = "TM81_FLASH"
    DESCRIPTION = "Flash firmware ke device TM81 via IrDA / CH340"
    STEPS       = 50
    STEP_MS     = 200

    def run(self) -> str:
        try:
            cfg = _load_cfg()
        except Exception as e:
            return f"NG:tm81_flash.json error: {e}"

        conn       = cfg.get("connection", "ch340")
        fw_dir     = os.path.join(_ROOT, cfg.get("fw_dir", "file_flash_fota/BEXA"))
        fw_version = cfg.get("fw_version", "")
        chunk_size = cfg.get("chunk_size", 512)
        fill_ff    = cfg.get("fill_with_ff", False)

        if not fw_version:
            return "NG:fw_version kosong di tm81_flash.json"

        fw_path = os.path.join(fw_dir, fw_version)
        if not os.path.isfile(fw_path):
            return f"NG:File tidak ada: {fw_path}"

        if not sm.is_connected(conn):
            return f"NG:Koneksi '{conn}' tidak terhubung"

        from commands.tm81.bl_write_firmware import BLWriteFirmware

        cmd = BLWriteFirmware(conn=conn, params={
            "fw_path":      fw_path,
            "chunk_size":   chunk_size,
            "fill_with_ff": fill_ff,
            "progress_cb":  self.report_progress,
        })

        return cmd.execute()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    t = TM81FlashTest()
    t.set_progress_cb(lambda p: print(f"  Progress: {p:.1f}%", end="\r"))

    import serial_manager as sm
    cfg = _load_cfg()
    conn = cfg.get("connection", "ch340")
    print(f"Connecting {conn}...")
    if not sm.connect(conn):
        print(f"Gagal connect ke {conn}"); sys.exit(1)

    print("Flashing...")
    result = t.run()
    print(f"\n[TM81 OTA Flash] -> {result}")
    sm.disconnect(conn)
