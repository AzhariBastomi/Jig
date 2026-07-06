"""
commands/tm81/rtc_set_time.py — Set RTC Time (CMD 0x0B)
Data (6 bytes): second, minute, hour, day, month, year(2digit).
"""

import datetime
from commands.tm81.base import TM81Command, CmdId


class RtcSetTime(TM81Command):
    """
    Set RTC ke waktu sekarang (PC time) atau waktu custom.

    Contoh:
        RtcSetTime().execute()                     # pakai waktu PC
        RtcSetTime(dt=datetime(2025,1,15,9,0,0)).execute()
    """

    def __init__(self, dt: datetime.datetime = None, **kwargs):
        super().__init__(**kwargs)
        self._dt = dt

    def execute(self) -> str:
        dt = self._dt or datetime.datetime.now()
        data = bytes([
            dt.year % 100, dt.month, dt.day,
            dt.hour, dt.minute, dt.second,
        ])
        result = self.xfer(CmdId.USR_SET_TIME, data=data)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print(f"  Set RTC Time: {dt.strftime('%Y-%m-%d %H:%M:%S')} → OK")
        return "OK"
