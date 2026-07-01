"""
commands/tm81/user_reset_config.py — Reset User Config to Default (CMD 0x09)
"""

from commands.tm81.base import TM81Command, CmdId


class UserResetConfig(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.USR_RESET_CONFIG)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print("  User Reset Config → OK")
        return "OK"
