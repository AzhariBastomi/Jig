"""
commands/tm81/bl_write_firmware.py — OTA Flash via IrDA (TM81 Bootloader)

Flow:
  1. AppGotoBL  — reboot ke bootloader (skip jika sudah di BL)
  2. BL_SET_RDY — kirim fw_size (4B LE) + CRC32-MPEG2 (4B LE)
  3. BL_FW_DATA — kirim data chunk per chunk (frame_id + chunk_size + data)
  4. BL_GOTO_APP — lompat ke App

progress_cb(float 0-100) dipanggil setiap chunk selesai dikirim.
"""

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))

import os
import time
from crccheck.crc import Crc32Mpeg2

try:
    from commands.tm81.base import TM81Command, CmdId
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))
    from commands.tm81.base import TM81Command, CmdId


class BLWriteFirmware(TM81Command):
    CHUNK_SIZE   = 512          # bytes per frame — override via params
    FILL_WITH_FF = False        # pad file ke APP_MAX_SIZE dengan 0xFF
    APP_MAX_SIZE = 1024 * 160   # 160 KB

    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        self._fw_path      = p.get("fw_path", "")
        self._chunk_size   = p.get("chunk_size",   self.CHUNK_SIZE)
        self._fill_with_ff = p.get("fill_with_ff", self.FILL_WITH_FF)
        self._progress_cb  = p.get("progress_cb",  None)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def execute(self) -> str:
        if not self._fw_path or not os.path.isfile(self._fw_path):
            return f"NG:File tidak ditemukan: {self._fw_path!r}"

        # Baca firmware
        with open(self._fw_path, "rb") as f:
            fw_data = f.read(self.APP_MAX_SIZE)

        fw_size   = len(fw_data)
        crc_bytes = Crc32Mpeg2.calc(fw_data).to_bytes(4, "little")

        if self._fill_with_ff and fw_size < self.APP_MAX_SIZE:
            fw_data += b"\xff" * (self.APP_MAX_SIZE - fw_size)

        print(f"  FW: {os.path.basename(self._fw_path)}")
        print(f"  Size: {fw_size} B  CRC: {crc_bytes.hex(' ')}")

        # Step 1: BL_SET_RDY — kirim fw_size + CRC
        r = self._bl_set_rdy(fw_size, crc_bytes)
        if r != "OK":
            return r

        time.sleep(0.5)

        # Step 2: BL_FW_DATA — kirim chunk per chunk
        r = self._bl_send_chunks(fw_data)
        if r != "OK":
            return r

        # Step 3: BL_GOTO_APP
        r = self._bl_goto_app()
        return r

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _bl_set_rdy(self, fw_size: int, crc_bytes: bytes) -> str:
        data = fw_size.to_bytes(4, "little") + crc_bytes
        result = self.xfer(CmdId.BL_SET_RDY, data, timeout=8.0)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:BL_SET_RDY {result.error}"
        print("  BL_SET_RDY → ACK")
        return "OK"

    def _bl_send_chunks(self, fw_data: bytes) -> str:
        total      = len(fw_data)
        chunk_size = self._chunk_size
        sent       = 0
        frame_id   = 0

        while sent < total:
            chunk     = fw_data[sent: sent + chunk_size]
            chunk_len = len(chunk)
            payload   = (
                frame_id.to_bytes(2, "little")
                + chunk_len.to_bytes(2, "little")
                + chunk
            )

            result = self.xfer(CmdId.BL_FW_DATA, payload, timeout=3.0)
            if not result.valid and result.error not in ("ACK",):
                return f"NG:BL_FW_DATA frame={frame_id} {result.error}"

            sent     += chunk_len
            frame_id += 1
            pct       = sent / total * 100
            print(f"  [{frame_id}] {sent}/{total} B  {pct:.1f}%", end="\r")

            if self._progress_cb:
                self._progress_cb(pct)

        print()  # newline setelah \r
        print(f"  Semua {frame_id} chunk terkirim")
        return "OK"

    def _bl_goto_app(self) -> str:
        data   = (1).to_bytes(1, "little")  # BOOT_REASON_NORMAL = 1
        result = self.xfer(CmdId.BL_GOTO_APP, data, timeout=3.0)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:BL_GOTO_APP {result.error}"
        print("  BL_GOTO_APP → OK")
        return "OK"

# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    import sys
    fw_path = sys.argv[1] if len(sys.argv) > 1 else "firmware.bin"
    params = {"firmware_path": fw_path}
    result = BLWriteFirmware(params=params).execute()
    print(result)
    sm.disconnect_all()
