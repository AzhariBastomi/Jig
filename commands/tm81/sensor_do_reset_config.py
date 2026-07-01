"""
commands/tm81/sensor_do_reset_config.py — Sensor Reset Config (CMD 0x03)
"""

from commands.tm81.base import TM81Command, CmdId


class SensorDoResetConfig(TM81Command):

    def execute(self) -> str:
        result = self.xfer(CmdId.SENSOR_RESET_CONFIG)
        if not result.valid and result.error != "ACK":
            return f"NG:{result.error}"
        print("  Sensor Reset Config → OK")
        return "OK"
