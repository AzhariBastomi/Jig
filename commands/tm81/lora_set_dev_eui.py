"""commands/tm81/lora_set_dev_eui.py — Set DevEUI (CMD 0x0F)

Default DevEUI dapat di-override lewat params di tm81_test.json:
    "params": {"dev_eui": "0080E1010101010A"}
"""
from commands.tm81.base import TM81Command, CmdId


class LoraSetDevEui(TM81Command):
    DEFAULT_DEV_EUI = bytes.fromhex("0080E10101010104")  # 8 bytes

    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        eui_hex = p.get("dev_eui", self.DEFAULT_DEV_EUI.hex())
        self._dev_eui = bytes.fromhex(eui_hex)

    def execute(self) -> str:
        result = self.xfer(CmdId.SET_DEV_EUI, self._dev_eui)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        print(f"  Set DevEUI={self._dev_eui.hex(':')} → OK")
        return "OK"
