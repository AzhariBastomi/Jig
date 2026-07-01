"""
commands/tm81/user_synch_config.py — Sync User Config (CMD 0x06)
"""

from commands.tm81.base import TM81Command, CmdId


class UserSynchConfig(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.USR_SYNC_CFG)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print("  User Sync Config → OK")
        return "OK"
