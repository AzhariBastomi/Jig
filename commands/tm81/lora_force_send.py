"""
commands/tm81/lora_force_send.py — Force Send LoRa (CMD 0x17)
Paksa device kirim uplink sekarang.
"""

from commands.tm81.base import TM81Command, CmdId


class LoraForceSend(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.FORCE_SEND_LORA, timeout=10.0)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print("  LoRa Force Send → OK")
        return "OK"
