"""
commands/tm81/dev_get_id.py — Get Device ID (CMD 0x1B)
Response payload (24 bytes):
  [0:8]  Device EUI (8 bytes binary)
  [8:24] Serial Number (16 bytes ASCII, null-padded)
"""

try:
    from commands.tm81.base import TM81Command, CmdId
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))
    from commands.tm81.base import TM81Command, CmdId


class DevGetId(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.DEV_GET_ID)
        if not result.valid:
            return f"NG:{result.error}"

        d = result.payload
        if len(d) < 24:
            return f"NG:payload terlalu pendek ({len(d)} bytes, expected 24)"

        eui = d[0:8].hex()                                          # "ffffffffffffffff"
        sn  = d[8:24].rstrip(b"\x00").decode("ascii", errors="replace")  # "TM81123487651230"

        return f"OK:EUI={eui} SN={sn}"

# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    result = DevGetId().execute()
    print(result)
    sm.disconnect_all()
