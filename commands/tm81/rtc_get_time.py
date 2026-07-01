"""
commands/tm81/rtc_get_time.py — Get RTC Time (CMD 0x0A)
Response payload (6 bytes): second, minute, hour, day, month, year(2digit).
"""

from commands.tm81.base import TM81Command, CmdId


class RtcGetTime(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.USR_GET_TIME)
        if not result.valid:
            return f"NG:{result.error}"

        d = result.payload
        if len(d) < 6:
            return f"NG:payload terlalu pendek ({len(d)} bytes)"

        sec, mn, hr, day, month, yr = d[0], d[1], d[2], d[3], d[4], d[5]
        self._time_str = f"20{yr:02d}-{month:02d}-{day:02d} {hr:02d}:{mn:02d}:{sec:02d}"
        print(f"  RTC Time: {self._time_str}")
        return "OK"

    def get_time(self) -> str:
        return getattr(self, "_time_str", "")
