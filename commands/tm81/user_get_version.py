"""
commands/tm81/user_get_version.py — Get Firmware Version (CMD 0x0C)
Response payload (6 bytes): major, minor, patch, build(3B).
"""

from commands.tm81.base import TM81Command, CmdId


class UserGetVersion(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.USR_GET_VER)
        if not result.valid:
            return f"NG:{result.error}"

        d = result.payload
        if len(d) < 3:
            return f"NG:payload terlalu pendek ({len(d)} bytes)"

        self._app_version = f"v{d[0]}.{d[1]}.{d[2]}"
        self._bl_version  = f"v{d[3]}.{d[4]}.{d[5]}" if len(d) >= 6 else "N/A"
        print(f"  App Version: {self._app_version}")
        print(f"  Bootloader Version: {self._bl_version}")
        return "OK"

    def get_version(self) -> str:
        return getattr(self, "_version", "")
