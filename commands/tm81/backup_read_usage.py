"""commands/tm81/backup_read_usage.py — Baca usage history (CMD 0x18)

Kirim: day(1B) + month(1B)
day=0 → baca seluruh bulan (31 hari), day>0 → baca hari tertentu
"""
try:
    from commands.tm81.base import TM81Command, CmdId
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))
    from commands.tm81.base import TM81Command, CmdId
from datetime import datetime


class BackupReadUsage(TM81Command):
    # pulse_res: 0=RES_1L, 1=RES_10L, 2=RES_100L
    PULSE_RES = 1  # RES_10L

    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        now = datetime.now()
        self._day       = p.get("day",   1)
        self._month     = p.get("month", now.month)
        self._pulse_res = p.get("pulse_res", self.PULSE_RES)

    def execute(self) -> str:
        data = (
            self._day.to_bytes(1, "little")
            + self._month.to_bytes(1, "little")
        )
        result = self.xfer(CmdId.USAGE_HISTORY_READ, data)
        if not result.valid:
            return f"NG:{result.error}"

        d = result.payload
        if not d:
            return "NG:empty payload"

        divisor = 10 * (10 ** self._pulse_res)
        if self._day == 0:
            # monthly: 31 entries × 4 bytes
            for i in range(1, 32):
                base = i * 4
                if base + 3 >= len(d):
                    break
                raw = int.from_bytes(d[base:base+4], "little")
                print(f"  Day {i:2d}: {raw/divisor:.2f} m3")
        else:
            raw = int.from_bytes(d[:4], "little")
            print(f"  Day {self._day}/{self._month}: {raw/divisor:.2f} m3")
        return "OK"

# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    # params: day=1, month=1 (opsional, default bulan ini)
    params = {}  # kosongkan untuk default
    result = BackupReadUsage(params=params).execute()
    print(result)
    sm.disconnect_all()
