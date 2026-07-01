"""
commands/tm81/sensor_do_get_config.py — Sensor Get Config trigger (CMD 0x02)
Perintah device untuk menjalankan satu siklus sensor.
"""

from commands.tm81.base import TM81Command, CmdId


class SensorDoGetConfig(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.SENSOR_GET_CONFIG)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print("  Sensor Get Config → OK")
        return "OK"
