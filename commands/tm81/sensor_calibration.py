"""
commands/tm81/sensor_calibration.py — Sensor Calibration (CMD 0x02 + 0x04)
Loop: get_config → get_data → cek status bit → konfirmasi operator.
Tipe: MANUAL (operator confirm saat calibration done).
"""

from commands.tm81.base import TM81Command, CmdId


class SensorCalibration(TM81Command):

    CAL_STATUS_FAIL           = 0x01
    CAL_STATUS_NEVER_CAL      = 0x10
    CAL_STATUS_REMOVED        = 0x04
    CAL_STATUS_METAL          = 0x08
    CAL_STATUS_LOW_VOLTAGE    = 0x20

    def _check_cal_status(self, status_byte: int) -> str:
        """Return "" jika OK, atau pesan error."""
        if status_byte & self.CAL_STATUS_FAIL:
            return "Calibration failed"
        if not (status_byte & self.CAL_STATUS_NEVER_CAL):
            return "Never calibrated"
        if status_byte & self.CAL_STATUS_REMOVED:
            return "Sensor removed"
        if status_byte & self.CAL_STATUS_METAL:
            return "Metal interference detected"
        if status_byte & self.CAL_STATUS_LOW_VOLTAGE:
            return "Sensor voltage too low"
        return ""

    def execute(self) -> str:
        import time

        max_attempts = 20
        for attempt in range(max_attempts):
            time.sleep(2)

            # 1. Get Config (trigger sensor cycle)
            r = self.xfer(CmdId.SENSOR_GET_CONFIG)
            if not r.valid and r.error != "ACK":
                print(f"  [cal] sensor_get_config fail: {r.error}")
                continue
            time.sleep(2)

            # 2. Get Data (baca hasil)
            r = self.xfer(CmdId.SENSOR_GET_DATA)
            if not r.valid:
                print(f"  [cal] sensor_get_data fail: {r.error}")
                continue

            d = r.payload
            if len(d) < 13:
                print(f"  [cal] payload terlalu pendek ({len(d)} bytes)")
                continue

            err = self._check_cal_status(d[12])
            if err:
                print(f"  [cal] attempt {attempt+1}: {err}")
                continue

            print(f"  [cal] Calibration success! Intensity={d[0]}, Status=0x{d[12]:02x}")
            return "OK"

        return "NG:Calibration timeout setelah banyak percobaan"
