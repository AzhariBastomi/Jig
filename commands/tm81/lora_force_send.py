"""
commands/tm81/lora_force_send.py — Force Send LoRa (CMD 0x17)
Paksa device kirim uplink sekarang.
"""

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))

from commands.tm81.base import TM81Command, CmdId


class LoraForceSend(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.FORCE_SEND_LORA, timeout=10.0)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print("  LoRa Force Send → OK")
        return "OK"

# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    result = LoraForceSend().execute()
    print(result)
    sm.disconnect_all()
