"""
import logging
_log = logging.getLogger(__name__)
commands/tm81/bl_goto_app.py — Bootloader → Lompat ke App (CMD BL 0x66)
"""

try:
    from commands.tm81.base import TM81Command, CmdId
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))
    from commands.tm81.base import TM81Command, CmdId

BOOT_REASON_NORMAL = 1


class BLGotoApp(TM81Command):

    def execute(self) -> str:
        data   = BOOT_REASON_NORMAL.to_bytes(1, "little")
        result = self.xfer(CmdId.BL_GOTO_APP, data=data, timeout=5.0)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        _log.debug("  Bootloader → App OK")
        return "OK"

# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    result = BLGotoApp().execute()
    print(result)
    sm.disconnect_all()
