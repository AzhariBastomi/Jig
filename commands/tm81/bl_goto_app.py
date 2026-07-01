"""
commands/tm81/bl_goto_app.py — Bootloader → Lompat ke App (CMD BL 0x66)
"""

from commands.tm81.base import TM81Command, CmdId

BOOT_REASON_NORMAL = 1


class BLGotoApp(TM81Command):

    def execute(self) -> str:
        data   = BOOT_REASON_NORMAL.to_bytes(1, "little")
        result = self.xfer(CmdId.BL_GOTO_APP, data=data, timeout=5.0)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print("  Bootloader → App OK")
        return "OK"
