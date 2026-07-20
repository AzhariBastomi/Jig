"""commands/tm81/lora_set_join_eui.py — Set JoinEUI (CMD 0x10)"""
import logging
_log = logging.getLogger(__name__)
try:
    from commands.tm81.base import TM81Command, CmdId
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))
    from commands.tm81.base import TM81Command, CmdId


class LoraSetJoinEui(TM81Command):
    DEFAULT_JOIN_EUI = bytes(8)  # 0x00 * 8

    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        eui_hex = p.get("join_eui", self.DEFAULT_JOIN_EUI.hex())
        self._join_eui = bytes.fromhex(eui_hex)

    def execute(self) -> str:
        result = self.xfer(CmdId.SET_JOIN_EUI, self._join_eui)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        _log.debug(f"  Set JoinEUI={self._join_eui.hex(':')} → OK")
        return "OK"

# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    params = {"join_eui": "0000000000000001"}  # 16 hex chars
    result = LoraSetJoinEui(params=params).execute()
    print(result)
    sm.disconnect_all()
