"""
commands/tm81/ping.py — Ping MCU (CMD 0x00)
Response: ACK jika device aktif.
"""

from commands.tm81.base import TM81Command, CmdId


class Ping(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.PING)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        return "OK"


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
    import serial_manager as sm
    sm.connect("ch340")
    print(Ping().execute())
