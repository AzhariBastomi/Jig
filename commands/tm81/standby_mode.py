"""commands/tm81/standby_mode.py — Enter Standby Mode (CMD 0x0E)"""
from commands.tm81.base import TM81Command, CmdId


class StandbyMode(TM81Command):
    def execute(self) -> str:
        result = self.xfer(CmdId.ENTER_STANDBY)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        print("  Standby Mode → OK")
        return "OK"
