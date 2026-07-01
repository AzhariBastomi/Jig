"""
commands/tm81/dev_set_id.py — Set Device ID (CMD 0x1C)
Data: ID string (max 24 bytes, null-padded).
"""

from commands.tm81.base import TM81Command, CmdId


class DevSetId(TM81Command):

    def __init__(self, device_id: str, **kwargs):
        super().__init__(**kwargs)
        self._device_id = device_id

    def execute(self) -> str:
        id_bytes = self._device_id.encode("utf-8")[:24].ljust(24, b"\x00")
        result   = self.xfer(CmdId.DEV_SET_ID, data=id_bytes)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print(f"  Set Device ID: {self._device_id} → OK")
        return "OK"
