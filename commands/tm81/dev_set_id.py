"""
commands/tm81/dev_set_id.py — Set Device ID / Serial Number (CMD 0x1C)
Data: Serial Number string, 16 bytes ASCII, null-padded.
(DevEUI tidak diset lewat command ini — DevEUI bersifat read-only dari hardware)
"""

try:
    from commands.tm81.base import TM81Command, CmdId
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))
    from commands.tm81.base import TM81Command, CmdId


class DevSetId(TM81Command):

    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        self._device_id = p.get("device_id", "")

    def execute(self) -> str:
        if not self._device_id:
            return "NG:device_id kosong — isi field 'Device ID / Serial No.' di UI"
        # Kirim 16 bytes (SN o

# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    params = {"device_id": "TM81123487651231"}  # ganti sesuai Serial No
    result = DevSetId(params=params).execute()
    print(result)
    sm.disconnect_all()
