"""commands/tm81/lora_set_dev_class.py — Set LoRa Device Class (CMD 0x15)

dev_class: 0=A, 1=B, 2=C
"""
from commands.tm81.base import TM81Command, CmdId


class LoraSetDevClass(TM81Command):
    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        self._cls = p.get("dev_class", 0)  # default Class A

    def execute(self) -> str:
        data = self._cls.to_bytes(1, "little")
        result = self.xfer(CmdId.SET_DEV_CLASS, data)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        names = {0: "A", 1: "B", 2: "C"}
        print(f"  Set DevClass={names.get(self._cls, self._cls)} → OK")
        return "OK"
