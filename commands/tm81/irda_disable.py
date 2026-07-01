"""commands/tm81/irda_disable.py — IrDA Disable (CMD 0x01)"""
from commands.tm81.base import TM81Command, CmdId


class IrdaDisable(TM81Command):
    def execute(self) -> str:
        result = self.xfer(CmdId.IRDA_DISABLE)
        if not result.valid and result.error not in ("ACK",):
            return f"NG:{result.error}"
        print("  IrDA Disable → OK")
        return "OK"
