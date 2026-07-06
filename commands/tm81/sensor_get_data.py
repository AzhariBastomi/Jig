"""
commands/tm81/sensor_get_data.py - Get Sensor Data (CMD 0x04)
"""

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "lib"))

from commands.tm81.base import TM81Command, CmdId


class SensorGetData(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.SENSOR_GET_DATA)
        if not result.valid:
            return f"NG:{result.error}"

        d = result.payload
        if len(d) < 2:
            return f"NG:payload terlalu pendek ({len(d)} bytes)"

        raw_val = int.from_bytes(d[0:2], "little")
        self._raw = raw_val
        print(f"  Sensor Raw Value: {raw_val} (0x{raw_val:04x})")
        if len(d) >= 4:
            print(f"  Sensor Extra: {d[2:].hex()}")
        return f"OK:Raw={raw_val} (0x{raw_val:04x})"

    def get_raw(self) -> int:
        return getattr(self, "_raw", 0)


# -- Standalone test ----------------------------------------------------------
if __name__ == "__main__":
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    result = SensorGetData().execute()
    print(result)
    sm.disconnect_all()
