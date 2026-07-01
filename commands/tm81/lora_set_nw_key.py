"""commands/tm81/lora_set_nw_key.py — Set NwKey (CMD 0x12)"""
from commands.tm81.base import TM81Command, CmdId


class LoraSetNwKey(TM81Command):
    DEFAULT_NW_KEY = bytes.fromhex("8833E75406D203F48F1F6D2CCC2815D8")  # 16 bytes

    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        key_hex = p.get("nw_key", self.DEFAULT_NW_KEY.hex())
        self._nw_key = bytes.fromhex(key_hex)

    def execute(self) -> str:
        result = self.xfer(CmdId.SET_NW_KEY, self._nw_key)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        print(f"  Set NwKey={self._nw_key.hex(':')} → OK")
        return "OK"
