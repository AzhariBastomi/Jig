"""
commands/tm81/dev_get_id.py — Get Device ID (CMD 0x1B)
Response payload (24 bytes): Device ID string.
"""

from commands.tm81.base import TM81Command, CmdId


class DevGetId(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.DEV_GET_ID)
        if not result.valid:
            return f"NG:{result.error}"

        self._device_id = result.payload.decode("utf-8", errors="replace").strip("\x00").strip()
        print(f"  Device ID: {self._device_id}")
        return "OK"

    def get_id(self) -> str:
        return getattr(self, "_device_id", "")
