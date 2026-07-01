"""
commands/tm81/wdt_test.py — Test Watchdog Timer (CMD 0x0D)
Device akan reset via WDT setelah command ini → koneksi putus adalah hasil normal.
"""

from commands.tm81.base import TM81Command, CmdId


class WdtTest(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.USR_TEST_WDT, timeout=5.0)
        # Device reset setelah WDT, ACK atau timeout dua-duanya normal
        if result.error in ("ACK", "Timeout"):
            print("  WDT Test → device akan reset (normal)")
            return "OK"
        if not result.valid:
            return f"NG:{result.error}"
        return "OK"
