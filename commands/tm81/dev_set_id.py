"""
commands/tm81/dev_set_id.py — Set Device ID / Serial Number (CMD 0x1C)
Data: Serial Number string, 16 bytes ASCII, null-padded.
(DevEUI tidak diset lewat command ini — DevEUI bersifat read-only dari hardware)
"""

from commands.tm81.base import TM81Command, CmdId


class DevSetId(TM81Command):

    def __init__(self, conn=None, timeout=None, params=None):
        super().__init__(conn, timeout)
        p = params or {}
        self._device_id = p.get("device_id", "")

    def execute(self) -> str:
        if not self._device_id:
            return "NG:device_id kosong — isi field 'Device ID / Serial No.' di UI"
        # Kirim 16 bytes (SN o