"""
commands/tm81/lora_get_last_submit_time.py — Get Last LoRa Submit Time (CMD 0x23)
Response payload (4 bytes): unix timestamp (little-endian).
"""

import datetime
from commands.tm81.base import TM81Command, CmdId


class LoraGetLastSubmitTime(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.GET_LAST_SUBMIT_TIME)
        if not result.valid:
            return f"NG:{result.error}"

        d = result.payload
        if len(d) < 4:
            return f"NG:payload terlalu pendek ({len(d)} bytes)"

        ts      = int.from_bytes(d[0:4], "little")
        dt_str  = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self._ts = ts
        print(f"  Last Submit Time: {dt_str} (unix={ts})")
        return "OK"
