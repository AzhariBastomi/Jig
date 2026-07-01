"""commands/tm81/lora_set_app_key.py — Set AppKey (CMD 0x11)"""
from commands.tm81.base import TM81Command, CmdId


class LoraSetAppKey(TM81Command):
    DEFAULT_APP_KEY = bytes.fromhex("8833E75406D203F48D1F6D2CCC2815D8")  # 16 bytes

    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        key_hex = p.get("app_key", self.DEFAULT_APP_KEY.hex())
        self._app_key = bytes.fromhex(key_hex)

    def execute(self) -> str:
        result = self.xfer(CmdId.SET_APP_KEY, self._app_key)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        print(f"  Set AppKey={self._app_key.hex(':')} → OK")
        return "OK"
