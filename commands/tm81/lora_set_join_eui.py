"""commands/tm81/lora_set_join_eui.py — Set JoinEUI (CMD 0x10)"""
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
        print(f"  Set JoinEUI={self._join_eui.hex(':')} → OK")
        return "OK"
