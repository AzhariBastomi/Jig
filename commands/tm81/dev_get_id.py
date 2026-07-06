"""
commands/tm81/dev_get_id.py — Get Device ID (CMD 0x1B)
Response payload (24 bytes):
  [0:8]  Device EUI (8 bytes binary)
  [8:24] Serial Number (16 bytes ASCII, null-padded)
"""

from commands.tm81.base import TM81Command, CmdId


class DevGetId(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.DEV_GET_ID)
        if not result.valid:
            return f"NG:{result.error}"

        d = result.payload
        if len(d) < 24:
            return f"NG:payload terlalu pendek ({len(d)} bytes, expected 24)"

        self._dev_eui = d[0:8].hex(":")
