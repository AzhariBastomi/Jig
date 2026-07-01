"""
commands/tm81/app_goto_bl.py — Reboot ke Bootloader (CMD 0x05)
Kirim dari App mode → masuk Bootloader mode (untuk OTA IrDA).
"""

from commands.tm81.base import TM81Command, CmdId

BOOT_REASON_IRDA_OTA = 2


class AppGotoBL(TM81Command):

    def execute(self) -> str:
        data   = BOOT_REASON_IRDA_OTA.to_bytes(1, "little")
        result = self.xfer(CmdId.USR_REBOOT_BOOTLOADER, data=data, timeout=5.0)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print("  App → Bootloader OK")
        return "OK"
